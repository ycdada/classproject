"""Report the current API, page, service, and test inventory."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS = ROOT / "backend" / "app" / "routers"
PAGES = ROOT / "frontend" / "src" / "pages"
SERVICES = ROOT / "backend" / "app" / "services"
TESTS = ROOT / "backend" / "tests"
ROUTE_PATTERN = re.compile(r"@router\.(get|post|put|patch|delete)\(")

REQUIRED_PATHS = [
    ROOT / "backend" / "app" / "main.py",
    ROOT / "backend" / "app" / "services" / "scope_builder.py",
    ROOT / "backend" / "app" / "services" / "paper_assembler.py",
    ROOT / "backend" / "app" / "services" / "draft_service.py",
    ROOT / "frontend" / "src" / "App.tsx",
    ROOT / "frontend" / "package.json",
]


def python_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.py") if p.name != "__init__.py")


def main() -> int:
    routers = python_files(ROUTERS)
    services = python_files(SERVICES)
    pages = sorted(PAGES.glob("*.tsx"))
    tests = sorted(TESTS.glob("test_*.py"))
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_PATHS if not path.is_file()]
    endpoint_count = sum(
        len(ROUTE_PATTERN.findall(path.read_text(encoding="utf-8")))
        for path in routers
    )

    report = {
        "root": str(ROOT),
        "router_modules": [p.stem for p in routers],
        "api_endpoint_count": endpoint_count,
        "frontend_pages": [p.stem for p in pages],
        "service_modules": [p.stem for p in services],
        "backend_test_files": [p.name for p in tests],
        "missing_required_paths": missing,
        "status": "ok" if not missing else "incomplete",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
