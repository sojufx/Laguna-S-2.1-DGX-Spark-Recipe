#!/usr/bin/env python3
"""
OpenAI-compatible LLM benchmark suite.

Designed for local vLLM / Cloudflare / OpenAI-compatible endpoints.
Measures:
- cold and warm TTFT
- decode tokens/sec
- aggregate concurrency throughput
- prefix-cache benefit
- basic reliability/errors

No API keys are stored here. Use --api-key or LLM_BENCH_API_KEY.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_AGENT_PREFIX = """You are an expert coding and research agent.
Follow instructions exactly. Be concise but complete. When writing code, prefer
clear maintainable implementations. If requirements are ambiguous, make a safe
assumption and state it briefly.
"""


PROMPTS = {
    "short": "Write a concise explanation of prefix caching in vLLM.",
    "code": """Write a complete single-file Python implementation of a tiny HTTP router.
Requirements: route decorators, path params, query parsing, JSON responses,
error handling, and a usage example. Return code only.""",
    "agent": """We are debugging a production LLM endpoint. Produce a practical checklist
for diagnosing slow first-token latency, memory growth, prefix-cache behavior,
and speculative decoding acceptance. Include commands where useful.""",
    "long_context": "\n".join(
        [f"Constraint {i}: preserve type hints, avoid external dependencies, handle edge cases clearly." for i in range(1, 241)]
    )
    + "\n\nWrite a self-contained Python module for an in-memory task queue with retries. Return code only.",
}


@dataclasses.dataclass
class RequestResult:
    name: str
    ok: bool
    elapsed_s: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tok_per_s: float
    ttft_s: float | None
    error: str | None = None


def now_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def api_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def make_payload(model: str, prompt: str, max_tokens: int, temperature: float, stream: bool) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }


def parse_usage(response: dict[str, Any]) -> tuple[int, int, int]:
    usage = response.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return prompt_tokens, completion_tokens, total_tokens


def post_json(url: str, api_key: str, payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_nonstream(
    name: str,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: int,
) -> RequestResult:
    start = time.perf_counter()
    try:
        payload = make_payload(model, prompt, max_tokens, temperature, stream=False)
        response = post_json(url, api_key, payload, timeout_s)
        elapsed = time.perf_counter() - start
        prompt_tokens, completion_tokens, total_tokens = parse_usage(response)
        tok_per_s = completion_tokens / elapsed if elapsed > 0 else 0.0
        return RequestResult(name, True, elapsed, prompt_tokens, completion_tokens, total_tokens, tok_per_s, None)
    except Exception as exc:  # noqa: BLE001 - benchmark should capture all failures
        elapsed = time.perf_counter() - start
        return RequestResult(name, False, elapsed, 0, 0, 0, 0.0, None, repr(exc))


def run_stream_ttft(
    name: str,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: int,
) -> RequestResult:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = make_payload(model, prompt, max_tokens, temperature, stream=True)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    start = time.perf_counter()
    first_token_at: float | None = None
    content_chars = 0
    completion_estimate = 0

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                event = json.loads(data)
                delta = event.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content") or ""
                if piece and first_token_at is None:
                    first_token_at = time.perf_counter()
                if piece:
                    content_chars += len(piece)
                    # Rough estimate for streaming endpoints that omit final usage.
                    completion_estimate = max(completion_estimate, content_chars // 4)
        elapsed = time.perf_counter() - start
        ttft = (first_token_at - start) if first_token_at else None
        tok_per_s = completion_estimate / elapsed if elapsed > 0 else 0.0
        return RequestResult(name, True, elapsed, 0, completion_estimate, completion_estimate, tok_per_s, ttft)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - start
        ttft = (first_token_at - start) if first_token_at else None
        return RequestResult(name, False, elapsed, 0, completion_estimate, completion_estimate, 0.0, ttft, repr(exc))


def summarize(results: list[RequestResult]) -> dict[str, Any]:
    ok = [r for r in results if r.ok]
    speeds = [r.tok_per_s for r in ok if r.tok_per_s > 0]
    ttfts = [r.ttft_s for r in ok if r.ttft_s is not None]
    elapsed = [r.elapsed_s for r in ok]
    completions = [r.completion_tokens for r in ok]
    return {
        "count": len(results),
        "ok": len(ok),
        "errors": len(results) - len(ok),
        "decode_tok_s_mean": statistics.mean(speeds) if speeds else None,
        "decode_tok_s_median": statistics.median(speeds) if speeds else None,
        "ttft_s_mean": statistics.mean(ttfts) if ttfts else None,
        "ttft_s_p95": percentile(ttfts, 0.95),
        "elapsed_s_mean": statistics.mean(elapsed) if elapsed else None,
        "completion_tokens_total": sum(completions),
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# LLM Benchmark: {report['model']}",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Base URL: `{report['base_url']}`",
        f"- Max tokens: `{report['max_tokens']}`",
        f"- Temperature: `{report['temperature']}`",
        "",
        "## Summary",
        "",
        "| Suite | OK/Total | Decode tok/s mean | Decode tok/s median | TTFT mean | TTFT p95 | Completion tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for suite, summary in report["summaries"].items():
        lines.append(
            "| {suite} | {ok}/{count} | {mean} | {median} | {ttft_mean} | {ttft_p95} | {tokens} |".format(
                suite=suite,
                ok=summary["ok"],
                count=summary["count"],
                mean=f"{summary['decode_tok_s_mean']:.1f}" if summary["decode_tok_s_mean"] is not None else "—",
                median=f"{summary['decode_tok_s_median']:.1f}" if summary["decode_tok_s_median"] is not None else "—",
                ttft_mean=f"{summary['ttft_s_mean']:.3f}s" if summary["ttft_s_mean"] is not None else "—",
                ttft_p95=f"{summary['ttft_s_p95']:.3f}s" if summary["ttft_s_p95"] is not None else "—",
                tokens=summary["completion_tokens_total"],
            )
        )

    lines.extend(["", "## Raw results", ""])
    for result in report["results"]:
        status = "OK" if result["ok"] else "ERR"
        lines.append(
            f"- `{status}` `{result['name']}` elapsed={result['elapsed_s']:.2f}s "
            f"completion={result['completion_tokens']} tok/s={result['tok_per_s']:.1f} "
            f"ttft={result['ttft_s'] if result['ttft_s'] is not None else 'n/a'}"
            + (f" error={result['error']}" if result.get("error") else "")
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAI-compatible LLM benchmark suite")
    parser.add_argument("--base-url", default=os.getenv("LLM_BENCH_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--api-key", default=os.getenv("LLM_BENCH_API_KEY"))
    parser.add_argument("--model", default=os.getenv("LLM_BENCH_MODEL", "ornith"))
    parser.add_argument("--out-dir", default="benchmarks/llm-bench/results")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-s", type=int, default=240)
    parser.add_argument("--concurrency", default="1,2,4,6", help="Comma-separated concurrency levels")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--prefix-repeats", type=int, default=3)
    parser.add_argument("--skip-stream", action="store_true")
    args = parser.parse_args()

    if not args.api_key:
        print("Missing API key. Set LLM_BENCH_API_KEY or pass --api-key.", file=sys.stderr)
        return 2

    url = api_url(args.base_url)
    concurrencies = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    results: list[RequestResult] = []

    print(f"Benchmarking model={args.model} url={url}")

    for prompt_name in ["short", "code", "agent", "long_context"]:
        for repeat in range(args.repeats):
            name = f"single/{prompt_name}/r{repeat + 1}"
            result = run_nonstream(
                name, url, args.api_key, args.model, PROMPTS[prompt_name], args.max_tokens, args.temperature, args.timeout_s
            )
            results.append(result)
            print(f"{name}: {'OK' if result.ok else 'ERR'} {result.tok_per_s:.1f} tok/s {result.elapsed_s:.2f}s")

    if not args.skip_stream:
        for prompt_name in ["short", "agent"]:
            name = f"ttft/{prompt_name}"
            result = run_stream_ttft(
                name, url, args.api_key, args.model, PROMPTS[prompt_name], 128, args.temperature, args.timeout_s
            )
            results.append(result)
            ttft = f"{result.ttft_s:.3f}s" if result.ttft_s is not None else "n/a"
            print(f"{name}: {'OK' if result.ok else 'ERR'} ttft={ttft}")

    warm_prompt = DEFAULT_AGENT_PREFIX + "\n\n" + PROMPTS["agent"]
    for repeat in range(args.prefix_repeats):
        name = f"prefix_warm/r{repeat + 1}"
        result = run_stream_ttft(name, url, args.api_key, args.model, warm_prompt, 128, args.temperature, args.timeout_s)
        results.append(result)
        ttft = f"{result.ttft_s:.3f}s" if result.ttft_s is not None else "n/a"
        print(f"{name}: {'OK' if result.ok else 'ERR'} ttft={ttft}")

    for concurrency in concurrencies:
        prompt = PROMPTS["code"]
        suite_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(
                    run_nonstream,
                    f"concurrency/c{concurrency}/s{i + 1}",
                    url,
                    args.api_key,
                    args.model,
                    prompt,
                    args.max_tokens,
                    args.temperature,
                    args.timeout_s,
                )
                for i in range(concurrency)
            ]
            batch_results = [f.result() for f in futures]
        suite_elapsed = time.perf_counter() - suite_start
        total_completion = sum(r.completion_tokens for r in batch_results if r.ok)
        aggregate = total_completion / suite_elapsed if suite_elapsed > 0 else 0.0
        for result in batch_results:
            results.append(result)
        print(f"concurrency c{concurrency}: aggregate={aggregate:.1f} tok/s elapsed={suite_elapsed:.2f}s")

    report = {
        "timestamp": now_stamp(),
        "base_url": args.base_url,
        "request_url": url,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "concurrency": concurrencies,
        "summaries": {
            "single": summarize([r for r in results if r.name.startswith("single/")]),
            "ttft": summarize([r for r in results if r.name.startswith("ttft/")]),
            "prefix_warm": summarize([r for r in results if r.name.startswith("prefix_warm/")]),
            "concurrency": summarize([r for r in results if r.name.startswith("concurrency/")]),
            "all": summarize(results),
        },
        "results": [dataclasses.asdict(r) for r in results],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{now_stamp()}-{args.model.replace('/', '_').replace(':', '_')}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
