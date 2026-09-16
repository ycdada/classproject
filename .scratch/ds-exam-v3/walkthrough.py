"""Run read-only smoke checks against the local application API."""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("DS_EXAM_API_BASE", "http://localhost:8000/api").rstrip("/")
CHECKS = [
    ("health", "/health", "status"),
    ("materials", "/materials", "list"),
    ("exams", "/exams", "list"),
    ("pending drafts", "/drafts?status=pending", "list"),
]


def run_check(name: str, path: str, expected: str) -> bool:
    request = Request(f"{BASE_URL}{path}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if expected == "status":
            ok = payload.get("status") == "ok"
            detail = payload.get("status", "missing status")
        else:
            ok = isinstance(payload, list)
            detail = f"{len(payload)} records" if ok else "expected a JSON list"
        print(f"{'PASS' if ok else 'FAIL'} | {name}: {detail}")
        return ok
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"FAIL | {name}: {exc}")
        return False


def main() -> int:
    print(f"Checking API at {BASE_URL}")
    results = [run_check(*check) for check in CHECKS]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
