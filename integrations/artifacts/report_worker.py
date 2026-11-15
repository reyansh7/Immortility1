"""Fixed report builder. Broker supplies an owned staging directory, never model paths.

No uploads, URLs fetched, macros, scripts, shell, template code or user documents.
DOCX structure can be tested, but publication requires a separate render gate.
"""

import hashlib
import json
import re
import sys
import time
from html import escape as html_escape
from pathlib import Path
from xml.sax.saxutils import escape


def markdown_text(value):
    # Draft content is literal text, never executable Markdown, HTML or images.
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", html_escape(value))


def text(value, limit=1200):
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= limit
        or any(ord(c) < 32 and c not in "\n\t" for c in value)
    ):
        raise ValueError("Invalid plain text")
    return value


def build(request):
    checkpoint = time.perf_counter()
    phases = {}
    def measured(name):
        nonlocal checkpoint
        current = time.perf_counter()
        phases[name] = round((current-checkpoint)*1000, 3)
        checkpoint = current
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import black
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from pypdf import PdfReader
    import pypdfium2 as pdfium
    measured("dependency_import")

    folder = Path(request["output_dir"])
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Staging scope unavailable")
    draft, sources = request["draft"], request["sources"]
    title = text(draft["title"], 100)
    summary = text(draft["summary"], 1000)
    if not re.fullmatch(r"[A-Za-z0-9 ]{3,100}", title):
        raise ValueError("Plain descriptive title required")
    if not 1 <= len(sources) <= 3 or not 2 <= len(draft["sections"]) <= 5:
        raise ValueError("Short report limits exceeded")
    known = {source["source_id"] for source in sources}
    blocks = [("summary", summary)]
    for section in draft["sections"]:
        heading = text(section["heading"], 80)
        if (
            not re.fullmatch(r"[A-Za-z0-9 ]{3,80}", heading)
            or not 1 <= len(section["paragraphs"]) <= 4
            or not section["citations"]
            or not set(section["citations"]) <= known
        ):
            raise ValueError("Invalid section or source references")
        blocks.append(("heading", heading))
        for paragraph in section["paragraphs"]:
            blocks.append(("body", text(paragraph) + " [" + ", ".join(section["citations"]) + "]"))
    if not 500 <= sum(len(value) for kind, value in blocks if kind != "heading") <= 7000:
        raise ValueError("Substantive short report required")
    body_paragraphs = [value for kind, value in blocks if kind == "body"]
    if len(set(body_paragraphs)) != len(body_paragraphs):
        raise ValueError("Repeated report paragraphs")
    blocks.append(("heading", "Sources"))
    for source in sources:
        # Sources are broker-owned metadata from the reviewed public catalog.
        blocks.append(
            (
                "source",
                f"[{source['source_id']}] {source['title']}\n{source['url']}\nRetrieved {source['retrieved_at']}\nSHA256 {source['sha256']}",
            )
        )
    for name in ("report.md", "report.docx", "report.pdf"):
        if (folder / name).exists():
            raise ValueError("Existing output refused")

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.75)
    section.left_margin = section.right_margin = Inches(0.8)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Arial", Pt(11)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.15
    for name in ("Title", "Heading 1"):
        document.styles[name].font.color.rgb = RGBColor(0, 0, 0)
        document.styles[name].font.name = "Arial"
    document.styles["Title"].font.size = Pt(23)
    document.styles["Heading 1"].font.size = Pt(15)
    document.core_properties.author = "Immortility"
    document.core_properties.title = title
    document.core_properties.subject = "Public source research report"
    document.add_heading(title, level=0)
    for kind, value in blocks:
        if kind == "heading":
            document.add_heading(value, level=1)
        else:
            paragraph = document.add_paragraph(value)
            if kind == "source":
                paragraph.paragraph_format.space_after = Pt(10)
                for run in paragraph.runs:
                    run.font.size = Pt(9)
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run("Page ")
    page_field = OxmlElement("w:fldSimple")
    page_field.set(qn("w:instr"), "PAGE")
    footer._p.append(page_field)
    document.save(folder / "report.docx")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "ReportSource",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            spaceAfter=10,
            splitLongWords=True,
        )
    )
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 23
    styles["Title"].leading = 27
    styles["Title"].textColor = black
    styles["Heading1"].fontName = "Helvetica-Bold"
    styles["Heading1"].fontSize = 15
    styles["Heading1"].leading = 19
    flow = [Paragraph(escape(title), styles["Title"]), Spacer(1, 10)]
    for kind, value in blocks:
        style = (
            styles["Heading1"]
            if kind == "heading"
            else styles["ReportSource"]
            if kind == "source"
            else styles["ReportBody"]
        )
        flow.append(Paragraph(escape(value).replace("\n", "<br/>"), style))

    def footer_pdf(canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(letter[0] - 0.8 * 72, 0.4 * 72, f"Page {doc.page}")

    SimpleDocTemplate(
        str(folder / "report.pdf"),
        pagesize=letter,
        topMargin=0.75 * 72,
        bottomMargin=0.75 * 72,
        leftMargin=0.8 * 72,
        rightMargin=0.8 * 72,
        title=title,
        author="Immortility",
    ).build(flow, onFirstPage=footer_pdf, onLaterPages=footer_pdf)
    markdown = (
        "# "
        + title
        + "\n\n"
        + "\n\n".join(("## " if kind == "heading" else "") + markdown_text(value) for kind, value in blocks)
        + "\n"
    )
    (folder / "report.md").write_text(markdown, encoding="utf-8")

    measured("construction")
    reopened = Document(folder / "report.docx")
    actual_docx = "\n".join(p.text for p in reopened.paragraphs)
    if title not in actual_docx or any(value not in actual_docx for _, value in blocks):
        raise ValueError("DOCX readback failed")
    reader = PdfReader(folder / "report.pdf", strict=True)
    if (
        reader.is_encrypted
        or not 1 <= len(reader.pages) <= 8
        or any(key in reader.trailer["/Root"] for key in ("/OpenAction", "/AA", "/AcroForm"))
        or any(page.get("/Annots") or page.get("/AA") for page in reader.pages)
        or reader.trailer["/Root"].get("/Names")
    ):
        raise ValueError("PDF verification failed")
    actual_pdf = " ".join(page.extract_text() for page in reader.pages)
    normalized = lambda value: re.sub(r"\s+", "", value)
    if normalized(title) not in normalized(actual_pdf) or any(
        normalized(value) not in normalized(actual_pdf) for _, value in blocks
    ):
        raise ValueError("PDF text verification failed")
    measured("readback")
    pdf = pdfium.PdfDocument(str(folder / "report.pdf"))
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=1.25)
            try:
                image = bitmap.to_pil()
                if image.convert("L").getextrema()[0] > 245:
                    raise ValueError("Blank rendered page")
                image.save(folder / f"page-{index + 1}.png")
            finally:
                bitmap.close()
                page.close()
    finally:
        pdf.close()
    measured("rendering")
    files = []
    for name in ("report.md", "report.pdf", "report.docx"):
        path = folder / name
        files.append(
            {
                "name": name,
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "parsed": True,
                "rendered": name != "report.docx",
                "publication_allowed": name != "report.docx",
            }
        )
    measured("hashing")
    return {
        "timing_ms": phases,
        "files": files,
        "pdf_pages": len(reader.pages),
        "pdf_rendered": True,
        "docx_structure_verified": True,
        "docx_rendered": False,
        "docx_blocker": "Verified DOCX renderer is unavailable; DOCX publication stays disabled.",
    }


if __name__ == "__main__":
    try:
        raw = sys.stdin.buffer.readline(64001)
        if len(raw) > 64000:
            raise ValueError("Input limit")
        print(json.dumps(build(json.loads(raw))), flush=True)
    except Exception:
        print('{"error":"artifact_verification_failed"}', flush=True)
        sys.exit(1)
