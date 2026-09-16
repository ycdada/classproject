"""Tests for the current project inventory report."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_diff


def test_python_files_excludes_package_initializer(tmp_path):
    (tmp_path / "alpha.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not Python", encoding="utf-8")

    assert [path.name for path in measure_diff.python_files(tmp_path)] == ["alpha.py"]


def test_route_pattern_counts_supported_http_methods():
    source = "@router.get('/a')\n@router.post('/b')\n@router.delete('/c')\n"

    assert len(measure_diff.ROUTE_PATTERN.findall(source)) == 3


def test_main_reports_current_inventory(tmp_path, monkeypatch, capsys):
    routers = tmp_path / "routers"
    pages = tmp_path / "pages"
    services = tmp_path / "services"
    tests = tmp_path / "tests"
    for directory in (routers, pages, services, tests):
        directory.mkdir()

    (routers / "questions.py").write_text(
        "@router.get('/questions')\n@router.post('/questions')\n", encoding="utf-8"
    )
    (pages / "QuestionBank.tsx").write_text("export {}\n", encoding="utf-8")
    (services / "question_service.py").write_text("pass\n", encoding="utf-8")
    (tests / "test_questions.py").write_text("pass\n", encoding="utf-8")
    required = tmp_path / "required.py"
    required.write_text("pass\n", encoding="utf-8")

    monkeypatch.setattr(measure_diff, "ROOT", tmp_path)
    monkeypatch.setattr(measure_diff, "ROUTERS", routers)
    monkeypatch.setattr(measure_diff, "PAGES", pages)
    monkeypatch.setattr(measure_diff, "SERVICES", services)
    monkeypatch.setattr(measure_diff, "TESTS", tests)
    monkeypatch.setattr(measure_diff, "REQUIRED_PATHS", [required])

    assert measure_diff.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["router_modules"] == ["questions"]
    assert report["api_endpoint_count"] == 2
    assert report["frontend_pages"] == ["QuestionBank"]
    assert report["service_modules"] == ["question_service"]
    assert report["backend_test_files"] == ["test_questions.py"]
    assert report["missing_required_paths"] == []
    assert report["status"] == "ok"
