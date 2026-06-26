import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def check_docs() -> None:
    required = [
        "README.md",
        "RUNBOOK.md",
        "MODELS.md",
        "DEPLOYMENT.md",
        ".env.example",
        "Dockerfile",
        ".dockerignore",
        "scripts/benchmark.py",
        "scripts/benchmark_live.py",
        "scripts/live_validate.py",
    ]
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f"FAIL: docs check missing {', '.join(missing)}")
    print("PASS: docs check")


def check_sample_outputs() -> None:
    output_dir = ROOT / "sample_outputs"
    expected_files = [output_dir / f"sample_{index:02d}_output.json" for index in range(1, 11)]
    missing = [path.name for path in expected_files if not path.exists()]
    if missing:
        raise SystemExit(f"FAIL: sample outputs missing {', '.join(missing)}")

    required_fields = {
        "ticket_id",
        "relevant_transaction_id",
        "evidence_verdict",
        "case_type",
        "severity",
        "department",
        "agent_summary",
        "recommended_next_action",
        "customer_reply",
        "human_review_required",
    }
    for path in expected_files:
        body = json.loads(path.read_text(encoding="utf-8"))
        missing_fields = required_fields - set(body)
        if missing_fields:
            raise SystemExit(f"FAIL: {path.name} missing {sorted(missing_fields)}")
    print("PASS: sample outputs")


def check_no_obvious_secrets() -> None:
    secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(
            r"(?i)\b(api_key|secret|token|password)\s*=\s*(?!your_|example|placeholder|changeme|$)[^\s#]+"
        ),
    ]
    allowed_suffixes = {
        ".py",
        ".md",
        ".txt",
        ".json",
        ".example",
        ".gitignore",
        ".dockerignore",
    }
    allowed_names = {"Dockerfile", "requirements.txt"}

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__", ".pytest_cache", ".venv", "venv"} for part in path.parts):
            continue
        if path.suffix not in allowed_suffixes and path.name not in allowed_names:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in secret_patterns:
            if pattern.search(text):
                raise SystemExit(f"FAIL: possible secret found in {path.relative_to(ROOT)}")
    print("PASS: no obvious secrets found")


def check_hidden_case_count() -> None:
    sys.path.insert(0, str(ROOT))
    from tests.test_hidden_style_cases import HIDDEN_VALID_CASES

    if len(HIDDEN_VALID_CASES) < 50:
        raise SystemExit("FAIL: fewer than 50 hidden-style valid cases")


def main() -> int:
    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_schema.py"])
    print("PASS: schema tests")

    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_sample_cases.py"])
    print("PASS: sample cases")

    check_hidden_case_count()
    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_hidden_style_cases.py"])
    print("PASS: hidden-style tests")

    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_safety.py"])
    print("PASS: safety tests")

    run_command([sys.executable, str(ROOT / "scripts" / "benchmark.py")])
    print("PASS: benchmark")

    check_docs()
    check_sample_outputs()
    check_no_obvious_secrets()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
