"""Export exam to DOCX format using python-docx — A3 paper with sidebar + two-column layout."""
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


TYPE_NAMES = {
    "choice": "选择题",
    "fill": "填空题",
    "tf": "判断题",
    "short_answer": "简答题",
    "code": "算法设计题",
}
TYPE_ORDER = ["choice", "fill", "tf", "short_answer", "code"]


def _add_run(para, text, size=11, bold=False, font="SimSun", color=None):
    """Add a run with Chinese font support."""
    run = para.add_run(str(text))
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    if color:
        run.font.color.rgb = color
    return run


def _make_font(name):
    """Get east-asian font element."""
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:eastAsia"), name)
    rPr.append(rFonts)
    return rPr


def _remove_table_borders(table):
    """Remove all borders from a table."""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    tblPr.append(borders)


def _set_cell_vertical(cell):
    """Set cell text direction to vertical (top-to-bottom)."""
    tcPr = cell._tc.get_or_add_tcPr()
    td = OxmlElement("w:textDirection")
    td.set(qn("w:val"), "tbRl")
    tcPr.append(td)


def _write_questions_to_cell(cell, questions, start_num=1, with_answer=False):
    """Write exam questions into a table cell, grouped by type. Returns next question number."""
    grouped = {}
    for q in questions:
        qtype = q.get("type", "choice")
        grouped.setdefault(qtype, []).append(q)

    global_num = start_num
    for qtype in TYPE_ORDER:
        items = grouped.get(qtype, [])
        if not items:
            continue

        # Section header
        h_para = cell.add_paragraph()
        scores = [q.get("score", 5) for q in items]
        section_total = sum(scores)
        if len(set(scores)) == 1:
            h_text = f"{TYPE_NAMES.get(qtype, qtype)}（共{len(items)}题，每小题{scores[0]}分，共{section_total}分）"
        else:
            h_text = f"{TYPE_NAMES.get(qtype, qtype)}（共{len(items)}题，共{section_total}分）"
        _add_run(h_para, h_text, size=12, bold=True, font="SimHei")

        for q in items:
            qdata = q.get("question", q)
            score = q.get("score", 5)

            para = cell.add_paragraph()
            para.paragraph_format.space_before = Pt(3)
            _add_run(para, f"{global_num}. ", size=11, bold=True)
            _add_run(para, f"（{score}分）", size=11, bold=True)
            _add_run(para, qdata.get("content", ""), size=11)

            if qtype == "choice" and qdata.get("options"):
                opts = qdata["options"]
                if isinstance(opts, dict):
                    for key in sorted(opts.keys()):
                        opt_para = cell.add_paragraph()
                        opt_para.paragraph_format.left_indent = Cm(0.8)
                        _add_run(opt_para, f"{key}. {opts[key]}", size=10.5)

            # Spacing
            sp = cell.add_paragraph()
            sp.paragraph_format.space_after = Pt(2)
            sp.paragraph_format.space_before = Pt(1)

            if with_answer:
                ans_para = cell.add_paragraph()
                ans_para.paragraph_format.left_indent = Cm(0.5)
                text = f"【答案】{qdata.get('answer', '')}"
                if qdata.get("explanation"):
                    text += f"  【解析】{qdata['explanation']}"
                _add_run(ans_para, text, size=9, color=RGBColor(14, 124, 134))

            global_num += 1

    return global_num


def export_exam_to_docx(exam: dict, with_answer: bool = True) -> BytesIO:
    """Generate a DOCX exam on A3 landscape: two-column layout, personal info below title."""
    doc = Document()

    # ── A3 page (420mm x 297mm landscape) ──
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    questions = exam.get("questions", [])
    total = len(questions)
    mid = (total + 1) // 2

    # ── 2-column table for questions ──
    tbl = doc.add_table(rows=1, cols=2)
    tbl.autofit = False
    _remove_table_borders(tbl)

    left_cell = tbl.cell(0, 0)
    right_cell = tbl.cell(0, 1)
    col_w = Cm(18.5)
    left_cell.width = col_w
    right_cell.width = col_w

    # ── Title ──
    title_para = left_cell.paragraphs[0]
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_run(title_para, exam.get("title", "试卷"), size=16, bold=True, font="SimHei")

    # Info line
    info_para = left_cell.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_run(info_para, f"总分：{exam.get('total_score', 100)}分  考试时间：{exam.get('duration', 120)}分钟", size=10)

    # Personal info line
    stu_para = left_cell.add_paragraph()
    stu_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_run(stu_para, "班级：______________  姓名：______________  学号：______________  得分：______________", size=10)

    left_cell.add_paragraph()  # spacer

    # Spacer in right cell to align with left
    for _ in range(4):
        right_cell.add_paragraph()

    # ── Split questions into two columns ──
    left_questions = questions[:mid]
    right_questions = questions[mid:]

    _write_questions_to_cell(left_cell, left_questions, start_num=1, with_answer=with_answer)
    _write_questions_to_cell(right_cell, right_questions, start_num=mid + 1, with_answer=with_answer)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
