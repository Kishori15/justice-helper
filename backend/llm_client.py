"""
Unified LLM Client for JusticeHelper.
Implements ARCHITECTURE.md §4, §4.1 and PROJECT_STRUCTURE.md §2.

Primary: Google Gemini API (with key rotation support).
Fallback: Groq / Together AI (invoked strictly on Gemini errors or 429 quota exhaustion).
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from backend.config import (
    FALLBACK_LLM_API_KEY,
    FALLBACK_LLM_PROVIDER,
    FALLBACK_MODEL,
    GEMINI_API_KEYS,
    GEMINI_MODEL,
)

logger = logging.getLogger("justicehelper.llm")


def clean_json_text(text: str) -> str:
    """
    Strips markdown code blocks ```json ... ``` if present.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class LLMClient:
    """
    Resilient LLM client with key rotation and automatic fallback.
    """
    def __init__(
        self,
        gemini_keys: Optional[List[str]] = None,
        gemini_model: str = GEMINI_MODEL,
        fallback_provider: str = FALLBACK_LLM_PROVIDER,
        fallback_key: str = FALLBACK_LLM_API_KEY,
        fallback_model: str = FALLBACK_MODEL,
    ):
        self.gemini_keys = gemini_keys or GEMINI_API_KEYS
        self.gemini_model_name = gemini_model
        self.fallback_provider = fallback_provider.lower()
        self.fallback_key = fallback_key
        self.fallback_model = fallback_model
        self._current_key_idx = 0

    def _get_next_gemini_key(self) -> Optional[str]:
        if not self.gemini_keys:
            return None
        key = self.gemini_keys[self._current_key_idx % len(self.gemini_keys)]
        self._current_key_idx += 1
        return key

    def _call_gemini(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        """
        Calls Google Gemini API with system instructions and JSON output mode.
        """
        key = self._get_next_gemini_key()
        if not key:
            raise ValueError("No Gemini API key configured.")

        import google.generativeai as genai

        genai.configure(api_key=key)
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name=self.gemini_model_name,
            system_instruction=system_prompt,
            generation_config=generation_config
        )

        response = model.generate_content(user_prompt)
        if not response.text:
            raise ValueError("Gemini returned empty response text.")
        return response.text

    def _call_fallback(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        """
        Calls secondary fallback provider (Groq or Together) on Gemini failure/429.
        """
        if not self.fallback_key:
            raise ValueError(f"Fallback provider '{self.fallback_provider}' requested but no API key configured.")

        logger.warning(f"Invoking fallback provider '{self.fallback_provider}'...")

        if self.fallback_provider == "groq":
            from groq import Groq
            client = Groq(api_key=self.fallback_key)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            kwargs = {
                "model": self.fallback_model,
                "messages": messages,
                "temperature": 0.1,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            chat_completion = client.chat.completions.create(**kwargs)
            return chat_completion.choices[0].message.content
        elif self.fallback_provider == "together":
            from together import Together
            client = Together(api_key=self.fallback_key)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"} if json_mode else None
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Unsupported fallback provider: {self.fallback_provider}")

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Executes a JSON-constrained LLM request.
        Attempts Gemini first; falls back to secondary provider upon error or 429.
        """
        raw_text = ""
        gemini_error = None

        if self.gemini_keys:
            try:
                raw_text = self._call_gemini(system_prompt, user_prompt, json_mode=True)
            except Exception as e:
                gemini_error = e
                logger.warning(f"Gemini API call failed: {e}. Attempting fallback...")

        if not raw_text:
            if self.fallback_key:
                try:
                    raw_text = self._call_fallback(system_prompt, user_prompt, json_mode=True)
                except Exception as fb_err:
                    raise RuntimeError(f"Both Gemini ({gemini_error}) and fallback provider ({fb_err}) failed.")
            else:
                raise RuntimeError(f"Gemini API call failed ({gemini_error}) and no fallback API key configured.")

        cleaned = clean_json_text(raw_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as decode_err:
            raise ValueError(f"Failed to parse LLM output as JSON: {decode_err}\nRaw text: {raw_text}")

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes a text generation request with fallback.
        """
        if self.gemini_keys:
            try:
                return self._call_gemini(system_prompt, user_prompt, json_mode=False)
            except Exception as e:
                logger.warning(f"Gemini call failed: {e}. Attempting fallback...")

        if self.fallback_key:
            return self._call_fallback(system_prompt, user_prompt, json_mode=False)
        raise RuntimeError("No working LLM provider available.")


# Global client instance
llm_client = LLMClient()
