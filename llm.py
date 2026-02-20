import json
import re
import sys
from pathlib import Path

import requests

from memory.config_manager import get_url


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
PROMPT_PATH = BASE_DIR / "prompts" / "prompt.txt"


def load_system_prompt() -> str:
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"prompt.txt couldn't be loaded: {e}")
        return (
            "You are Ulysses, a helpful AI assistant. Output strictly in JSON format."
        )


SYSTEM_PROMPT = load_system_prompt()


def safe_json_parse(text: str) -> dict | None:
    if text is None:
        return None

    text = str(text).strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except Exception as e:
            print(
                f"\033[31m[ERROR] JSON Parsing Failed on extracted string: {e}\033[0m"
            )
            print(f"\033[33m[DEBUG] Failed Text: {json_str[:150]}...\033[0m")
            return None
    else:
        print("\033[31m[ERROR] No valid JSON object found in LLM response.\033[0m")
        print(f"\033[33m[DEBUG] Raw Output: {text[:150]}...\033[0m")
        return None


def get_llm_output(user_text, memory_block=None, history=""):

    url = get_url()

    user_prompt = f"""User message: "{user_text}"
    
Known user memory: {json.dumps(memory_block) if memory_block else "None"}
Recent History: {history}"""

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]

            parsed = safe_json_parse(content)

            if parsed:
                return parsed

            return {"intent": "chat", "text": content}

        else:
            print(f"LM Studio Status Error: {response.status_code}")
            return {
                "intent": "chat",
                "text": "Sir, my local brain encountered an error while processing.",
            }

    except Exception as e:
        print(f"LLM Connection Error: {e}")
        return {
            "intent": "chat",
            "text": "Sir, I'm having trouble connecting to my brain.",
        }
