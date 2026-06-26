import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * percentile_value))
    return sorted_values[index]


def load_sample_inputs() -> list[dict[str, Any]]:
    data = json.loads((ROOT / "SUST_Preli_Sample_Cases.json").read_text(encoding="utf-8"))
    return [case["input"] for case in data["cases"]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a live QueueStorm Investigator endpoint.")
    parser.add_argument("--base-url", required=True, help="Live base URL, for example https://example.com")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    sample_inputs = load_sample_inputs()
    latencies_ms: list[float] = []
    success_count = 0
    failure_count = 0
    invalid_json_count = 0
    server_error_count = 0

    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        for _ in range(args.repeats):
            for payload in sample_inputs:
                start = time.perf_counter()
                try:
                    response = client.post(f"{base_url}/analyze-ticket", json=payload)
                except httpx.HTTPError:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    latencies_ms.append(elapsed_ms)
                    failure_count += 1
                    continue

                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies_ms.append(elapsed_ms)

                try:
                    response.json()
                except ValueError:
                    invalid_json_count += 1
                    failure_count += 1
                    continue

                if response.status_code >= 500:
                    server_error_count += 1
                    failure_count += 1
                elif response.status_code == 200:
                    success_count += 1
                else:
                    failure_count += 1

    total_requests = len(sample_inputs) * args.repeats
    average_latency_ms = statistics.mean(latencies_ms) if latencies_ms else 0.0
    p95_latency_ms = percentile(latencies_ms, 0.95)
    max_latency_ms = max(latencies_ms) if latencies_ms else 0.0

    print(f"total_requests={total_requests}")
    print(f"success_count={success_count}")
    print(f"failure_count={failure_count}")
    print(f"average_latency_ms={average_latency_ms:.2f}")
    print(f"p95_latency_ms={p95_latency_ms:.2f}")
    print(f"max_latency_ms={max_latency_ms:.2f}")
    print(f"invalid_json_count={invalid_json_count}")
    print(f"server_error_count={server_error_count}")

    if failure_count:
        print("FAIL: benchmark saw failed requests")
        return 1
    if invalid_json_count:
        print("FAIL: benchmark saw invalid JSON responses")
        return 1
    if server_error_count:
        print("FAIL: benchmark saw 5xx responses")
        return 1
    if p95_latency_ms >= 5000:
        print("FAIL: p95 latency exceeded 5000 ms")
        return 1

    print("PASS: live benchmark")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
