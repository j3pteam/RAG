#!/usr/bin/env python3
"""
exports.py — turn an assistant reply into a downloadable document.

Supports four formats:
    docx  → Word            (python-docx)
    pptx  → PowerPoint      (python-pptx)
    xlsx  → Excel           (openpyxl)
    pdf   → PDF             (reportlab)

Everything is rendered in the J3P brand palette. All builders take the raw
reply text (lightweight markdown) and return a BytesIO ready to stream.

Add to requirements.txt:
    python-docx
    python-pptx
    openpyxl
    reportlab
"""
import io
import os
import re
from datetime import datetime

# --- Brand palette -----------------------------------------------------------
NAVY = "27334A"
GOLD = "D2BC8D"
RUST = "9D432C"
PAPER = "FAF6F0"
CHARCOAL = "3F3F44"

BRAND_NAME = "J3P Health"
DOC_SUBTITLE = "J3P Advisor"

# --- Logo -------------------------------------------------------------------
# Embedded at the top of every generated file. Falls back to the wordmark text
# if the image can't be found, so exports never fail over a missing asset.
LOGO_CANDIDATES = [
    os.environ.get("BRAND_LOGO_FILE", ""),
    "full_logo.png",
    "logo.png",
    "monogram.jpg",
]


def find_logo():
    """Return a filesystem path to the brand logo, or None if unavailable."""
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in LOGO_CANDIDATES:
        if not candidate:
            continue
        for base in (here, os.getcwd()):
            path = candidate if os.path.isabs(candidate) else os.path.join(base, candidate)
            if os.path.isfile(path):
                return path
    return None


# --- Meta-language stripping -------------------------------------------------
# The assistant closes its reply with a line about the SAVE button / the file
# downloading. That's useful in the chat window but must never appear inside
# the document itself, so it's removed before rendering.
_META_LINE_PATTERNS = [
    r"\bsave\s+button\b",
    r"\bclick\s+save\b",
    r"\bre-?download\b",
    r"\bthe file is (?:downloading|being (?:downloaded|generated|created))\b",
    r"\bdownloading (?:now|automatically)\b",
    r"\bwill download it\b",
    r"\bdownload(?:ed|ing)? (?:it )?(?:in|as) (?:powerpoint|word|excel|pdf)\b",
    r"\bbelow will (?:download|save|export)\b",
    r"\b(?:deck|document|letter|file) is (?:written and ready|ready to download)\b",
    r"\bexported? (?:to|as) an? (?:word|powerpoint|excel|pdf)\b",
    r"\bis (?:attached|downloading) (?:now|below)\b",
]
_META_RE = re.compile("|".join(_META_LINE_PATTERNS), re.IGNORECASE)


def strip_meta(text: str) -> str:
    """Remove chat-only lines about saving/downloading from document content."""
    if not text:
        return text
    kept = []
    for line in str(text).replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        # Only drop short standalone lines — never gut a real paragraph that
        # happens to mention one of these words in passing.
        if stripped and len(stripped) < 320 and _META_RE.search(stripped):
            continue
        kept.append(line)
    out = "\n".join(kept)
    # Collapse blank runs left behind and trailing separators
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"(?:\n\s*[-*_]{3,}\s*)+$", "", out)
    return out.strip()



# ---------------------------------------------------------------------------
# Lightweight markdown parser
# ---------------------------------------------------------------------------

