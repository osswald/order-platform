"""HTTP response helpers for PDF downloads."""

from __future__ import annotations

from urllib.parse import quote

from fastapi.responses import Response


def pdf_download_response(pdf_bytes: bytes, filename: str) -> Response:
    safe_name = filename if filename.lower().endswith(".pdf") else f"{filename}.pdf"
    encoded = quote(safe_name)
    disposition = f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{encoded}'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )
