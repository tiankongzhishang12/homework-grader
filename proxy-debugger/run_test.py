from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from src.client import RequestConfig, post_chat_completions, post_responses
from src.diagnostics import diagnose
from src.extractors import extract_text
from src.reporters import build_record, print_summary, save_record
from src.scenarios import get_prompt, get_suite


PROJECT_ROOT = Path(__file__).resolve().parent


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="Config YAML path")
    parser.add_argument("--base-url", help="Base URL, e.g. http://localhost:8317/v1")
    parser.add_argument("--api-key", help="Bearer token")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--timeout", type=float, help="Timeout seconds")
    parser.add_argument("--temperature", type=float, help="Sampling temperature")
    parser.add_argument("--max-output-tokens", type=int, help="Max output tokens")
    parser.add_argument("--output-dir", help="Output directory")


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        path = PROJECT_ROOT / "config.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a top-level mapping")
    return data


def build_request_config(args: argparse.Namespace, config_data: dict[str, Any]) -> RequestConfig:
    base_url = getattr(args, "base_url", None) or config_data.get("base_url") or "http://localhost:8317/v1"
    api_key = getattr(args, "api_key", None) or config_data.get("api_key") or ""
    model = getattr(args, "model", None) or config_data.get("model") or "gpt-5.4"
    timeout_value = getattr(args, "timeout", None)
    temperature_value = getattr(args, "temperature", None)
    max_output_tokens_value = getattr(args, "max_output_tokens", None)
    timeout_seconds = float(timeout_value or config_data.get("timeout_seconds") or 120)
    temperature = float(temperature_value if temperature_value is not None else config_data.get("temperature", 1.0))
    max_output_tokens = int(max_output_tokens_value or config_data.get("max_output_tokens") or 256)
    return RequestConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def get_output_dir(args: argparse.Namespace, config_data: dict[str, Any]) -> Path:
    output_value = getattr(args, "output_dir", None) or config_data.get("output_dir") or "outputs"
    return (PROJECT_ROOT / output_value).resolve()


def run_single(endpoint: str, prompt: str, request_config: RequestConfig, output_dir: Path, save_outputs: bool) -> None:
    if endpoint == "responses":
        raw = post_responses(request_config, prompt)
    elif endpoint == "chat":
        raw = post_chat_completions(request_config, prompt)
    else:
        raise ValueError(f"Unsupported endpoint: {endpoint}")

    parsed_text = extract_text(raw.response_body)
    diagnostics = diagnose(raw.response_body, parsed_text, raw.transport_error)
    record = build_record(raw, parsed_text, diagnostics)
    saved_path = save_record(output_dir, record, endpoint) if save_outputs else None
    print_summary(record, saved_path)


def main() -> None:
    # Suppress absent defaults so subparser options don't overwrite values
    # that were already parsed before the subcommand.
    shared_parser = argparse.ArgumentParser(add_help=False, argument_default=argparse.SUPPRESS)
    add_shared_arguments(shared_parser)

    parser = argparse.ArgumentParser(
        description="OpenAI-compatible proxy debugger",
        parents=[shared_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    single_parser = subparsers.add_parser("single", help="Run a single request", parents=[shared_parser])
    single_parser.add_argument("--endpoint", choices=["responses", "chat"], required=True)
    single_parser.add_argument("--prompt", help="Prompt text")
    single_parser.add_argument("--scenario", choices=["hello", "json", "english", "long"], default="hello")

    compare_parser = subparsers.add_parser("compare", help="Run the same prompt against both endpoints", parents=[shared_parser])
    compare_parser.add_argument("--prompt", help="Prompt text")
    compare_parser.add_argument("--scenario", choices=["hello", "json", "english", "long"], default="hello")

    suite_parser = subparsers.add_parser("suite", help="Run a built-in suite", parents=[shared_parser])
    suite_parser.add_argument("--name", choices=["smoke", "json", "stress"], required=True)
    suite_parser.add_argument("--repeat", type=int, default=3, help="Only used for stress suite")

    args = parser.parse_args()
    config_data = load_config(getattr(args, "config", None))
    request_config = build_request_config(args, config_data)
    output_dir = get_output_dir(args, config_data)
    save_outputs = bool(config_data.get("save_outputs", True))

    if not request_config.api_key:
        raise SystemExit("Missing API key. Pass --api-key or set api_key in config.yaml")

    if args.command == "single":
        prompt = args.prompt or get_prompt(args.scenario)
        run_single(args.endpoint, prompt, request_config, output_dir, save_outputs)
        return

    if args.command == "compare":
        prompt = args.prompt or get_prompt(args.scenario)
        run_single("responses", prompt, request_config, output_dir, save_outputs)
        print("-" * 60)
        run_single("chat", prompt, request_config, output_dir, save_outputs)
        return

    if args.command == "suite":
        suite_items = get_suite(args.name)
        if args.name == "stress":
            for index in range(args.repeat):
                print(f"[stress] round {index + 1}/{args.repeat}")
                run_single("responses", get_prompt("hello"), request_config, output_dir, save_outputs)
                print("-" * 60)
            return

        for endpoint, prompt in suite_items:
            run_single(endpoint, prompt, request_config, output_dir, save_outputs)
            print("-" * 60)
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
