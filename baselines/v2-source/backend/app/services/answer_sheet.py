"""Generate answer sheet (答题卡) as PDF — matches exam question numbers and spacing."""
import os
from io import BytesIO

from reportlab.lib.pagesizes import A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

TYPE_NAMES = {
    "choice": "选择题", "fill": "填空题", "tf": "判断题",
    "short_answer": "简答题", "code": "算法设计题",
}
TYPE_ORDER = ["choice", "fill", "tf", "short_answer", "code"]
CN_NUMS = ["一", "二", "三", "四", "五", "六", "七", "八"]
_FONT_NAME = None


def _register_chinese_font():
    global _FONT_NAME
    if _FONT_NAME:
        return _FONT_NAME
    candidates = [
        ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
        ("MSYaHei", r"C:\Windows\Fonts\msyh.ttc"),
        ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for name, path in candidates:
        if os.path.exists(path):
            try:
                if path.lower().endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(name, path))
                _FONT_NAME = name
                return name
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    _FONT_NAME = "STSong-Light"
    return _FONT_NAME


def generate_answer_sheet_pdf(exam: dict) -> BytesIO:
    """Generate an answer sheet PDF matching the exam paper layout."""
    font = _register_chinese_font()
    buf = BytesIO()

    page_w, page_h = A3
    page_w, page_h = page_h, page_w  # landscape A3

    left_margin = 2 * cm
    right_margin = 2 * cm
    top_margin = 1.5 * cm
    bottom_margin = 1.5 * cm
    col_w = (page_w - left_margin - right_margin - 0.5 * cm) / 2

    content_h = page_h - top_margin - bottom_margin
    left_frame = Frame(left_margin, bottom_margin, col_w, content_h, id="left")
    right_frame = Frame(left_margin + col_w + 0.5 * cm, bottom_margin, col_w, content_h, id="right")

    page_template = PageTemplate(id="AnswerSheet", frames=[left_frame, right_frame])

    doc = BaseDocTemplate(
        buf, pagesize=(page_w, page_h),
        leftMargin=left_margin, rightMargin=right_margin,
        topMargin=top_margin, bottomMargin=bottom_margin,
    )
    doc.addPageTemplates([page_template])

    # Styles
    title_style = ParagraphStyle("ASTitle", fontName=font, fontSize=16,
                                 alignment=TA_CENTER, spaceAfter=6, leading=22)
    info_style = ParagraphStyle("ASInfo", fontName=font, fontSize=10,
                                alignment=TA_CENTER, spaceAfter=3, leading=14)
    student_style = ParagraphStyle("ASStudent", fontName=font, fontSize=10,
                                   alignment=TA_CENTER, spaceAfter=8, leading=16)
    section_style = ParagraphStyle("ASSection", fontName=font, fontSize=11,
                                   spaceBefore=8, spaceAfter=4, leading=15)
    item_style = ParagraphStyle("ASItem", fontName=font, fontSize=10,
                                spaceAfter=2, leading=14)
    choice_style = ParagraphStyle("ASChoice", fontName=font, fontSize=10,
                                  leftIndent=0.5 * cm, spaceAfter=1, leading=14)

    questions = exam.get("questions", [])

    story = [
        Paragraph(f"《{exam.get('title', '试卷')}》答题卡", title_style),
        Paragraph(f"总分：{exam.get('total_score', 100)}分  时间：{exam.get('duration', 120)}分钟", info_style),
        Paragraph("班级：______________  姓名：______________  学号：______________  得分：______________", student_style),
    ]

    def section_border(content_items, col_w):
        """Wrap content in a thin-bordered section box."""
        inner = list(content_items)
        t = Table([[inner]], colWidths=[col_w - 1*cm])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return t

    def build_sheet(questions_list, start_num):
        """Build answer sheet: [A][B][C][D] for choice, lines for fill, tall box for writing."""
        grouped = {}
        for q in questions_list:
            qtype = q.get("type", "choice")
            grouped.setdefault(qtype, []).append(q)

        items = []
        global_num = start_num
        for sec_idx, qtype in enumerate(TYPE_ORDER):
            qs = grouped.get(qtype, [])
            if not qs:
                continue

            cn = CN_NUMS[sec_idx] if sec_idx < len(CN_NUMS) else str(sec_idx + 1)
            sec_content = [
                Paragraph(
                    f"{cn}、{TYPE_NAMES.get(qtype, qtype)}（共{len(qs)}题）", section_style
                ),
            ]

            for q in qs:
                score = q.get("score", 5)
                qdata = q.get("question", q)

                if qtype == "choice":
                    options = qdata.get("options", {})
                    if isinstance(options, dict):
                        opt_keys = sorted(options.keys())[:4]
                    else:
                        opt_keys = ["A", "B", "C", "D"]
                    bubbles = "      ".join(f"[{k}]" for k in opt_keys)
                    sec_content.append(Paragraph(
                        f"{global_num}. （{score}分）    {bubbles}", item_style
                    ))

                elif qtype == "tf":
                    sec_content.append(Paragraph(
                        f"{global_num}. （{score}分）    [ 对 ]      [ 错 ]", item_style
                    ))

                elif qtype == "fill":
                    sec_content.append(Paragraph(
                        f"{global_num}. （{score}分）____________________________", item_style
                    ))

                elif qtype in ("short_answer", "code"):
                    sec_content.append(Paragraph(
                        f"{global_num}. （{score}分）", item_style
                    ))
                    # Tall answer area
                    t = Table([[""]], colWidths=[col_w - 2*cm], rowHeights=[120])
                    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.black)]))
                    sec_content.append(t)

                sec_content.append(Spacer(1, 4))
                global_num += 1

            items.append(section_border(sec_content, col_w))
            items.append(Spacer(1, 10))

        return items

    story += build_sheet(questions, 1)

    doc.build(story)
    buf.seek(0)
    return buf
