#!/usr/bin/env python3
"""OpenRouter API client for Moltbook Observatory - uses Kimi K2.5."""

import os
import json
import requests
from pathlib import Path

# Load API key from various sources
OPENROUTER_API_KEY = None

# Source 1: Environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Source 2: .openclaw/.env file
if not OPENROUTER_API_KEY:
    OPENCLAW_ENV = Path.home() / ".openclaw" / ".env"
    if OPENCLAW_ENV.exists():
        with open(OPENCLAW_ENV, "r") as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    OPENROUTER_API_KEY = line.strip().split("=", 1)[1]
                    break

# Source 3: OpenClaw auth-profiles.json (where openclaw configure stores keys)
if not OPENROUTER_API_KEY:
    AUTH_PROFILES = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
    if AUTH_PROFILES.exists():
        try:
            import json
            with open(AUTH_PROFILES, "r") as f:
                profiles = json.load(f)
            # Look for openrouter profile
            for profile_name, profile_data in profiles.get("profiles", {}).items():
                if profile_data.get("provider") == "openrouter" and profile_data.get("key"):
                    OPENROUTER_API_KEY = profile_data["key"]
                    break
        except (json.JSONDecodeError, KeyError):
            pass

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Available models (K2.5 is default - better reasoning, 262K context)
MODELS = {
    "k2.5": "moonshotai/kimi-k2.5",        # Best quality, 262K context
    "k2": "moonshotai/kimi-k2",            # Standard, 131K context
    "k2-thinking": "moonshotai/kimi-k2-thinking",  # Extended thinking
    "k2-free": "moonshotai/kimi-k2:free",  # Free tier, 32K context
}
DEFAULT_MODEL = MODELS["k2.5"]


def call_kimi(prompt: str, system_prompt: str = None, model: str = DEFAULT_MODEL,
               max_tokens: int = 4000, max_retries: int = 3) -> dict:
    """
    Call Kimi via OpenRouter API with retry logic.

    Note: K2.5 uses reasoning tokens, so needs higher max_tokens.
    Default increased to 4000 for K2.5 compatibility.

    Args:
        max_retries: Number of retries for transient errors (default: 3)
    """
    import time

    if not OPENROUTER_API_KEY:
        return {"error": "No OPENROUTER_API_KEY found"}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://noosphereproject.com",
        "X-Title": "Noosphere Project"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            message = data["choices"][0]["message"]
            content = message.get("content", "")

            # K2.5 may have reasoning in separate field
            reasoning = message.get("reasoning", "")

            return {
                "content": content,
                "reasoning": reasoning,  # K2.5 thinking process
                "model": data.get("model", model),
                "usage": data.get("usage", {}),
                "cost": data.get("usage", {}).get("cost", 0)
            }
        except requests.Timeout:
            last_error = "Request timeout (120s)"
            # Retry on timeout
        except requests.RequestException as e:
            last_error = f"Network error: {e}"
            # Retry on network errors
            if response is not None and response.status_code in (400, 401, 403, 404):
                # Don't retry on client errors
                return {"error": last_error}
        except Exception as e:
            return {"error": str(e)}

        # Exponential backoff before retry
        if attempt < max_retries - 1:
            wait_time = (2 ** attempt) + 1  # 2, 3, 5 seconds
            time.sleep(wait_time)

    return {"error": f"{last_error} (after {max_retries} retries)"}


def test_connection(model: str = None):
    """Test if OpenRouter/Kimi connection works."""
    test_model = model or DEFAULT_MODEL
    print(f"Testing model: {test_model}")

    result = call_kimi(
        "Respond with exactly: 'Kimi K2.5 connected successfully'",
        model=test_model,
        max_tokens=20
    )

    if "error" in result:
        print(f"[ERROR] {result['error']}")
        return False

    print(f"[OK] Response: {result['content']}")
    print(f"[OK] Model used: {result.get('model', 'unknown')}")
    print(f"[OK] Tokens: {result.get('usage', {})}")
    return True


if __name__ == "__main__":
    print("=== Kimi K2.5 Connection Test ===\n")
    test_connection()
