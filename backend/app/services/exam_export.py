"""Export exam to PDF (reportlab, Chinese font) and plain text formats.
A3 landscape — two-column layout, personal info below title."""
import os, re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

TYPE_NAMES = {"choice":"选择题","fill":"填空题","tf":"判断题","short_answer":"简答题","code":"算法设计题"}
TYPE_ORDER = ["choice","fill","tf","short_answer","code"]
CN_NUMS = ["一","二","三","四","五","六","七","八"]
_BLANK_BRACKET_RE = re.compile(r"[（(]\s*[）)]\s*[。.？?]?\s*$")
_FONT_NAME = None

def _register_chinese_font():
    global _FONT_NAME
    if _FONT_NAME: return _FONT_NAME
    for name, path in [
        ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
        ("MSYaHei", r"C:\Windows\Fonts\msyh.ttc"),
        ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ]:
        if os.path.exists(path):
            try:
                if path.lower().endswith(".ttc"): pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
                else: pdfmetrics.registerFont(TTFont(name, path))
                _FONT_NAME = name; return name
            except Exception: continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    _FONT_NAME = "STSong-Light"; return _FONT_NAME

def _format_options(options):
    if isinstance(options, dict): return [f"{k}. {options[k]}" for k in sorted(options.keys())]
    if isinstance(options, list): return [str(o) for o in options]
    return []

def _para_text(text):
    out = []
    for ln in str(text).expandtabs(4).split("\n"):
        s = ln.lstrip(" "); pad = "\xa0" * (len(ln) - len(s))
        out.append(pad + escape(s))
    return "<br/>".join(out)

def _grouped_questions(exam):
    g = {}
    for q in exam.get("questions", []): g.setdefault(q.get("type","choice"), []).append(q)
    return [(t, g[t]) for t in TYPE_ORDER if t in g]

def _section_title(i, qtype, items):
    scores = [q.get("score",5) for q in items]; total = sum(scores)
    cn = CN_NUMS[i] if i < len(CN_NUMS) else str(i+1)
    if len(set(scores)) == 1: detail = f"本大题共{len(items)}小题，每小题{scores[0]}分，共{total}分"
    else: detail = f"本大题共{len(items)}小题，共{total}分"
    return f"{cn}、{TYPE_NAMES.get(qtype,qtype)}（{detail}）"

def _build_story(questions, start_num, font, q_style, opt_style, ans_style, section_style, with_answer):
    g = {}
    for q in questions: g.setdefault(q.get("type","choice"), []).append(q)
    story = []; n = start_num
    for si, (qt, items) in enumerate((t, g[t]) for t in TYPE_ORDER if t in g):
        story.append(Paragraph(escape(_section_title(si, qt, items)), section_style))
        for q in items:
            qd = q.get("question", q); score = q.get("score",5)
            c = str(qd.get("content","")).rstrip()
            if qt == "choice" and not _BLANK_BRACKET_RE.search(c): c += "（　　）"
            story.append(Paragraph(_para_text(f"{n}. （{score}分）{c}"), q_style))
            if qt == "choice":
                for line in _format_options(qd.get("options")): story.append(Paragraph(_para_text(line), opt_style))
            story.append(Spacer(1, 6*14 if qt in ("short_answer","code") else 6))
            if with_answer:
                t = f"    【答案】{qd.get('answer','')}"
                if qd.get("explanation"): t += f"  【解析】{qd['explanation']}"
                story.append(Paragraph(_para_text(t), ans_style))
            n += 1
    return story

def export_exam_to_pdf(exam: dict, with_answer: bool = False) -> BytesIO:
    font = _register_chinese_font(); buf = BytesIO()
    pw, ph = A3; pw, ph = ph, pw  # landscape
    lm, rm, tm, bm = 2*cm, 2*cm, 1.5*cm, 1.5*cm
    cw = (pw - lm - rm - 0.5*cm) / 2; ch = ph - tm - bm
    lf = Frame(lm, bm, cw, ch, id="left")
    rf = Frame(lm + cw + 0.5*cm, bm, cw, ch, id="right")
    doc = BaseDocTemplate(buf, pagesize=(pw,ph), leftMargin=lm, rightMargin=rm, topMargin=tm, bottomMargin=bm)
    doc.addPageTemplates([PageTemplate(id="Exam", frames=[lf, rf])])

    ts = ParagraphStyle("Title", fontName=font, fontSize=15, alignment=TA_CENTER, spaceAfter=6, leading=20)
    infos = ParagraphStyle("Info", fontName=font, fontSize=10, alignment=TA_CENTER, spaceAfter=3, leading=14)
    stus = ParagraphStyle("Student", fontName=font, fontSize=10, alignment=TA_CENTER, spaceAfter=8, leading=16)
    secs = ParagraphStyle("Section", fontName=font, fontSize=12, spaceBefore=10, spaceAfter=6, leading=16)
    qs = ParagraphStyle("Question", fontName=font, fontSize=10, spaceAfter=3, leading=15)
    opts = ParagraphStyle("Option", fontName=font, fontSize=10, leftIndent=0.7*cm, spaceAfter=1, leading=14)
    anss = ParagraphStyle("Answer", fontName=font, fontSize=8, spaceAfter=3, leading=12, textColor=colors.HexColor("#0E7C86"))

    questions = exam.get("questions", [])
    story = [
        Paragraph(escape(exam.get("title","试卷")), ts),
        Paragraph(escape(f"总分：{exam.get('total_score',100)}分  考试时间：{exam.get('duration',120)}分钟"), infos),
        Paragraph("班级：______________  姓名：______________  学号：______________  得分：______________", stus),
    ]
    sections = _grouped_questions(exam)
    if sections:
        hdr = ["题号"] + [CN_NUMS[i] if i < len(CN_NUMS) else str(i+1) for i in range(len(sections))] + ["总分"]
        td = [hdr, ["得分"] + [""] * (len(sections)+1)]
        ct = cw / (len(sections)+2)
        st = Table(td, colWidths=[ct]*(len(sections)+2), rowHeights=[0.6*cm, 0.7*cm])
        st.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),9),
            ("GRID",(0,0),(-1,-1),0.6,colors.black),("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story.append(st); story.append(Spacer(1, 8))
    story += _build_story(questions, 1, font, qs, opts, anss, secs, with_answer)
    doc.build(story); buf.seek(0); return buf

def export_exam_to_txt(exam: dict, with_answer: bool = False) -> str:
    lines = [
        exam.get("title","试卷"), "="*40,
        f"总分：{exam.get('total_score',100)}分 | 考试时间：{exam.get('duration',120)}分钟",
        "", "班级：__________  姓名：__________  学号：__________  得分：__________", "",
    ]
    n = 0
    for si, (qt, items) in enumerate(_grouped_questions(exam)):
        lines.append(_section_title(si, qt, items)); lines.append("-"*30)
        for q in items:
            n += 1; qd = q.get("question", q)
            lines.append(f"{n}. （{q.get('score',5)}分）{qd.get('content','')}")
            if qt == "choice":
                for line in _format_options(qd.get("options")): lines.append(f"    {line}")
            if with_answer:
                lines.append(f"    【答案】{qd.get('answer','')}")
                if qd.get("explanation"): lines.append(f"    【解析】{qd['explanation']}")
            lines.append("")
    return "\n".join(lines)
