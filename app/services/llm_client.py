import json
import logging
import time
from typing import Any
from urllib import request

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Small OpenAI-compatible client.

    The app remains usable without an API key because callers provide rule-based
    fallbacks when this client returns empty results.
    """

    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.model = settings.llm_model

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def chat_text(self, system_prompt: str, user_prompt: str) -> str:
        logger.info(
            "llm.call.start configured=%s model=%s system_chars=%s user_chars=%s system_preview=%r user_preview=%r",
            self.configured,
            self.model or "<unset>",
            len(system_prompt),
            len(user_prompt),
            _preview(system_prompt, 240),
            _preview(user_prompt, 800),
        )
        started = time.perf_counter()
        payload = self._request_payload(system_prompt, user_prompt)
        data = self._post(payload)
        content = _extract_content(data)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "llm.response.done elapsed_ms=%s content_chars=%s content_preview=%r",
            elapsed_ms,
            len(content),
            _preview(content, 1000),
        )
        return content

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        text = self.chat_text(system_prompt, user_prompt)
        if not text:
            logger.info("llm.chat_json.empty_response")
            return {}
        try:
            parsed = json.loads(text)
            logger.info("llm.chat_json.parsed mode=direct keys=%s", list(parsed.keys()))
            return parsed
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                    logger.info("llm.chat_json.parsed mode=substring keys=%s", list(parsed.keys()))
                    return parsed
                except json.JSONDecodeError:
                    logger.warning("llm.chat_json.parse_failed mode=substring")
                    return {}
        logger.warning("llm.chat_json.parse_failed mode=direct")
        return {}

    def _request_payload(self, system_prompt: str, user_prompt: str) -> bytes:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        return json.dumps(body).encode("utf-8")

    def _post(self, payload: bytes) -> dict[str, Any]:
        if not self.configured:
            logger.info("llm.call.skip reason=not_configured")
            return {}

        url = f"{self.base_url}/chat/completions"
        logger.info("llm.transport.send model=%s payload_bytes=%s", self.model, len(payload))
        req = request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "llm.transport.done elapsed_ms=%s raw_chars=%s raw_preview=%r",
                    elapsed_ms,
                    len(raw),
                    _preview(raw, 1000),
                )
                return json.loads(raw)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception("llm.transport.failed elapsed_ms=%s error=%s", elapsed_ms, exc.__class__.__name__)
            return {}


def _extract_content(data: dict[str, Any]) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _preview(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
