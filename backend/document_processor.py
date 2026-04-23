import base64
import io
import fitz
from PIL import Image, ImageDraw, ImageFont


SUPPORTED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp", "gif", "bmp", "txt"}
SUPPORTED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "application/pdf",
    "text/plain",
}


def validate_upload(filename: str, content_type: str | None) -> None:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")
    if content_type and content_type not in SUPPORTED_MIME:
        raise ValueError(f"Unsupported content type: {content_type}")


def process_upload(
    file_bytes: bytes,
    filename: str,
    max_dimension: int,
    pdf_mode: str = "first_page",
    pdf_page_limit: int = 3,
) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return _pdf_to_image(file_bytes, max_dimension, pdf_mode=pdf_mode, pdf_page_limit=pdf_page_limit)
    if ext == "txt":
        return _text_to_image(file_bytes)

    try:
        Image.open(io.BytesIO(file_bytes)).verify()
    except Exception as exc:
        raise ValueError("Invalid image upload") from exc
    return _process_image(file_bytes, ext or "png", max_dimension)


def _pdf_to_image(pdf_bytes: bytes, max_dimension: int, pdf_mode: str, pdf_page_limit: int) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    if page_count == 0:
        raise ValueError("PDF has no pages")

    if pdf_mode == "all_pages":
        page_indexes = list(range(min(page_count, max(1, pdf_page_limit))))
    else:
        page_indexes = [0]

    rendered_pages: list[str] = []
    preview_payload: dict | None = None
    for idx in page_indexes:
        page = doc[idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        image_bytes = pix.tobytes("png")
        processed = _process_image(image_bytes, "pdf", max_dimension, page_count=page_count)
        rendered_pages.append(processed["base64"])
        if preview_payload is None:
            preview_payload = processed

    if preview_payload is None:
        raise ValueError("Unable to render PDF preview")

    preview_payload["pdf_pages_base64"] = rendered_pages
    preview_payload["processed_page_count"] = len(rendered_pages)
    preview_payload["pdf_mode"] = pdf_mode
    return preview_payload


def _process_image(img_bytes: bytes, file_type: str, max_dimension: int, page_count: int = 1) -> dict:
    image = Image.open(io.BytesIO(img_bytes))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    w, h = image.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        image = image.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    return {
        "base64": base64.b64encode(png_bytes).decode("utf-8"),
        "media_type": "image/png",
        "file_type": file_type,
        "width": image.size[0],
        "height": image.size[1],
        "page_count": page_count,
    }


def _text_to_image(text_bytes: bytes) -> dict:
    text = text_bytes.decode("utf-8", errors="ignore")[:3000]
    image = Image.new("RGB", (900, max(450, len(text.split("\n")) * 22 + 80)), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 20), text, fill="black", font=font)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png = buf.getvalue()
    return {
        "base64": base64.b64encode(png).decode("utf-8"),
        "media_type": "image/png",
        "file_type": "txt",
        "width": image.size[0],
        "height": image.size[1],
        "page_count": 1,
    }
