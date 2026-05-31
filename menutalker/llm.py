from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


class LLMProviderError(RuntimeError):
    """Raised when an external LLM provider returns a user-actionable error."""


@dataclass
class LLMSettings:
    provider: str = "mock"
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    include_images: bool = False

    @classmethod
    def from_values(
        cls,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        include_images: bool | None = None,
    ) -> "LLMSettings":
        selected_provider = (provider or os.getenv("LLM_PROVIDER") or "mock").strip().lower()
        selected_model = (model or os.getenv("LLM_MODEL") or "").strip()
        selected_base_url = (base_url or os.getenv("LLM_BASE_URL") or "").strip()
        selected_api_key = (api_key or os.getenv("LLM_API_KEY") or "").strip()
        if selected_provider == "google" and not selected_api_key:
            selected_api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
        if include_images is None:
            include_images = os.getenv("LLM_INCLUDE_IMAGES", "false").lower() in {"1", "true", "yes"}
        return cls(selected_provider, selected_model, selected_base_url, selected_api_key, include_images)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM output must be a JSON object.")
    return parsed


def _image_content(image_paths: list[Path]) -> list[dict[str, Any]]:
    content = []
    for image_path in image_paths:
        data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{data}"},
            }
        )
    return content


def _chat_completion_url(settings: LLMSettings) -> str:
    if settings.provider == "hf":
        base_url = settings.base_url or "https://router.huggingface.co/v1"
    elif settings.provider == "ollama":
        base_url = settings.base_url or "http://localhost:11434/v1"
    else:
        base_url = settings.base_url
    return base_url.rstrip("/") + "/chat/completions"


def _google_generate_content_url(settings: LLMSettings) -> str:
    model = settings.model or "gemini-flash-latest"
    base_url = (settings.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    if base_url.endswith(":generateContent"):
        return base_url
    if "/models/" in base_url:
        return base_url + ":generateContent"
    if base_url.endswith("/models"):
        return f"{base_url}/{model}:generateContent"
    return f"{base_url}/models/{model}:generateContent"


def _provider_error_message(provider: str, response: requests.Response) -> str:
    detail = response.text.strip()
    try:
        payload = response.json()
        error = payload.get("error", {})
        if isinstance(error, dict):
            detail = error.get("message") or detail
    except ValueError:
        pass
    if len(detail) > 800:
        detail = detail[:797] + "..."
    return f"{provider} API error {response.status_code}: {detail}"


def _google_parts_from_text(text: str) -> list[dict[str, Any]]:
    return [{"text": text}]


def _google_parts_from_images(image_paths: list[Path]) -> list[dict[str, Any]]:
    parts = []
    for image_path in image_paths:
        data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        parts.append(
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": data,
                }
            }
        )
    return parts


def _google_history(history: list[dict[str, str]] | None) -> list[dict[str, Any]]:
    contents = []
    for entry in history or []:
        role = entry.get("role")
        text = entry.get("content", "")
        if role not in {"user", "assistant"} or not text:
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )
    return contents


def _call_google_generate_content(
    settings: LLMSettings,
    system_prompt: str,
    user_prompt: str,
    history: list[dict[str, str]] | None,
    image_paths: list[Path] | None,
    temperature: float,
) -> str:
    if not settings.api_key:
        raise ValueError("GOOGLE_API_KEY, GEMINI_API_KEY, LLM_API_KEY, or the API key field is required for Google provider.")

    url = _google_generate_content_url(settings)

    user_parts = _google_parts_from_text(user_prompt)
    if settings.include_images and image_paths:
        user_parts = [*_google_parts_from_images(image_paths), *user_parts]

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [
            *_google_history(history),
            {
                "role": "user",
                "parts": user_parts,
            },
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": settings.api_key,
            },
            json=payload,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise LLMProviderError(f"Google API request failed: {exc}") from exc

    if not response.ok:
        raise LLMProviderError(_provider_error_message("Google", response))

    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMProviderError("Google API returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def call_chat_completion(
    settings: LLMSettings,
    system_prompt: str,
    user_prompt: str,
    history: list[dict[str, str]] | None = None,
    image_paths: list[Path] | None = None,
    temperature: float = 0.1,
) -> str:
    if settings.provider == "mock":
        raise RuntimeError("Mock provider does not call an external LLM.")
    if settings.provider == "google":
        return _call_google_generate_content(settings, system_prompt, user_prompt, history, image_paths, temperature)
    if not settings.model:
        raise ValueError("LLM_MODEL or the model field is required for external LLM providers.")
    if settings.provider in {"hf", "openai_compatible"} and not settings.api_key:
        raise ValueError("LLM_API_KEY or the API key field is required for this provider.")
    if settings.provider not in {"hf", "openai_compatible", "ollama"}:
        raise ValueError(f"Unsupported LLM provider: {settings.provider}")

    user_content: str | list[dict[str, Any]]
    if settings.include_images and image_paths:
        user_content = [{"type": "text", "text": user_prompt}, *_image_content(image_paths)]
    else:
        user_content = user_prompt

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_content})

    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    try:
        response = requests.post(
            _chat_completion_url(settings),
            headers=headers,
            json={
                "model": settings.model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise LLMProviderError(f"{settings.provider} API request failed: {exc}") from exc

    if not response.ok:
        raise LLMProviderError(_provider_error_message(settings.provider, response))

    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def find_meal(text: str) -> str | None:
    match = re.search(r"<MEAL>(.*?)</MEAL>", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()
