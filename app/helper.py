import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class llmRequester:
    def __init__(self):
        self.api_key = os.getenv("GPT_KEY")
        if not self.api_key:
            raise ValueError("GPT_KEY not found in .env file")

        self.client = OpenAI(api_key=self.api_key)

        # Defaults (override via setters if you want)
        self.model = "gpt-4o-mini"
        self.temperature = 0.1
        self.max_tokens = 512

        logging.info("GPT client initialized successfully")

    # ---------- NEW: chat() to match how you're calling it ----------
    def chat(self, messages, response_format=None, model=None, temperature=None, max_tokens=None):
        """
        Wrapper for chat.completions.create that supports response_format json_schema.

        If response_format is provided (e.g. json_schema), this returns a parsed Python object (dict).
        Otherwise returns plain text.
        """
        used_model = model or self.model
        used_temp = self.temperature if temperature is None else temperature
        used_max = self.max_tokens if max_tokens is None else max_tokens

        try:
            kwargs = dict(
                model=used_model,
                messages=messages,
                temperature=used_temp,
                max_tokens=used_max,
            )
            if response_format is not None:
                kwargs["response_format"] = response_format

            resp = self.client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()

            # If caller asked for structured output, parse JSON
            if response_format is not None:
                return self._safe_json_loads(content)

            return content

        except Exception as e:
            logging.error(f"Error calling OpenAI API in chat(): {e}")
            raise

    def _safe_json_loads(self, s: str):
        """
        Parse JSON content robustly. Handles occasional code-fences.
        """
        s = s.strip()

        # Remove common code-fence wrappers if present
        if s.startswith("```"):
            # strip ```json ... ```
            s = s.split("\n", 1)[-1]
            if s.endswith("```"):
                s = s.rsplit("```", 1)[0]
            s = s.strip()

        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON. Raw content was:\n{s}")
            raise

    # ---------- Existing interface you already use ----------
    def run_llama(self, prompt: str, text: str) -> str:
        """
        Keeps your old interface: fills {text} and returns plain string answer.
        """
        full_prompt = prompt.replace("{text}", text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes articles about technology and its societal impacts."
                    },
                    {"role": "user", "content": full_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return (response.choices[0].message.content or "").strip()

        except Exception as e:
            logging.error(f"Error calling OpenAI API in run_llama(): {e}")
            raise

    # ---------- Optional setters ----------
    def set_model(self, model: str):
        self.model = model
        logging.info(f"Model changed to: {model}")

    def set_temperature(self, temperature: float):
        self.temperature = temperature

    def set_max_tokens(self, max_tokens: int):
        self.max_tokens = max_tokens


# Backwards compatibility - if other code expects these classes
class TogetherLLM:
    """Deprecated: Use llmRequester instead"""
    def __init__(self, *args, **kwargs):
        logging.warning("TogetherLLM is deprecated. Use llmRequester instead.")
        raise NotImplementedError("Please use llmRequester class instead")
