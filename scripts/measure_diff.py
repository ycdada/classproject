"""30% 差异门：对照冻结基线度量源码 churn、模块替换与学术文档重写。"""
from __future__ import annotations

from pathlib import Path
import hashlib, json, re, zipfile, argparse

SRC_SUFFIX = {".py", ".ts", ".tsx", ".js", ".vue", ".css", ".md"}
SKIP_PARTS = {"node_modules", "dist", "__pycache__", ".venv", "chroma", "data", "uploads", "baselines"}
NEW_SRC_ROOTS = ("backend", "frontend/src")

REPO_ROOT = Path(__file__).resolve().parents[1]


def iter_files(root: Path, suffixes=None):
    # 新源码树只扫 backend/ 与 frontend/src，避免把 baselines/ 算进新树
    if root.resolve() == REPO_ROOT.resolve():
        for sub in NEW_SRC_ROOTS:
            sub_path = root / sub
            if sub_path.exists():
                yield from iter_files(sub_path, suffixes)
        return
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if suffixes and p.suffix.lower() not in suffixes:
            continue
        yield p


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_churn(old: Path, new: Path) -> float:
    old_bytes = {file_hash(p): p.stat().st_size for p in iter_files(old, SRC_SUFFIX)}
    new_hashes = {file_hash(p) for p in iter_files(new, SRC_SUFFIX)}
    total = sum(old_bytes.values()) or 1
    survived = sum(sz for h, sz in old_bytes.items() if h in new_hashes)
    return 1.0 - survived / total


def extract_docx_paragraphs(path: Path) -> list[str]:
    from xml.etree import ElementTree as ET
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.findall(".//w:p", ns):
        text = "".join((t.text or "") for t in p.findall(".//w:t", ns)).strip()
        if text:
            paras.append(text)
    return paras


def extract_pptx_text(path: Path) -> list[str]:
    from xml.etree import ElementTree as ET
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    paras = []
    with zipfile.ZipFile(path) as z:
        slides = sorted(n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        for name in slides:
            root = ET.fromstring(z.read(name))
            for t in root.findall(".//a:t", ns):
                if t.text and t.text.strip():
                    paras.append(t.text.strip())
    return paras


def extract_paragraphs(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        return extract_docx_paragraphs(path)
    if path.suffix.lower() == ".pptx":
        return extract_pptx_text(path)
    return [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]


def doc_rewrite(old_dir: Path, new_dir: Path) -> float:
    targets = [
        "数据结构出卷系统-项目计划书.docx",
        "数据结构智能出卷系统_中期报告.docx",
        "开发文档.docx",
        "摸鱼小组-《数据结构》智能出卷系统.pptx",
    ]
    scores = []
    for name in targets:
        op, np = old_dir / name, new_dir / name
        if not op.exists() or not np.exists():
            scores.append(1.0)
            continue
        old_p, new_p = extract_paragraphs(op), extract_paragraphs(np)
        old_set, new_set = set(old_p), set(new_p)
        if not old_set:
            scores.append(1.0)
            continue
        scores.append(1.0 - len(old_set & new_set) / len(old_set))
    return min(scores) if scores else 0.0


def measure_diff(old_src, old_docs, new_src, new_docs, inventory=None):
    if inventory is None:
        inventory = json.loads(Path(__file__).resolve().parent.joinpath("module_inventory.json").read_text(encoding="utf-8"))
    modules = inventory["modules"]
    changed = set(inventory.get("changed", []))
    result = {
        "source_churn": source_churn(Path(old_src), Path(new_src)),
        "module_change": (len(changed) / len(modules)) if modules else 0.0,
        "doc_rewrite": doc_rewrite(Path(old_docs), Path(new_docs)),
    }
    result["pass"] = all(result[k] >= 0.30 for k in ("source_churn", "module_change", "doc_rewrite"))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--old-src", default=str(REPO_ROOT / "baselines/v2-source"))
    p.add_argument("--old-docs", default=str(REPO_ROOT / "baselines/original-docs"))
    p.add_argument("--new-src", default=str(REPO_ROOT))
    p.add_argument("--new-docs", default=str(REPO_ROOT / "原文档"))
    args = p.parse_args()
    r = measure_diff(args.old_src, args.old_docs, args.new_src, args.new_docs)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    raise SystemExit(0 if r["pass"] else 1)
