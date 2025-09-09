#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOConfig, DPOTrainer


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass
    return rows


def chat_wrap(tokenizer, prompt: str) -> str:
    # Skapa en system+user prompt i modellens chat-template
    msgs = [{"role": "user", "content": prompt}]
    try:
        return tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        # Fallback: rå prompt + "Assistant:"
        return f"User: {prompt}\nAssistant:"


def make_dataset(tokenizer, path: Path, use_chat_template: bool) -> Dataset:
    data = []
    for r in read_jsonl(path):
        p = r["prompt"]
        if use_chat_template:
            p = chat_wrap(tokenizer, p)
        data.append(
            {
                "prompt": p,
                "chosen": r["chosen"],
                "rejected": r["rejected"],
            }
        )
    return Dataset.from_list(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--train", default=None, help="override train_file")
    ap.add_argument("--val", default=None, help="override val_file")
    ap.add_argument("--out", default=None, help="override output_dir")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    model_name = cfg["model_name"]
    output_dir = args.out or cfg["output_dir"]
    train_file = Path(args.train or cfg["train_file"])
    val_file = Path(args.val or cfg["val_file"])

    # tokenizer
    tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tok.pad_token is None and cfg.get("eos_token_fallback", True):
        tok.pad_token = tok.eos_token

    # model (MPS kräver float32, uppdaterad parameter)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float32,  # uppdaterad från torch_dtype
    )

    # datasets
    use_chat_template = bool(cfg.get("use_chat_template", True))
    train_ds = make_dataset(tok, train_file, use_chat_template)
    eval_ds = make_dataset(tok, val_file, use_chat_template)

    # DPOConfig (ersätter TrainingArguments för DPO)
    training_args = DPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=cfg["per_device_train_batch_size"],
        per_device_eval_batch_size=cfg.get("per_device_eval_batch_size", 1),
        gradient_accumulation_steps=cfg["gradient_accumulation_steps"],
        learning_rate=cfg["learning_rate"],
        max_steps=cfg.get("max_steps", 2000),
        logging_steps=cfg.get("logging_steps", 25),
        eval_steps=cfg.get("eval_steps", 100),
        save_steps=cfg.get("save_steps", 200),
        save_total_limit=cfg.get("save_total_limit", 2),
        warmup_ratio=cfg.get("warmup_ratio", 0.06),
        weight_decay=cfg.get("weight_decay", 0.0),
        report_to=cfg.get("report_to", "none"),
        fp16=cfg.get("fp16", True),
        bf16=cfg.get("bf16", False),
        gradient_checkpointing=cfg.get("gradient_checkpointing", True),
        # DPO-specifikt
        beta=cfg.get("beta", 0.2),
        loss_type=cfg.get("loss_type", "ipo"),
        reference_free=True,
        # Sekvensbudget
        max_length=cfg.get("max_length", 2048),
        max_prompt_length=int(cfg.get("max_length", 2048) * 0.6),
        max_completion_length=int(
            cfg.get("max_length", 2048) * 0.4
        ),  # ny parameter namn
    )

    # LoRA config för DPOTrainer
    peft_cfg = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        target_modules=cfg.get(
            "target_modules",
            [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        ),
        bias="none",
        task_type="CAUSAL_LM",
    )

    # DPOTrainer (TRL 0.11.4 kräver processing_class=)
    trainer = DPOTrainer(
        model=model,
        args=training_args,
        processing_class=tok,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=peft_cfg,  # TRL hanterar LoRA åt oss
    )

    # vissa modeller behöver detta för checkpointing på MPS
    model.config.use_cache = cfg.get("use_cache", False)

    trainer.train()
    trainer.save_model(output_dir)
    tok.save_pretrained(output_dir)
    print("✅ Träning klar →", output_dir)


if __name__ == "__main__":
    main()
