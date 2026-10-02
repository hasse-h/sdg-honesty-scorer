"""OpenRouter chat-completions client for extraction tasks."""

from __future__ import annotations

import http.client
import json
import os
import socket
import time
from collections.abc import Mapping
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    INVESTMENT_SYSTEM_PROMPT,
    INVESTMENT_USER_TEMPLATE,
    SAFE_OPENROUTER_HOSTS,
    SDG_MENTIONS_SYSTEM_PROMPT,
    SDG_MENTIONS_USER_TEMPLATE,
)
from .models import JsonDict, normalize_investment_categorization, normalize_sdg_mentions
from .secrets import load_openrouter_api_key

OpenCallable = Callable[..., Any]


class AIClient:
    """OpenRouter chat-completions client for SDG and investment extraction."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_tokens: Optional[int] = None,
        opener: Optional[OpenCallable] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        _validate_openrouter_model_route(self.model)
        self.api_key = load_openrouter_api_key(api_key=api_key)
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
        if not _allow_unsafe_openrouter_base_url():
            _validate_openrouter_base_url(self.base_url)
        self.site_url = site_url if site_url is not None else os.getenv("OPENROUTER_SITE_URL", "")
        self.app_name = app_name if app_name is not None else os.getenv("OPENROUTER_APP_NAME", "SDG Honesty Scorer")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("OPENROUTER_MAX_TOKENS", "8192"))
        self._opener = opener or urlopen
        self._sleep = sleep

    def fetch_sdg_mentions(self, text: str) -> list[JsonDict]:
        """Extract SDG mention records from report text."""
        result = self._chat_json(
            system_prompt=SDG_MENTIONS_SYSTEM_PROMPT,
            user_prompt=_render_report_template(SDG_MENTIONS_USER_TEMPLATE, text),
        )
        return normalize_sdg_mentions(result)

    def categorize_investments(self, text: str, report_year: str = "") -> JsonDict:
        """Categorize investments and instruments mentioned in report text."""
        result = self._chat_json(
            system_prompt=INVESTMENT_SYSTEM_PROMPT,
            user_prompt=_render_report_template(INVESTMENT_USER_TEMPLATE, text),
        )
        return normalize_investment_categorization(result, report_year)

    def _chat_json(self, system_prompt: str, user_prompt: str) -> JsonDict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        last_error: BaseException | None = None
        for attempt in range(self.max_retries + 1):
            response = self._request_with_retries(payload)
            try:
                return _parse_chat_json_response(response)
            except (json.JSONDecodeError, RuntimeError) as exc:
                if not _retryable_model_json_error(exc) or attempt >= self.max_retries:
                    raise
                last_error = exc
                self._sleep(2**attempt)
        raise RuntimeError("OpenRouter model returned invalid JSON after retries") from last_error

    def _request_with_retries(self, payload: JsonDict) -> JsonDict:
        body = json.dumps(payload).encode("utf-8")
        headers = self._headers()
        last_error: Optional[BaseException] = None
        for attempt in range(self.max_retries + 1):
            request = Request(self.base_url, data=body, headers=headers, method="POST")
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    return _load_json_response(response.read().decode("utf-8"))
            except HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    raise RuntimeError(f"OpenRouter HTTP {exc.code}: {error_body}") from exc
                last_error = exc
            except json.JSONDecodeError as exc:
                if attempt >= self.max_retries:
                    raise RuntimeError(f"OpenRouter response was not valid JSON: {exc}") from exc
                last_error = exc
            except (
                URLError,
                TimeoutError,
                ConnectionResetError,
                http.client.RemoteDisconnected,
                http.client.IncompleteRead,
                socket.timeout,
            ) as exc:
                if attempt >= self.max_retries:
                    reason = exc.reason if isinstance(exc, URLError) else str(exc)
                    raise RuntimeError(f"OpenRouter request failed: {reason}") from exc
                last_error = exc
            self._sleep(2**attempt)
        raise RuntimeError("OpenRouter request failed after retries") from last_error

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers


def _render_report_template(template: str, report_text: str) -> str:
    """Insert report text into a prompt template that contains JSON braces."""
    return template.replace("{report_text}", report_text)


def _allow_unsafe_openrouter_base_url() -> bool:
    """Return whether non-OpenRouter base URLs are explicitly enabled."""
    return os.getenv("OPENROUTER_ALLOW_UNSAFE_BASE_URL", "").lower() in {"1", "true", "yes"}


def _validate_openrouter_base_url(base_url: str) -> None:
    """Ensure OpenRouter credentials are only sent to the expected HTTPS host."""
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname not in SAFE_OPENROUTER_HOSTS:
        raise RuntimeError(
            "OPENROUTER_BASE_URL must be an https://openrouter.ai URL unless OPENROUTER_ALLOW_UNSAFE_BASE_URL=1 is set"
        )


def _validate_openrouter_model_route(model: str) -> None:
    """Prevent proprietary GPT, Claude, and Gemini models from being routed through OpenRouter."""
    normalized = model.strip().lower()
    if normalized.startswith("openai/") and not normalized.startswith("openai/gpt-oss"):
        raise RuntimeError("OpenAI models must use the direct OpenAI path; OpenRouter is only for open-weight models")
    if normalized.startswith("anthropic/") or normalized.startswith("claude") or "/claude" in normalized:
        raise RuntimeError(
            "Claude models must use the direct Anthropic path; OpenRouter is only for open-weight models"
        )
    if normalized.startswith("google/gemini") or normalized.startswith("gemini") or "/gemini" in normalized:
        raise RuntimeError("Gemini models must use the direct Google path; OpenRouter is only for open-weight models")


def _load_json_response(text: str) -> JsonDict:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object response, got {type(value).__name__}")
    if "error" in value:
        raise RuntimeError(f"OpenRouter error: {value['error']}")
    return value


def _parse_chat_json_response(response: JsonDict) -> JsonDict:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"OpenRouter response did not contain choices: {response}")
    message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
    if not isinstance(message, Mapping):
        raise RuntimeError(f"OpenRouter choice did not contain a message: {choices[0]}")
    content = _message_content_to_text(message.get("content"))
    return _load_json_object(content)


def _retryable_model_json_error(exc: BaseException) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True
    message = str(exc)
    retryable_fragments = (
        "Model response did not contain a JSON object",
        "Model response contained an incomplete JSON object",
        "Expected model to return a JSON object",
        "Model response did not contain message content",
    )
    return any(fragment in message for fragment in retryable_fragments)


def _message_content_to_text(content: Any) -> str:
    if content is None:
        raise RuntimeError("Model response did not contain message content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    raise RuntimeError(f"Unsupported message content type: {type(content).__name__}")


def _load_json_object(text: str) -> JsonDict:
    cleaned = _strip_code_fence(text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        value = json.loads(_extract_first_json_object(cleaned))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected model to return a JSON object, got {type(value).__name__}")
    return value


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    first_newline = text.find("\n")
    if first_newline == -1:
        return text
    body = text[first_newline + 1 :]
    if body.endswith("```"):
        body = body[:-3]
    return body.strip()


def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise RuntimeError("Model response did not contain a JSON object")
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise RuntimeError("Model response contained an incomplete JSON object")
