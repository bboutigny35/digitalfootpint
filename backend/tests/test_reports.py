import io
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from openpyxl import load_workbook  # type: ignore[import-untyped]

from app.reporting.exports import (
    ReportData,
    ReportEntry,
    neutralize_spreadsheet,
    render_csv,
    render_html,
    render_pdf,
    render_xlsx,
)


def synthetic_report() -> ReportData:
    return ReportData(
        generated_at=datetime(2026, 10, 14, 20, 0, tzinfo=UTC),
        scope="Profil synthétique",
        sources_queried=("github",),
        sources_unavailable=(),
        entries=(
            ReportEntry(
                profile="Alice Test",
                connector="github",
                url="https://github.com/example",
                title='=WEBSERVICE("https://attacker.invalid")',
                snippet="<script>alert('xss')</script>",
                confidence=0.2,
                verification_status="uncertain",
                discovered_at="2026-10-14T20:00:00+00:00",
                last_checked_at="2026-10-14T20:00:00+00:00",
                published_at=None,
            ),
        ),
    )


def test_spreadsheet_exports_neutralize_formulas() -> None:
    report = synthetic_report()
    csv_content = render_csv(report, "detailed").decode("utf-8-sig")
    assert "'=WEBSERVICE" in csv_content
    workbook = load_workbook(io.BytesIO(render_xlsx(report, "detailed")), read_only=True)
    title_cell = workbook["Mentions"][2][3]
    assert title_cell.value.startswith("'=")
    assert title_cell.data_type != "f"
    assert neutralize_spreadsheet("  +cmd") == "'  +cmd"


def test_html_escapes_untrusted_content_and_pdf_is_real() -> None:
    report = synthetic_report()
    html_content = render_html(report, "detailed").decode()
    assert "<script>alert" not in html_content
    assert "&lt;script&gt;" in html_content
    assert "default-src 'none'" in html_content
    assert render_pdf(report, "detailed").startswith(b"%PDF-")


def test_report_api_supports_all_formats_and_enforces_profile_ownership(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    created = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": "Rapport", "last_name": "Test"},
    )
    profile_id = created.json()["id"]
    expected_prefixes = {
        "csv": b"\xef\xbb\xbf",
        "json": b"{",
        "xlsx": b"PK",
        "html": b"<!doctype html>",
        "pdf": b"%PDF-",
    }
    for export_format, prefix in expected_prefixes.items():
        response = client.get(
            f"/api/v1/reports/export?format={export_format}&profile_id={profile_id}"
        )
        assert response.status_code == 200
        assert response.content.startswith(prefix)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    history = client.get("/api/v1/reports")
    assert history.status_code == 200
    assert len(history.json()) == 5
    assert {item["export_format"] for item in history.json()} == set(expected_prefixes)
    assert all(item["profile_id"] == profile_id for item in history.json())
    assert (
        client.get("/api/v1/reports/export?format=json&profile_id=foreign").status_code == 404
    )
