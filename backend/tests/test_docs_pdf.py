from pathlib import Path

import pytest

from app.reporting.docs_pdf import generate_guide


def test_guide_pdf_is_generated_only_from_markdown_sources(tmp_path: Path) -> None:
    source = tmp_path / "guide.md"
    source.write_text(
        "# Guide synthétique\n\nTexte avec <script>alert('x')</script>.\n\n"
        "- Élément public\n\n```bash\necho test\n```\n",
        encoding="utf-8",
    )
    destination = generate_guide("Guide de test", [source], tmp_path / "guide.pdf")

    assert destination.read_bytes().startswith(b"%PDF-")
    assert destination.stat().st_size > 1000


def test_guide_generation_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="absentes"):
        generate_guide("Guide", [tmp_path / "missing.md"], tmp_path / "guide.pdf")
