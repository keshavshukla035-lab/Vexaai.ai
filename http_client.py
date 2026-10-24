"""External HTTP helpers for FormFriend AI.

Only this module may import the requests package; protocols.py imports the
functions from here instead.
"""

import os

import requests

# Public file host used to turn generated PDF bytes into a real, working
# download URL. For sensitive documents, set the PDF_UPLOAD_URL secret to
# your own endpoint (multipart POST with a "file" field that returns a URL).
DEFAULT_PDF_UPLOAD_URL = "https://file.io"


def upload_pdf(pdf_bytes: bytes, filename: str = "formfriend-document.pdf") -> str | None:
    """Upload PDF bytes and return the real download URL, or None on failure.

    The URL is taken verbatim from the upload service response - it is never
    invented locally. Returns None when the upload or parsing fails.
    """
    endpoint = os.environ.get("PDF_UPLOAD_URL") or DEFAULT_PDF_UPLOAD_URL
    try:
        response = requests.post(
            url=endpoint,
            files={"file": (filename, pdf_bytes, "application/pdf")},
            data={"expires": "1w", "maxDownloads": "25"},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        link = payload.get("link") or payload.get("url")
        if isinstance(link, str) and link.startswith(("http://", "https://")):
            return link

    # Some services return the bare URL as plain text.
    body = response.text.strip()
    if body.startswith(("http://", "https://")) and " " not in body and len(body) <= 300:
        return body
    return None
      
