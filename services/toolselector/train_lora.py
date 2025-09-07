#!/usr/bin/env python3
"""
🎯 ToolSelector LoRA Training - Svenska AI Agent Tool Selection
Tränar LoRA adapter för förbättrad verktygsval i svenska kontexter
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import torch
import transformers

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
WEIGHTS_DIR = PROJECT_ROOT / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True, parents=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration för LoRA finetune"""

    # Model settings
    base_model: str = "microsoft/DialoGPT-small"  # 117M params, bra för svenska
    model_max_length: int = 512

    # LoRA settings
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: List[str] = field(default_factory=lambda: ["c_attn", "c_proj"])

    # Training hyperparams
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1

    # Evaluation
    eval_steps: int = 50
    save_steps: int = 100
    logging_steps: int = 25
    eval_strategy: str = "steps"

    # Output
    output_dir: str = "weights/toolselector-lora-v1"
    run_name: str = "toolselector-svenska-lora"

    # Safety gates
    max_train_samples: int = 1000
    max_eval_samples: int = 200


def create_tool_selection_prompt(
    intent: str, lang: str = "sv", context: str = ""
) -> str:
    """Skapa träningsprompt för verktygsval"""

    tool_options = {
        "email": "email_tool",
        "calendar": "calendar_tool",
        "time_info": "time_tool",
        "calculation": "math_tool",
        "weather": "weather_tool",
        "general": "chat_tool",
        "unknown": "chat_tool",
    }

    if lang == "sv":
        prompt = f"""<|system|>Du är Alice, en svensk AI-assistent. Välj bästa verktyget för användarens förfrågan.

Tillgängliga verktyg:
- email_tool: för att skicka email och meddelanden
- calendar_tool: för kalender och scheman  
- time_tool: för tid och datum
- math_tool: för beräkningar
- weather_tool: för väder
- chat_tool: för allmän konversation

Intent: {intent}
Kontext: {context}

Verktyg:<|endoftext|>"""
    else:
        prompt = f"""<|system|>You are Alice, an AI assistant. Choose the best tool for the user's request.

Available tools:
- email_tool: for sending emails and messages
- calendar_tool: for calendar and scheduling
- time_tool: for time and date queries
- math_tool: for calculations  
- weather_tool: for weather queries
- chat_tool: for general conversation

Intent: {intent}
Context: {context}

Tool:<|endoftext|>"""

    return prompt, tool_options.get(intent, "chat_tool")


