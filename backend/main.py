import json
import uuid
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from config import get_settings
from document_processor import process_upload, validate_upload
from gemini_service import analyze_document_vision, ask_document_question
from schemas import ApiError, AskRequest, AskResponse, ScanResponse, ScanResult
from storage import InMemoryStore

load_dotenv()
settings = get_settings()
app = FastAPI(title="VISIO")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = InMemoryStore()
connections: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast(job_id: str, data: dict) -> None:
    payload = json.dumps({"job_id": job_id, **data})
    for ws in connections[job_id][:]:
        try:
            await ws.send_text(payload)
        except Exception:
            connections[job_id].remove(ws)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, job_id: str = Query(...)) -> None:
    await websocket.accept()
    connections[job_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connections[job_id]:
            connections[job_id].remove(websocket)


def _rate_key(request: Request, action: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{action}:{host}"


def error_response(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ApiError(code=code, error=message, status=status, details=details).model_dump(),
    )


@app.get("/")
def root() -> dict:
    return {"status": "VISIO ONLINE", "version": "1.0"}


@app.post("/scan", response_model=ScanResponse, responses={400: {"model": ApiError}, 429: {"model": ApiError}})
async def scan_document(
    request: Request,
    file: UploadFile = File(...),
    job_id: str | None = Query(default=None),
    pdf_mode: str = Query(default="first_page"),
    pdf_page_limit: int = Query(default=3, ge=1, le=10),
):
    if not store.allow_rate(_rate_key(request, "scan"), limit=20, window_seconds=60):
        return error_response(429, "rate_limit_scan", "Rate limit exceeded for /scan")
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        return error_response(400, "file_too_large", f"File too large. Max {settings.max_file_size_mb}MB.")

    try:
        if pdf_mode not in {"first_page", "all_pages"}:
            return error_response(400, "invalid_pdf_mode", "pdf_mode must be first_page or all_pages")
        validate_upload(file.filename or "upload.bin", file.content_type)
        job_id = job_id or str(uuid.uuid4())
        await broadcast(job_id, {"step": "validating", "message": "Validating upload..."})
        await broadcast(job_id, {"step": "uploading", "message": f"Processing {file.filename}..."})
        await broadcast(job_id, {"step": "rendering_pages", "message": "Rendering pages..."})
        image_data = process_upload(
            file_bytes,
            file.filename or "upload.bin",
            settings.max_image_dimension,
            pdf_mode=pdf_mode,
            pdf_page_limit=pdf_page_limit,
        )
        await broadcast(job_id, {"step": "scanning", "message": "Analyzing with Gemini..."})
        analysis = analyze_document_vision(image_data["base64"], image_data["media_type"])

        result = ScanResult(
            filename=file.filename or "upload.bin",
            file_type=image_data.get("file_type", "unknown"),
            file_size_mb=round(file_size_mb, 2),
            preview_base64=image_data["base64"],
            media_type=image_data["media_type"],
            document_type=analysis.get("document_type", "Unknown"),
            language=analysis.get("language", "English"),
            summary=analysis.get("summary", ""),
            full_text=analysis.get("full_text", ""),
            entities=analysis.get("entities", []),
            key_values=analysis.get("key_values", {}),
            tables=analysis.get("tables", []),
            sentiment=analysis.get("sentiment", {"label": "neutral", "score": 0.5}),
            quality_score=int(analysis.get("quality_score", 0)),
            confidence=int(analysis.get("confidence", 0)),
            raw_model_output=analysis.get("raw_model_output", ""),
            page_count=int(image_data.get("page_count", 1)),
            processed_page_count=int(image_data.get("processed_page_count", 1)),
            pdf_mode=str(image_data.get("pdf_mode", "first_page")),
        ).model_dump()
        store.set_latest(job_id, result)
        await broadcast(job_id, {"step": "complete", "message": "Done"})
        return ScanResponse(job_id=job_id, result=result)
    except ValueError as exc:
        return error_response(400, "validation_error", str(exc))
    except Exception as exc:
        return error_response(500, "scan_failed", "Failed to scan", {"reason": str(exc)})


@app.post("/ask", response_model=AskResponse, responses={400: {"model": ApiError}, 429: {"model": ApiError}})
async def ask_question(request: Request, body: AskRequest, job_id: str = Query(...)):
    if not store.allow_rate(_rate_key(request, "ask"), limit=60, window_seconds=60):
        return error_response(429, "rate_limit_ask", "Rate limit exceeded for /ask")
    question = body.question.strip()
    if not question:
        return error_response(400, "question_required", "Question required")
    doc = store.get_latest(job_id)
    if not doc:
        return error_response(404, "job_not_found", "No scan found for job")
    answer = ask_document_question(question, doc["preview_base64"], doc["media_type"], doc.get("full_text", ""))
    return AskResponse(question=question, answer=answer)


@app.get("/latest", response_model=ScanResponse, responses={404: {"model": ApiError}})
def get_latest(job_id: str | None = Query(default=None)):
    if not job_id:
        job_id = store.latest_job_id()
    if not job_id:
        return error_response(404, "no_document", "No document scanned")
    data = store.get_latest(job_id)
    if not data:
        return error_response(404, "job_not_found", "No scan found for job")
    return ScanResponse(job_id=job_id, result=data)


@app.get("/status")
def status():
    return {"ok": True}
