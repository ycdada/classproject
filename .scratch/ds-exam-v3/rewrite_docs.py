"""Generate a current API and page inventory from the repository source tree."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ROUTERS = ROOT / "backend" / "app" / "routers"
PAGES = ROOT / "frontend" / "src" / "pages"
OUTPUT = Path(__file__).resolve().parent / "api-reference.md"

ROUTER_PREFIX = re.compile(r"APIRouter\s*\([^)]*?prefix\s*=\s*['\"]([^'\"]+)['\"]", re.S)
ROUTE_DECORATOR = re.compile(
    r"@router\.(get|post|put|patch|delete)\(\s*(['\"])(.*?)\2", re.S
)


def router_endpoints(path: Path) -> list[tuple[str, str]]:
    source = path.read_text(encoding="utf-8")
    prefix_match = ROUTER_PREFIX.search(source)
    prefix = prefix_match.group(1).rstrip("/") if prefix_match else ""
    endpoints = []
    for match in ROUTE_DECORATOR.finditer(source):
        method, route = match.group(1).upper(), match.group(3)
        full_path = f"{prefix}/{route.lstrip('/')}" if route else (prefix or "/")
        endpoints.append((method, full_path))
    return endpoints


def build_markdown() -> str:
    lines = [
        "# API 与页面清单",
        "",
        "本清单根据当前后端路由和前端页面文件自动生成。",
        "",
        "## 后端 API",
        "",
        "| 模块 | 方法 | 路径 |",
        "|---|---|---|",
    ]

    for router_file in sorted(ROUTERS.glob("*.py")):
        if router_file.name == "__init__.py":
            continue
        for method, route in router_endpoints(router_file):
            lines.append(f"| `{router_file.stem}` | `{method}` | `{route}` |")

    lines.extend(["", "## 前端页面", ""])
    for page in sorted(PAGES.glob("*.tsx")):
        lines.append(f"- `{page.stem}`")

    lines.extend(["", "## 核心服务模块", ""])
    services = ROOT / "backend" / "app" / "services"
    for service in sorted(services.glob("*.py")):
        if service.name != "__init__.py":
            lines.append(f"- `{service.stem}`")

    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT.write_text(build_markdown(), encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
