from __future__ import annotations


def get_prompt(name: str) -> str:
    prompts = {
        "hello": "请只回复：你好",
        "json": '请只返回一个 JSON 对象，例如 {"ok": true, "message": "hello"}',
        "english": "Reply with exactly: hello",
        "long": "请用中文简要介绍软件测试的目的，控制在 120 字以内。",
    }
    if name not in prompts:
        raise KeyError(f"Unknown scenario: {name}")
    return prompts[name]


def get_suite(name: str) -> list[tuple[str, str]]:
    if name == "smoke":
        return [
            ("responses", get_prompt("hello")),
            ("chat", get_prompt("hello")),
        ]
    if name == "json":
        return [
            ("responses", get_prompt("json")),
            ("chat", get_prompt("json")),
        ]
    if name == "stress":
        return [
            ("responses", get_prompt("hello")),
        ]
    raise KeyError(f"Unknown suite: {name}")
