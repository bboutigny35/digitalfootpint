"""Génération des guides PDF à partir des sources Markdown maintenues."""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

USER_GUIDE_SOURCES = (
    "user-guide/getting-started.md",
    "user-guide/scans.md",
    "user-guide/reports.md",
    "user-guide/sensitive-data.md",
    "user-guide/removal-requests.md",
)
ADMIN_GUIDE_SOURCES = (
    "administration/configuration.md",
    "administration/backup-restore.md",
    "administration/troubleshooting.md",
    "installation/debian13.md",
    "installation/docker.md",
    "security/security-model.md",
    "security/data-retention.md",
)


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"DigitalFootprint — {document.page}")
    canvas.restoreState()


def _markdown_story(markdown: str) -> list[Any]:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "GuideBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        spaceAfter=5,
    )
    code = ParagraphStyle(
        "GuideCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=6,
        spaceAfter=7,
    )
    heading_styles = {
        1: styles["Heading1"],
        2: styles["Heading2"],
        3: styles["Heading3"],
    }
    story: list[Any] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(Paragraph(escape(" ".join(paragraph_lines)), body))
            paragraph_lines.clear()

    def flush_code() -> None:
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), code))
            code_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                flush_code()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            story.append(Paragraph(escape(heading.group(2)), heading_styles[level]))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            match = bullet if bullet is not None else numbered
            assert match is not None
            text = match.group(1)
            marker = "•" if bullet else "–"
            story.append(Paragraph(escape(text), body, bulletText=marker))
            continue
        if not line.strip():
            flush_paragraph()
            story.append(Spacer(1, 2 * mm))
            continue
        paragraph_lines.append(line.strip())
    flush_paragraph()
    flush_code()
    return story


def generate_guide(title: str, sources: Iterable[Path], destination: Path) -> Path:
    source_paths = tuple(sources)
    missing = [str(path) for path in source_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Sources Markdown absentes: {', '.join(missing)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GuideTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f766e"),
        fontSize=25,
        leading=31,
    )
    story: list[Any] = [
        Spacer(1, 55 * mm),
        Paragraph(escape(title), title_style),
        Spacer(1, 8 * mm),
        Paragraph(
            "Généré depuis les sources Markdown versionnées du dépôt.",
            ParagraphStyle("Subtitle", parent=styles["BodyText"], alignment=TA_CENTER),
        ),
        PageBreak(),
    ]
    for index, source in enumerate(source_paths):
        if index:
            story.append(PageBreak())
        story.extend(_markdown_story(source.read_text(encoding="utf-8")))
    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="Projet DigitalFootprint",
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return destination


def generate_documentation(docs_root: Path, output_directory: Path) -> tuple[Path, Path]:
    user = generate_guide(
        "DigitalFootprint — Guide utilisateur",
        (docs_root / relative for relative in USER_GUIDE_SOURCES),
        output_directory / "digitalfootprint-guide-utilisateur.pdf",
    )
    admin = generate_guide(
        "DigitalFootprint — Guide administrateur",
        (docs_root / relative for relative in ADMIN_GUIDE_SOURCES),
        output_directory / "digitalfootprint-guide-administrateur.pdf",
    )
    return user, admin


def main() -> None:
    parser = argparse.ArgumentParser(description="Générer les guides PDF DigitalFootprint")
    parser.add_argument("--docs-root", type=Path, default=Path("docs"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/documentation"))
    arguments = parser.parse_args()
    for path in generate_documentation(arguments.docs_root, arguments.output_dir):
        print(path)


if __name__ == "__main__":
    main()
