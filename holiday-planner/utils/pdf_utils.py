import io
import random
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from pypdf import PdfWriter, PdfReader

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}

CAT_EMOJIS = ["🐱", "😸", "😺", "🐾", "🐈", "😻", "🙀", "😹"]
ORANGE = colors.HexColor("#FF6B35")
CREAM = colors.HexColor("#FFF8F0")
LIGHT_ORANGE = colors.HexColor("#FFB347")
GREEN = colors.HexColor("#4CAF50")
BLUE = colors.HexColor("#2196F3")


def download_pdf(url, timeout=15):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and "pdf" in resp.headers.get("Content-Type", "").lower():
            return io.BytesIO(resp.content)
        # Try to get PDF even if content-type is wrong
        if resp.status_code == 200 and len(resp.content) > 1000:
            if resp.content[:4] == b"%PDF":
                return io.BytesIO(resp.content)
    except Exception:
        pass
    return None


def generate_speed_math_sheet(day_num):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title", fontSize=20, textColor=ORANGE,
                                  alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", fontSize=11, textColor=colors.HexColor("#666666"),
                                     alignment=TA_CENTER, spaceAfter=2)
    header_style = ParagraphStyle("header", fontSize=10, textColor=colors.HexColor("#444444"),
                                   alignment=TA_LEFT)

    story = []

    cat = random.choice(CAT_EMOJIS)
    story.append(Paragraph(f"{cat} Speed Math – Day {day_num} {cat}", title_style))
    story.append(Paragraph("Single-digit Addition &amp; Subtraction", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=LIGHT_ORANGE, spaceAfter=8))

    # Name / Date / Time fields
    info_data = [["Name: ___________________________",
                  "Date: ________________",
                  "Time taken: ________"]]
    info_table = Table(info_data, colWidths=[8*cm, 5.5*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Paragraph("⏱️ How fast can you go? Try to finish in under 5 minutes!", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    # Generate 20 problems: mix of addition and subtraction
    problems = []
    used = set()
    while len(problems) < 20:
        op = random.choice(["+", "-"])
        if op == "+":
            a = random.randint(1, 9)
            b = random.randint(1, 9)
        else:
            a = random.randint(2, 9)
            b = random.randint(1, a)  # ensures no negative answers
        key = (a, op, b)
        if key not in used:
            used.add(key)
            problems.append((a, op, b))

    # Layout in 4 columns × 5 rows
    num_style = ParagraphStyle("num", fontSize=14, fontName="Helvetica-Bold",
                                alignment=TA_CENTER, textColor=colors.HexColor("#222222"))
    line_style = ParagraphStyle("line", fontSize=14, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#999999"))

    rows = []
    col_width = 4.2 * cm
    for row_i in range(5):
        row = []
        for col_i in range(4):
            idx = row_i * 4 + col_i
            a, op, b = problems[idx]
            cell_content = f"{idx+1}. {a} {op} {b} = ___"
            row.append(Paragraph(cell_content, num_style))
        rows.append(row)

    prob_table = Table(rows, colWidths=[col_width]*4, rowHeights=[1.6*cm]*5)
    prob_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_ORANGE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM, colors.white]),
    ]))
    story.append(prob_table)
    story.append(Spacer(1, 0.4*cm))

    footer_style = ParagraphStyle("footer", fontSize=9, textColor=colors.HexColor("#999999"),
                                   alignment=TA_CENTER)
    story.append(Paragraph("🐾 Great work! Check your answers with a grown-up. 🐾", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf


def generate_cover_page(day_num, worksheets):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2.5*cm, bottomMargin=2*cm)

    title_style = ParagraphStyle("title", fontSize=26, textColor=ORANGE,
                                  alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=6)
    subtitle_style = ParagraphStyle("subtitle", fontSize=13, textColor=colors.HexColor("#666666"),
                                     alignment=TA_CENTER, spaceAfter=4)
    section_style = ParagraphStyle("section", fontSize=11, textColor=colors.HexColor("#444444"),
                                    fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4)
    item_style = ParagraphStyle("item", fontSize=10, textColor=colors.HexColor("#333333"),
                                 leftIndent=10, spaceAfter=3)

    story = []
    cat = random.choice(CAT_EMOJIS)
    story.append(Paragraph(f"🐱 Holiday Learning Plan", title_style))
    story.append(Paragraph(f"Day {day_num} – Today's Practice Sheets", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=LIGHT_ORANGE, spaceAfter=12))
    story.append(Paragraph("📋 What you'll do today:", section_style))

    lit_sheets = [w for w in worksheets if w["subject"] == "literacy"]
    num_sheets = [w for w in worksheets if w["subject"] == "numeracy" and not w["is_speed_math"]]
    speed_math = [w for w in worksheets if w.get("is_speed_math")]

    if lit_sheets:
        story.append(Paragraph("📗 Literacy", ParagraphStyle("lt", fontSize=12, textColor=GREEN,
                                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)))
        for i, ws in enumerate(lit_sheets, 1):
            story.append(Paragraph(f"  ✏️  <b>{ws['topic_label']}</b> – {ws['title']}", item_style))
            story.append(Paragraph(f"      <i>{ws['description']}</i>",
                         ParagraphStyle("desc", fontSize=9, textColor=colors.HexColor("#777777"),
                                         leftIndent=20, spaceAfter=4)))

    if num_sheets:
        story.append(Paragraph("📘 Numeracy", ParagraphStyle("nt", fontSize=12, textColor=BLUE,
                                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)))
        for ws in num_sheets:
            story.append(Paragraph(f"  🔢  <b>{ws['topic_label']}</b> – {ws['title']}", item_style))
            story.append(Paragraph(f"      <i>{ws['description']}</i>",
                         ParagraphStyle("desc", fontSize=9, textColor=colors.HexColor("#777777"),
                                         leftIndent=20, spaceAfter=4)))

    if speed_math:
        story.append(Paragraph("⚡ Speed Math", ParagraphStyle("sm", fontSize=12, textColor=ORANGE,
                                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)))
        story.append(Paragraph("  ➕➖  20 single-digit addition &amp; subtraction problems", item_style))
        story.append(Paragraph("      <i>Try to beat your time from yesterday!</i>",
                     ParagraphStyle("desc", fontSize=9, textColor=colors.HexColor("#777777"),
                                     leftIndent=20, spaceAfter=4)))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_ORANGE, spaceAfter=8))
    footer_style = ParagraphStyle("footer", fontSize=10, textColor=colors.HexColor("#888888"),
                                   alignment=TA_CENTER)
    story.append(Paragraph(f"⏰ Aim to finish in 30 minutes  •  {cat} You've got this!", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf


def generate_fallback_page(worksheet):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=3*cm, bottomMargin=2*cm)

    title_style = ParagraphStyle("title", fontSize=16, textColor=ORANGE,
                                  alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=8)
    body_style = ParagraphStyle("body", fontSize=11, textColor=colors.HexColor("#333333"),
                                 alignment=TA_CENTER, spaceAfter=6)
    url_style = ParagraphStyle("url", fontSize=10, textColor=BLUE,
                                alignment=TA_CENTER, spaceAfter=6)

    story = [
        Paragraph("🐱 Worksheet – Open & Print", title_style),
        Spacer(1, 0.5*cm),
        Paragraph(f"<b>{worksheet['topic_label']}: {worksheet['title']}</b>", body_style),
        Paragraph(f"<i>{worksheet['description']}</i>", body_style),
        Spacer(1, 0.5*cm),
        Paragraph("Please open this link in your browser and print:", body_style),
        Paragraph(f"<u>{worksheet['url']}</u>", url_style),
        Spacer(1, 0.3*cm),
        Paragraph(f"Source: {worksheet['source']}", body_style),
    ]
    doc.build(story)
    buf.seek(0)
    return buf


def build_day_pdf(day_num, worksheets):
    writer = PdfWriter()

    # 1. Cover page
    cover = generate_cover_page(day_num, worksheets)
    writer.append(PdfReader(cover))

    failed_worksheets = []

    for ws in worksheets:
        if ws.get("is_speed_math"):
            speed_pdf = generate_speed_math_sheet(day_num)
            writer.append(PdfReader(speed_pdf))
        elif ws.get("url"):
            pdf_buf = download_pdf(ws["url"])
            if pdf_buf:
                try:
                    writer.append(PdfReader(pdf_buf))
                except Exception:
                    failed_worksheets.append(ws)
            else:
                failed_worksheets.append(ws)

    # Add fallback pages for worksheets that couldn't be downloaded
    for ws in failed_worksheets:
        fallback = generate_fallback_page(ws)
        writer.append(PdfReader(fallback))

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output, failed_worksheets
