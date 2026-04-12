# CLIProxyAPI Empty Response Samples

## Context

- Base URL: `http://localhost:8317/v1` (local proxy)
- Model: `gpt-5.4`
- Symptom:
  - `/v1/responses` returns `200`, but `output` is empty
  - `/v1/chat/completions` returns `200`, but `message.content` is `null`

## `/v1/responses` Sample

```json
{
  "id": "<redacted-response-id>",
  "object": "response",
  "created_at": 1775635717,
  "status": "completed",
  "background": false,
  "completed_at": 1775635719,
  "error": null,
  "frequency_penalty": 0.0,
  "incomplete_details": null,
  "instructions": null,
  "max_output_tokens": null,
  "max_tool_calls": null,
  "model": "gpt-5.4",
  "output": [],
  "parallel_tool_calls": true,
  "presence_penalty": 0.0,
  "previous_response_id": null,
  "prompt_cache_key": "<redacted-prompt-cache-key>",
  "prompt_cache_retention": null,
  "reasoning": {
    "effort": "none",
    "summary": null
  },
  "safety_identifier": "<redacted-safety-identifier>",
  "service_tier": "default",
  "store": false,
  "temperature": 1.0,
  "text": {
    "format": {
      "type": "text"
    },
    "verbosity": "medium"
  },
  "tool_choice": "auto",
  "tool_usage": {
    "image_gen": {
      "input_tokens": 0,
      "input_tokens_details": {
        "image_tokens": 0,
        "text_tokens": 0
      },
      "output_tokens": 0,
      "output_tokens_details": {
        "image_tokens": 0,
        "text_tokens": 0
      },
      "total_tokens": 0
    },
    "web_search": {
      "num_requests": 0
    }
  },
  "tools": [],
  "top_logprobs": 0,
  "top_p": 0.98,
  "truncation": "disabled",
  "usage": {
    "input_tokens": 11,
    "input_tokens_details": {
      "cached_tokens": 0
    },
    "output_tokens": 5,
    "output_tokens_details": {
      "reasoning_tokens": 0
    },
    "total_tokens": 16
  },
  "user": null,
  "metadata": {}
}
```

## `/v1/chat/completions` Sample

```json
{
  "id": "<redacted-response-id>",
  "object": "chat.completion",
  "created": 1775635726,
  "model": "gpt-5.4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "reasoning_content": null,
        "tool_calls": null
      },
      "finish_reason": "stop",
      "native_finish_reason": "stop"
    }
  ],
  "usage": {
    "completion_tokens": 22,
    "total_tokens": 33,
    "prompt_tokens": 11,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 15
    }
  }
}
```
