"""Client LLM: trả lời hỏng (rỗng, bị cắt, không phải JSON) là lỗi gọi lại được, vẫn giữ số token."""

import json

import httpx
import pytest

from tutor_backend.ai.llm_client import LLMError, LLMOutputError, OpenAICompatibleClient


def client(content: str | None, finish_reason: str = "stop", status: int = 200) -> OpenAICompatibleClient:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 300},
        }
        return httpx.Response(status, json=body)

    return OpenAICompatibleClient(
        base_url="https://llm.test/v1",
        api_key="khoa-test",
        model="mercury-3",
        timeout=5,
        max_tokens=100,
        transport=httpx.MockTransport(handler),
    )


def ask(llm: OpenAICompatibleClient):
    return llm.complete_json("system", "user", {"type": "object"}, "plan")


def test_valid_json_is_parsed_with_usage():
    response = ask(client(json.dumps({"steps": []})))
    assert (response.data, response.prompt_tokens, response.completion_tokens) == ({"steps": []}, 1200, 300)


@pytest.mark.parametrize(
    ("content", "finish_reason", "message"),
    [
        ("", "stop", "AI trả về nội dung rỗng"),
        (None, "stop", "AI trả về nội dung rỗng"),
        ('{"steps": [', "length", "AI viết quá dài nên bị cắt giữa chừng"),
        ("Hmm, let me reconsider…", "stop", "AI trả về không phải JSON hợp lệ"),
    ],
)
def test_unusable_answers_are_retryable_and_keep_token_counts(content, finish_reason, message):
    with pytest.raises(LLMOutputError) as caught:
        ask(client(content, finish_reason))
    assert str(caught.value).startswith(message)
    assert (caught.value.prompt_tokens, caught.value.completion_tokens) == (1200, 300)


def test_http_errors_stay_fatal():
    with pytest.raises(LLMError) as caught:
        ask(client("{}", status=401))
    assert not isinstance(caught.value, LLMOutputError)
