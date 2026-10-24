"""Minimal pure-Python PDF writer for FormFriend AI.

Converts plain text into a small, valid PDF 1.4 file using only Python's
built-in modules. Agentverse does not guarantee PDF libraries such as
reportlab, so no third-party package is used here.

Text is rendered in Helvetica 11 pt on US Letter pages, wrapped at 80
characters. Only Latin-1 characters are supported; anything else (for
example CJK or emoji) is replaced with "?".
"""

MAX_LINE_CHARS = 80
LINES_PER_PAGE = 45
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 72
START_Y = 720
LINE_HEIGHT = 14


def _sanitize(line: str) -> str:
    line = line.replace("\t", "    ")
    cleaned = []
    for char in line:
        if ord(char) < 32 or ord(char) == 127:
            cleaned.append(" ")
          else:
            cleaned.append(char)
    line = "".join(cleaned)
    # PDF standard encoding is close to Latin-1; drop anything else.
    return line.encode("latin-1", "replace").decode("latin-1")


def _escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(line: str, max_chars: int = MAX_LINE_CHARS) -> list:
    words = line.split()
    if not words:
        return [""]
       wrapped = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            wrapped.append(current)
        while len(word) > max_chars:
            wrapped.append(word[:max_chars])
            word = word[max_chars:]
        current = word
    if current:
        wrapped.append(current)
    return wrapped


def text_to_pdf(text: str) -> bytes:
    """Convert plain text into valid PDF bytes (pure built-ins, no dependencies)."""
    pages = [[]]
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        for wrapped in _wrap(_sanitize(raw.strip())):
            if len(pages[-1]) >= LINES_PER_PAGE:
                pages.append([])
            pages[-1].append(wrapped)
    if not pages[0]:
        pages = [["(empty document)"]]

    page_count = len(pages)
    last_object = 3 + 2 * page_count

    kids = " ".join(f"{4 + 2 * index} 0 R" for index in range(page_count))
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
      
        2: f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("latin-1"),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    for index, page_lines in enumerate(pages):
        page_object = 4 + 2 * index
        stream_object = page_object + 1
        rows = ["BT", "/F1 11 Tf", f"{LINE_HEIGHT} TL", f"{MARGIN_X} {START_Y} Td"]
        for line in page_lines:
            rows.append(f"({_escape(line)}) Tj T*")
        rows.append("ET")
        stream = "\n".join(rows).encode("latin-1")
        objects[page_object] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                  f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_object} 0 R >>"
        ).encode("latin-1")
        objects[stream_object] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for number in range(1, last_object + 1):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode("latin-1")
        out += objects[number]
        out += b"\nendobj\n"
      
    xref_offset = len(out)
    out += f"xref\n0 {last_object + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for number in range(1, last_object + 1):
        out += f"{offsets[number]:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {last_object + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)