def prepare_training_data(telemetry_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Förbered träningsdata från telemetri för verktygsval"""

    training_examples = []

    for episode in telemetry_data:
        intent = episode.get("intent", "unknown")
        lang = episode.get("lang", "sv")
        tool_used = episode.get("tool_primary", "chat_tool")
        success = episode.get("success", False)

        # Bara framgångsrika exempel för supervised learning
        if not success:
            continue

        # Skapa prompt och target
        prompt, expected_tool = create_tool_selection_prompt(intent, lang)

        # Om verktyget som användes var framgångsrikt, lär av det
        target_tool = tool_used if success else expected_tool

        training_example = {
            "input_text": prompt,
            "target_text": target_tool,
            "intent": intent,
            "language": lang,
            "success": success,
            "reward": episode.get("reward", 0.0),
        }

        training_examples.append(training_example)

    # Sortera på reward - använd bästa exempel först
    training_examples.sort(key=lambda x: x["reward"], reverse=True)

    logger.info(f"Prepared {len(training_examples)} training examples")
    return training_examples


def create_training_dataset(
    examples: List[Dict[str, str]], tokenizer, config: TrainingConfig
):
    """Skapa HuggingFace dataset för träning"""

    class ToolSelectorDataset(torch.utils.data.Dataset):
        def __init__(self, examples, tokenizer, max_length=512):
            self.examples = examples
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self):
            return len(self.examples)

        def __getitem__(self, idx):
            example = self.examples[idx]

            # Kombinera input + target för causal LM
            full_text = example["input_text"] + example["target_text"]

            # Tokenize
            encoding = self.tokenizer(
                full_text,
                truncation=True,
                max_length=self.max_length,
                padding="max_length",
                return_tensors="pt",
            )

            # Labels = input_ids (för causal LM)
            labels = encoding["input_ids"].clone()

            # Mask prompt tokens so we only train on tool selection
            prompt_length = len(self.tokenizer.encode(example["input_text"]))
            labels[:prompt_length] = -100  # Ignore loss on prompt

            return {
                "input_ids": encoding["input_ids"].flatten(),
                "attention_mask": encoding["attention_mask"].flatten(),
                "labels": labels.flatten(),
            }

    return ToolSelectorDataset(examples, tokenizer, config.model_max_length)


def setup_model_and_tokenizer(config: TrainingConfig):
    """Setup modell och tokenizer med LoRA"""

    # Load tokenizer
    tokenizer = transformers.AutoTokenizer.from_pretrained(config.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = transformers.AutoModelForCausalLM.from_pretrained(
        config.base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    # Setup LoRA
    from peft import LoraConfig, TaskType, get_peft_model

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
        bias="none",
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    return model, tokenizer


def train_toolselector(config: TrainingConfig, training_data: List[Dict[str, str]]):
    """Huvudträningsfunktion"""

    logger.info("🎯 Starting ToolSelector LoRA Training")

    # Setup model
    model, tokenizer = setup_model_and_tokenizer(config)

    # Prepare datasets
    train_split = int(0.8 * len(training_data))
    train_examples = training_data[:train_split][: config.max_train_samples]
    eval_examples = training_data[train_split:][: config.max_eval_samples]

    train_dataset = create_training_dataset(train_examples, tokenizer, config)
    eval_dataset = create_training_dataset(eval_examples, tokenizer, config)

    logger.info(
        f"Train examples: {len(train_examples)}, Eval examples: {len(eval_examples)}"
    )

    # Training arguments
    training_args = transformers.TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_ratio=config.warmup_ratio,
        logging_steps=config.logging_steps,
        eval_steps=config.eval_steps,
        evaluation_strategy=config.eval_strategy,
        save_steps=config.save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        run_name=config.run_name,
        report_to=None,  # Disable wandb for now
        fp16=torch.cuda.is_available(),
    )

    # Data collator
    data_collator = transformers.DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM
    )

    # Trainer
    trainer = transformers.Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # Train!
    logger.info("🚀 Starting training...")
    trainer.train()

    # Save final model
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    # Save training metadata
    metadata = {
        "model_type": "toolselector_lora",
        "base_model": config.base_model,
        "lora_config": {
            "r": config.lora_r,
            "alpha": config.lora_alpha,
            "dropout": config.lora_dropout,
            "target_modules": config.target_modules,
        },
        "training_config": config.__dict__,
        "train_samples": len(train_examples),
        "eval_samples": len(eval_examples),
        "trained_at": datetime.now().isoformat(),
        "final_eval_loss": trainer.state.log_history[-1].get("eval_loss", 0.0),
    }

    metadata_path = Path(config.output_dir) / "training_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Training completed! Model saved to {config.output_dir}")
    return model, tokenizer, trainer


def main():
    """Main training entry point"""

    # Load existing telemetry episodes (om de finns)
    episodes_file = DATA_DIR / "rl" / "night_test_episodes.jsonl"

    if not episodes_file.exists():
        logger.error(f"No episodes file found at {episodes_file}")
        logger.info("Run: python3 services/rl/build_dataset.py first")
        return

    # Load episodes
    training_data = []
    with open(episodes_file, "r") as f:
        for line in f:
            if line.strip():
                training_data.append(json.loads(line))

    if not training_data:
        logger.error("No training data found!")
        return

    logger.info(f"Loaded {len(training_data)} episodes from {episodes_file}")

    # Prepare for tool selection training
    tool_examples = prepare_training_data(training_data)

    if len(tool_examples) < 10:
        logger.warning(
            f"Very few training examples ({len(tool_examples)}), results may be poor"
        )

    # Training config
    config = TrainingConfig()
    config.output_dir = str(WEIGHTS_DIR / "toolselector-lora-v1")

    # Train!
    train_toolselector(config, tool_examples)

    logger.info("🎉 ToolSelector LoRA training complete!")


if __name__ == "__main__":
    main()
