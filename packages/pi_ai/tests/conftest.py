
import httpx
import pytest
import respx


class MockResponses:
    MOCK_OPENAI_CHAT_COMPLETION = {
        "id": "chatcmpl-test123",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None,
            }
        ],
    }

    MOCK_OPENAI_TEXT_DELTA = {
        "id": "chatcmpl-test123",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "delta": {"content": "Hello, I am an AI assistant."},
                "finish_reason": None,
            }
        ],
    }

    MOCK_OPENAI_DONE = {
        "id": "chatcmpl-test123",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }

    MOCK_ANTHROPIC_MESSAGE_START = {
        "type": "message_start",
        "message": {
            "id": "msg_test123",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "claude-3-5-sonnet-20241022",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }

    MOCK_ANTHROPIC_CONTENT_BLOCK_START = {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""},
    }

    MOCK_ANTHROPIC_CONTENT_DELTA = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "Hello!"},
    }

    MOCK_ANTHROPIC_MESSAGE_STOP = {
        "type": "message_stop",
    }

    MOCK_GOOGLE_RESPONSE = {
        "candidates": [
            {
                "content": {
                    "parts": [{"type": "text", "text": "Hello from Gemini!"}],
                    "role": "model",
                },
                "finishReason": "STOP",
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            }
        ],
    }


def format_sse(data: dict) -> str:
    import json

    return f"data: {json.dumps(data)}\n\n"


@pytest.fixture
def mock_openai_stream():
    def _mock(respx_mock, baseUrl="https://api.openai.com/v1"):
        sse_data = (
            format_sse(MockResponses.MOCK_OPENAI_CHAT_COMPLETION)
            + format_sse(MockResponses.MOCK_OPENAI_TEXT_DELTA)
            + format_sse(MockResponses.MOCK_OPENAI_DONE)
            + "data: [DONE]\n\n"
        )
        respx_mock.post(f"{base_url}/chat/completions").mock(
            return_value=httpx.Response(
                200, content=sse_data.encode(), headers={"content-type": "text/event-stream"}
            )
        )

    return _mock


@pytest.fixture
def mock_anthropic_stream():
    def _mock(respx_mock, baseUrl="https://api.anthropic.com"):
        sse_data = (
            format_sse(MockResponses.MOCK_ANTHROPIC_MESSAGE_START)
            + format_sse(MockResponses.MOCK_ANTHROPIC_CONTENT_BLOCK_START)
            + format_sse(MockResponses.MOCK_ANTHROPIC_CONTENT_DELTA)
            + format_sse(MockResponses.MOCK_ANTHROPIC_MESSAGE_STOP)
        )
        respx_mock.post(f"{base_url}/v1/messages").mock(
            return_value=respx.Response(
                200, content=sse_data, headers={"content-type": "text/event-stream"}
            )
        )

    return _mock


@pytest.fixture
def mock_google_stream():
    def _mock(respx_mock, baseUrl="https://generativelanguage.googleapis.com"):

        sse_data = format_sse(MockResponses.MOCK_GOOGLE_RESPONSE)
        respx_mock.post(f"{base_url}/v1beta/models/gemini-2.0-flash:streamGenerateContent").mock(
            return_value=respx.Response(
                200, content=sse_data, headers={"content-type": "text/event-stream"}
            )
        )

    return _mock
