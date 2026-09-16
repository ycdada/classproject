from pathlib import Path
import tempfile, shutil, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_diff import measure_diff, extract_paragraphs


def test_identical_trees_fail_threshold():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "old" / "a.py").parent.mkdir(parents=True)
        (d / "old" / "a.py").write_text("print(1)\n", encoding="utf-8")
        shutil.copytree(d / "old", d / "new")
        (d / "docs_old" / "a.txt").parent.mkdir(parents=True)
        (d / "docs_old" / "a.txt").write_text("hello world\n" * 20, encoding="utf-8")
        shutil.copytree(d / "docs_old", d / "docs_new")
        r = measure_diff(d / "old", d / "docs_old", d / "new", d / "docs_new",
                         inventory={"modules": ["a", "b", "c"], "changed": []})
        assert r["source_churn"] < 0.3
        assert r["pass"] is False


def test_rewritten_source_passes_churn():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "old" / "a.py").parent.mkdir(parents=True)
        (d / "old" / "a.py").write_text("print(1)\n" * 50, encoding="utf-8")
        (d / "new").mkdir()
        (d / "new" / "b.py").write_text("x = 2\n" * 50, encoding="utf-8")
        (d / "docs_old" / "a.txt").parent.mkdir(parents=True)
        (d / "docs_old" / "a.txt").write_text("hello world\n" * 20, encoding="utf-8")
        (d / "docs_new").mkdir()
        (d / "docs_new" / "a.txt").write_text("brand new text\n" * 20, encoding="utf-8")
        r = measure_diff(d / "old", d / "docs_old", d / "new", d / "docs_new",
                         inventory={"modules": ["a", "b", "c"], "changed": ["a", "b"]})
        assert r["source_churn"] >= 0.3
        assert r["module_change"] >= 0.3
        assert r["doc_rewrite"] >= 0.3
        assert r["pass"] is True


def test_doc_rewrite_uses_paragraph_sets():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        old = d / "old.txt"
        new = d / "new.txt"
        old.write_text("段一\n" * 1 + "\n".join(f"旧段落{i}" for i in range(10)), encoding="utf-8")
        new.write_text("\n".join(f"新段落{i}" for i in range(10)), encoding="utf-8")
        lines_old = [ln.strip() for ln in old.read_text(encoding="utf-8").splitlines() if ln.strip()]
        lines_new = [ln.strip() for ln in new.read_text(encoding="utf-8").splitlines() if ln.strip()]
        overlap = len(set(lines_old) & set(lines_new)) / len(set(lines_old))
        assert overlap < 0.7
        assert extract_paragraphs(old) == lines_old
