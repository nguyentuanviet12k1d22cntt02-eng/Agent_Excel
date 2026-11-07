"""Gọi LLM qua API tương thích OpenAI (Inception mercury-3, T0.4) với structured output `json_schema`.

Dùng httpx (đã có sẵn), không cần SDK riêng. Desktop không gọi tới đây: chỉ Backend gọi LLM (quy tắc 3.5).
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class LLMError(RuntimeError):
    """Không lấy được kết quả từ LLM (mạng, key, quota, trả về không phải JSON)."""


@dataclass(frozen=True)
class LLMResponse:
    data: Any
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int


class LLMClient(Protocol):
    model: str

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], schema_name: str
    ) -> LLMResponse: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        max_tokens: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._max_tokens = max_tokens
        self._client = httpx.Client(
            timeout=timeout, transport=transport, headers={"Authorization": f"Bearer {api_key}"}
        )

    def complete_json(self, system: str, user: str, schema: dict[str, Any], schema_name: str) -> LLMResponse:
        structured = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        }
        start = time.perf_counter()
        response = self._post(system, user, structured)
        if response.status_code == httpx.codes.BAD_REQUEST and "response_format" in response.text:
            # Nhà cung cấp không nhận lược đồ ở chế độ strict: chuyển sang JSON tự do, đưa lược đồ vào prompt
            logger.warning("LLM không nhận json_schema, chuyển sang json_object")
            schema_text = json.dumps(schema, ensure_ascii=False)
            system = f"{system}\n\nTrả về đúng một đối tượng JSON theo lược đồ:\n{schema_text}"
            response = self._post(system, user, {"type": "json_object"})
        duration_ms = int((time.perf_counter() - start) * 1000)
        self._raise_for_status(response)
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"] or ""
            data = json.loads(_FENCE.sub("", content.strip()))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(f"AI trả về không phải JSON hợp lệ: {exc}") from exc
        usage = body.get("usage") or {}
        return LLMResponse(
            data, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0), duration_ms
        )

    def _post(self, system: str, user: str, response_format: dict[str, Any]) -> httpx.Response:
        body = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": response_format,
        }
        try:
            return self._client.post(self._url, json=body)
        except httpx.TimeoutException as exc:
            raise LLMError("Dịch vụ AI không trả lời kịp (quá thời gian chờ)") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Không gọi được dịch vụ AI: {type(exc).__name__}") from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < httpx.codes.BAD_REQUEST:
            return
        if response.status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN):
            raise LLMError("API key của dịch vụ AI không hợp lệ hoặc hết hạn")
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise LLMError("Dịch vụ AI đang giới hạn số lượt gọi, thử lại sau")
        raise LLMError(f"Dịch vụ AI báo lỗi {response.status_code}: {response.text[:200]}")
