import json
import os

MEMORY_PATH = "memory/memory.json"


def _empty_memory() -> dict:
    return {
        "identity": {},
        "preferences": {},
        "relationships": {},
        "emotional_state": {},
    }


def load_memory() -> dict:
    if not os.path.exists(MEMORY_PATH):
        return _empty_memory()
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"\033[31m[ERROR] Failed to load memory: {e}\033[0m")
        return _empty_memory()


def save_memory(memory: dict):
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def update_memory(memory_update: dict):
    if not isinstance(memory_update, dict):
        return

    memory = load_memory()
    for category, values in memory_update.items():
        if category in memory and isinstance(values, dict):
            memory[category].update(values)

    save_memory(memory)
