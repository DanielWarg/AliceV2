import hashlib
import pathlib

# Default system prompt path
PROMPT_PATH = pathlib.Path("config/system_prompt.txt")


def get_system_prompt_hash() -> str:
    """Calculate SHA256 hash of system prompt"""
    try:
        if PROMPT_PATH.exists():
            system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
            return hashlib.sha256(system_prompt.encode()).hexdigest()
        else:
            # Fallback to default prompt
            default_prompt = "You are Alice, a helpful AI assistant."
            return hashlib.sha256(default_prompt.encode()).hexdigest()
    except Exception:
        # Return hash of error state
        return hashlib.sha256(b"error_reading_prompt").hexdigest()


# Global hash for easy access
SYSTEM_PROMPT_SHA256 = get_system_prompt_hash()