def parse_blocks(text: str) -> list:
    """Parse reply text into a flat list of blocks.

    Returns a list of dicts, each one of:
        {"type": "heading", "level": 1|2|3, "text": str}
        {"type": "bullet",  "text": str}
        {"type": "number",  "text": str, "num": int}
        {"type": "para",    "text": str}

    Inline **bold** markers are left in place — each renderer strips or
    converts them as appropriate for its format.
    """
    blocks = []
    if not text:
        return blocks

    # Drop fenced code blocks — they don't translate well to these formats
    text = re.sub(r"```[\s\S]*?```", "", text)

    lines = text.replace("\r\n", "\n").split("\n")
    para_buffer = []

    def flush_para():
        if para_buffer:
            joined = " ".join(l.strip() for l in para_buffer).strip()
            if joined:
                blocks.append({"type": "para", "text": joined})
            para_buffer.clear()

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_para()
            continue

        # Horizontal rule
        if re.fullmatch(r"[-*_]{3,}", stripped):
            flush_para()
            continue

        # Headings: # / ## / ###
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = min(len(m.group(1)), 3)
            blocks.append({"type": "heading", "level": level, "text": m.group(2).strip()})
            continue

        # A standalone all-bold line reads as a heading
        m = re.fullmatch(r"\*\*(.+?)\*\*:?", stripped)
        if m:
            flush_para()
            blocks.append({"type": "heading", "level": 2, "text": m.group(1).strip()})
            continue

        # Bulleted list
        m = re.match(r"^[-*+]\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append({"type": "bullet", "text": m.group(1).strip()})
            continue

        # Numbered list
        m = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append({
                "type": "number",
                "num": int(m.group(1)),
                "text": m.group(2).strip(),
            })
            continue

        para_buffer.append(stripped)

    flush_para()
    return blocks


def strip_inline(s: str) -> str:
    """Remove inline markdown emphasis, links, and inline code markers."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
    s = re.sub(r"`([^`]+?)`", r"\1", s)
    s = re.sub(r"\[([^\]]+?)\]\([^)]+?\)", r"\1", s)
    return s.strip()


def split_bold_runs(s: str) -> list:
    """Split a string into [(text, is_bold), ...] on **bold** boundaries."""
    parts = []
    for chunk in re.split(r"(\*\*.+?\*\*)", s):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            parts.append((strip_inline(chunk[2:-2]), True))
        else:
            parts.append((strip_inline(chunk), False))
    return [(t, b) for t, b in parts if t]


def derive_title(text: str, fallback: str = "J3P Advisor Response") -> str:
    """Pick a document title from the first heading or sentence."""
    for block in parse_blocks(text):
        if block["type"] == "heading":
            return strip_inline(block["text"])[:90]
    first = strip_inline((text or "").strip().split("\n")[0])
    if not first:
        return fallback
    # Cut at the first sentence boundary if it's a long line
    sentence = re.split(r"(?<=[.!?])\s", first)[0]
    return (sentence or first)[:90] or fallback


def safe_filename(title: str, ext: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", strip_inline(title)).strip("_")[:50] or "j3p_response"
    return f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"


# ---------------------------------------------------------------------------
# Word (.docx)
# ---------------------------------------------------------------------------

def build_docx(text: str, title: str = None) -> io.BytesIO:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    title = title or derive_title(text)
    doc = Document()

    # Base style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Masthead — logo image when available, wordmark text otherwise
    logo_path = find_logo()
    brand = doc.add_paragraph()
    brand.paragraph_format.space_after = Pt(2)
    if logo_path:
        try:
            brand.add_run().add_picture(logo_path, height=Inches(0.42))
        except Exception:
            logo_path = None
    if not logo_path:
        brand_run = brand.add_run(BRAND_NAME.upper())
        brand_run.bold = True
        brand_run.font.size = Pt(9)
        brand_run.font.color.rgb = RGBColor.from_string(GOLD)

    head = doc.add_paragraph()
    head_run = head.add_run(title)
    head_run.bold = True
    head_run.font.size = Pt(20)
    head_run.font.color.rgb = RGBColor.from_string(NAVY)
    head.paragraph_format.space_after = Pt(4)

    meta = doc.add_paragraph()
    meta_run = meta.add_run(
        f"{DOC_SUBTITLE} · {datetime.now().strftime('%B %d, %Y')}"
    )
    meta_run.font.size = Pt(9)
    meta_run.font.color.rgb = RGBColor.from_string(CHARCOAL)
    meta.paragraph_format.space_after = Pt(14)

    # Body
    for block in parse_blocks(text):
        btype = block["type"]

        if btype == "heading":
            level = block["level"]
            p = doc.add_paragraph()
            run = p.add_run(strip_inline(block["text"]))
            run.bold = True
            run.font.size = Pt({1: 15, 2: 13, 3: 11.5}[level])
            run.font.color.rgb = RGBColor.from_string(NAVY)
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(5)

        elif btype == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            for chunk, is_bold in split_bold_runs(block["text"]):
                run = p.add_run(chunk)
                run.bold = is_bold
            p.paragraph_format.space_after = Pt(4)

        elif btype == "number":
            p = doc.add_paragraph(style="List Number")
            for chunk, is_bold in split_bold_runs(block["text"]):
                run = p.add_run(chunk)
                run.bold = is_bold
            p.paragraph_format.space_after = Pt(4)

        else:
            p = doc.add_paragraph()
            for chunk, is_bold in split_bold_runs(block["text"]):
                run = p.add_run(chunk)
                run.bold = is_bold

    # Footer disclaimer
    doc.add_paragraph()
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    foot_run = foot.add_run(
        "For informational purposes only. Not medical, legal, or financial advice."
    )
    foot_run.italic = True
    foot_run.font.size = Pt(8)
    foot_run.font.color.rgb = RGBColor.from_string(CHARCOAL)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PowerPoint (.pptx)
# ---------------------------------------------------------------------------

def build_pptx(text: str, title: str = None) -> io.BytesIO:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    title = title or derive_title(text)
    prs = Presentation()
    prs.slide_width = Inches(13.333)   # 16:9
    prs.slide_height = Inches(7.5)

    navy = RGBColor.from_string(NAVY)
    gold = RGBColor.from_string(GOLD)
    paper = RGBColor.from_string(PAPER)
    MAX_BULLETS = 6

    def set_bg(slide, color):
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = color

    # --- Title slide ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])   # blank
    set_bg(slide, navy)

    logo_path = find_logo()

    box = slide.shapes.add_textbox(Inches(0.9), Inches(2.5), Inches(11.5), Inches(2.2))
    tf = box.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    if logo_path:
        try:
            slide.shapes.add_picture(logo_path, Inches(0.9), Inches(1.15), height=Inches(0.95))
            p.text = ""                    # logo replaces the wordmark text
        except Exception:
            p.text = BRAND_NAME.upper()
    else:
        p.text = BRAND_NAME.upper()
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = gold

    p = tf.add_paragraph()
    p.text = title
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = paper
    p.space_before = Pt(10)

    p = tf.add_paragraph()
    p.text = f"{DOC_SUBTITLE} · {datetime.now().strftime('%B %d, %Y')}"
    p.font.size = Pt(13)
    p.font.color.rgb = gold
    p.space_before = Pt(12)

    # --- Group blocks into sections keyed by heading ---
    sections = []
    current = {"title": title, "items": []}
    for block in parse_blocks(text):
        if block["type"] == "heading":
            if current["items"]:
                sections.append(current)
            current = {"title": strip_inline(block["text"]), "items": []}
        else:
            current["items"].append(strip_inline(block["text"]))
    if current["items"]:
        sections.append(current)
    if not sections:
        sections = [{"title": title, "items": [strip_inline(text or "")]}]

    # --- Content slides — split any section over MAX_BULLETS items ---
    for section in sections:
        items = [i for i in section["items"] if i]
        pages = [items[i:i + MAX_BULLETS] for i in range(0, len(items), MAX_BULLETS)] or [[]]
        for idx, page_items in enumerate(pages):
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            set_bg(slide, paper)

            # Gold accent rule under the heading
            head_text = section["title"] + ("" if idx == 0 else f" (cont. {idx + 1})")
            head_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
            htf = head_box.text_frame
            htf.word_wrap = True
            hp = htf.paragraphs[0]
            hp.text = head_text
            hp.font.size = Pt(28)
            hp.font.bold = True
            hp.font.color.rgb = navy

            line = slide.shapes.add_shape(1, Inches(0.85), Inches(1.62), Inches(2.0), Inches(0.045))
            line.fill.solid()
            line.fill.fore_color.rgb = gold
            line.line.fill.background()
            line.shadow.inherit = False

            body_box = slide.shapes.add_textbox(Inches(0.85), Inches(2.0), Inches(11.6), Inches(4.7))
            btf = body_box.text_frame
            btf.word_wrap = True
            for j, item in enumerate(page_items):
                bp = btf.paragraphs[0] if j == 0 else btf.add_paragraph()
                bp.text = "•  " + item
                bp.font.size = Pt(17)
                bp.font.color.rgb = RGBColor.from_string(CHARCOAL)
                bp.space_after = Pt(13)

            # Footer — small logo, falling back to the wordmark
            placed_logo = False
            if logo_path:
                try:
                    slide.shapes.add_picture(
                        logo_path, Inches(0.85), Inches(6.82), height=Inches(0.34))
                    placed_logo = True
                except Exception:
                    placed_logo = False
            if not placed_logo:
                foot = slide.shapes.add_textbox(Inches(0.85), Inches(6.95), Inches(11.6), Inches(0.4))
                ftf = foot.text_frame
                fp = ftf.paragraphs[0]
                fp.text = BRAND_NAME
                fp.font.size = Pt(9)
                fp.font.color.rgb = gold
                fp.alignment = PP_ALIGN.LEFT

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Excel (.xlsx)
# ---------------------------------------------------------------------------

def build_xlsx(text: str, title: str = None) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    title = title or derive_title(text)
    wb = Workbook()
    ws = wb.active
    ws.title = "Response"

    navy_fill = PatternFill("solid", fgColor=NAVY)
    gold_fill = PatternFill("solid", fgColor=GOLD)
    paper_fill = PatternFill("solid", fgColor=PAPER)
    wrap = Alignment(vertical="top", wrap_text=True)
    bottom_rule = Border(bottom=Side(style="thin", color=GOLD))

    # Masthead
    ws["A1"] = BRAND_NAME.upper()
    ws["A1"].font = Font(bold=True, size=10, color=GOLD)
    ws["A1"].fill = navy_fill
    ws["B1"].fill = navy_fill
    ws["C1"].fill = navy_fill

    logo_path = find_logo()
    if logo_path:
        try:
            from openpyxl.drawing.image import Image as XLImage
            img = XLImage(logo_path)
            ratio = (img.height or 1) / float(img.width or 1)
            img.width = 120
            img.height = max(int(120 * ratio), 1)
            ws.row_dimensions[1].height = max(img.height * 0.78, 18)
            ws["A1"] = ""                       # logo replaces the text wordmark
            ws.add_image(img, "A1")
        except Exception:
            pass                                 # keep the text masthead

    ws["A2"] = title
    ws["A2"].font = Font(bold=True, size=16, color=NAVY)
    ws.merge_cells("A2:C2")
    ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 30

    ws["A3"] = f"{DOC_SUBTITLE} · {datetime.now().strftime('%B %d, %Y')}"
    ws["A3"].font = Font(size=9, italic=True, color=CHARCOAL)
    ws.merge_cells("A3:C3")

    # Column headers
    header_row = 5
    for col, label in enumerate(["Section", "Type", "Content"], start=1):
        cell = ws.cell(row=header_row, column=col, value=label)
        cell.font = Font(bold=True, size=10, color=GOLD)
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="left", vertical="center")

    TYPE_LABEL = {"heading": "Heading", "bullet": "Bullet",
                  "number": "Numbered", "para": "Paragraph"}

    row = header_row + 1
    current_section = "—"
    for block in parse_blocks(text):
        content = strip_inline(block["text"])
        if not content:
            continue
        if block["type"] == "heading":
            current_section = content
            ws.cell(row=row, column=1, value=content).font = Font(bold=True, size=11, color=NAVY)
            ws.cell(row=row, column=2, value="Heading").font = Font(size=9, color=CHARCOAL)
            ws.cell(row=row, column=3, value=content).font = Font(bold=True, size=11, color=NAVY)
            for col in range(1, 4):
                ws.cell(row=row, column=col).fill = paper_fill
                ws.cell(row=row, column=col).border = bottom_rule
                ws.cell(row=row, column=col).alignment = wrap
        else:
            prefix = f"{block['num']}. " if block["type"] == "number" else ""
            ws.cell(row=row, column=1, value=current_section).font = Font(size=9, color=CHARCOAL)
            ws.cell(row=row, column=2, value=TYPE_LABEL.get(block["type"], "Text")).font = Font(size=9, color=CHARCOAL)
            ws.cell(row=row, column=3, value=prefix + content).font = Font(size=10)
            for col in range(1, 4):
                ws.cell(row=row, column=col).alignment = wrap
        row += 1

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 13
    ws.column_dimensions["C"].width = 95
    ws.freeze_panes = f"A{header_row + 1}"

    # Plain-text sheet for anyone who just wants to copy the whole thing
    ws2 = wb.create_sheet("Full text")
    ws2["A1"] = "Full response"
    ws2["A1"].font = Font(bold=True, size=11, color=NAVY)
    ws2["A1"].fill = gold_fill
    ws2["A2"] = strip_inline(text or "")
    ws2["A2"].alignment = wrap
    ws2.column_dimensions["A"].width = 120
    ws2.row_dimensions[2].height = 400

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def build_pdf(text: str, title: str = None) -> io.BytesIO:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
    )

    title = title or derive_title(text)
    navy = colors.HexColor("#" + NAVY)
    gold = colors.HexColor("#" + GOLD)
    charcoal = colors.HexColor("#" + CHARCOAL)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title=title, author=BRAND_NAME,
    )

    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle("brand", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, textColor=gold, spaceAfter=3, leading=11),
        "title": ParagraphStyle("titleS", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=20, textColor=navy, leading=25, spaceAfter=4),
        "meta": ParagraphStyle("meta", parent=base["Normal"], fontName="Helvetica-Oblique",
                               fontSize=8.5, textColor=charcoal, spaceAfter=12),
        "h1": ParagraphStyle("h1S", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=14.5, textColor=navy, spaceBefore=14, spaceAfter=5, leading=18),
        "h2": ParagraphStyle("h2S", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=12.5, textColor=navy, spaceBefore=12, spaceAfter=4, leading=16),
        "h3": ParagraphStyle("h3S", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=11, textColor=navy, spaceBefore=10, spaceAfter=3, leading=14),
        "body": ParagraphStyle("bodyS", parent=base["Normal"], fontName="Helvetica",
                               fontSize=10.5, textColor=colors.HexColor("#2B2B2B"),
                               leading=15.5, spaceAfter=8),
        "item": ParagraphStyle("itemS", parent=base["Normal"], fontName="Helvetica",
                               fontSize=10.5, textColor=colors.HexColor("#2B2B2B"),
                               leading=15, spaceAfter=4),
        "foot": ParagraphStyle("footS", parent=base["Normal"], fontName="Helvetica-Oblique",
                               fontSize=7.5, textColor=charcoal, alignment=TA_CENTER),
    }

    def inline_html(s: str) -> str:
        """Convert **bold** to <b> and escape XML-unsafe characters."""
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`([^`]+?)`", r"\1", s)
        s = re.sub(r"\[([^\]]+?)\]\([^)]+?\)", r"\1", s)
        return s

    from reportlab.platypus import Image as RLImage
    logo_path = find_logo()
    masthead = None
    if logo_path:
        try:
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(logo_path).getSize()
            h = 0.42 * inch
            masthead = RLImage(logo_path, width=h * (iw / float(ih)), height=h)
            masthead.hAlign = "LEFT"
        except Exception:
            masthead = None

    story = [
        masthead if masthead else Paragraph(BRAND_NAME.upper(), styles["brand"]),
        Spacer(1, 6) if masthead else Spacer(1, 0),
        Paragraph(inline_html(title), styles["title"]),
        HRFlowable(width="100%", thickness=1.5, color=gold,
                   spaceBefore=2, spaceAfter=6),
        Paragraph(f"{DOC_SUBTITLE} &middot; {datetime.now().strftime('%B %d, %Y')}",
                  styles["meta"]),
    ]

    # Consecutive list items get grouped into a single ListFlowable
    pending = []
    pending_kind = None

    def flush_list():
        nonlocal pending, pending_kind
        if not pending:
            return
        items = [ListItem(Paragraph(inline_html(t), styles["item"]), leftIndent=16)
                 for t in pending]
        if pending_kind == "bullet":
            story.append(ListFlowable(
                items, bulletType="bullet", start="\u2022",
                bulletColor=gold, bulletFontSize=11,
                bulletFontName="Helvetica", leftIndent=20,
            ))
        else:
            story.append(ListFlowable(
                items, bulletType="1", start=1, bulletFormat="%s.",
                bulletColor=navy, bulletFontSize=10.5,
                bulletFontName="Helvetica-Bold", leftIndent=20,
            ))
        story.append(Spacer(1, 6))
        pending = []
        pending_kind = None

    for block in parse_blocks(text):
        btype = block["type"]
        if btype in ("bullet", "number"):
            if pending_kind and pending_kind != btype:
                flush_list()
            pending_kind = btype
            pending.append(block["text"])
            continue
        flush_list()
        if btype == "heading":
            story.append(Paragraph(inline_html(block["text"]),
                                   styles[f"h{block['level']}"]))
        else:
            story.append(Paragraph(inline_html(block["text"]), styles["body"]))
    flush_list()

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.6, color=gold, spaceAfter=6))
    story.append(Paragraph(
        "For informational purposes only. Not medical, legal, or financial advice.",
        styles["foot"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

BUILDERS = {
    "docx": build_docx,
    "pptx": build_pptx,
    "xlsx": build_xlsx,
    "pdf": build_pdf,
}

MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def build(fmt: str, text: str, title: str = None):
    """Return (BytesIO, filename, mimetype) for the requested format."""
    fmt = (fmt or "").lower().strip()
    if fmt not in BUILDERS:
        raise ValueError(f"Unsupported format: {fmt}")
    # Chat-only instructions must never reach the document
    text = strip_meta(text)
    resolved_title = (title or "").strip() or derive_title(text)
    buffer = BUILDERS[fmt](text, resolved_title)
    return buffer, safe_filename(resolved_title, fmt), MIME_TYPES[fmt]
