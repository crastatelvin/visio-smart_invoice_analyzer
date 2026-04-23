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


@app.get("/")
def root() -> dict:
    return {"status": "VISIO ONLINE", "version": "1.0"}


@app.post("/scan", response_model=ScanResponse, responses={400: {"model": ApiError}, 429: {"model": ApiError}})
async def scan_document(request: Request, file: UploadFile = File(...), job_id: str | None = Query(default=None)):
    if not store.allow_rate(_rate_key(request, "scan"), limit=20, window_seconds=60):
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded for /scan"})
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        return JSONResponse(status_code=400, content={"error": f"File too large. Max {settings.max_file_size_mb}MB."})

    try:
        validate_upload(file.filename or "upload.bin", file.content_type)
        job_id = job_id or str(uuid.uuid4())
        await broadcast(job_id, {"step": "uploading", "message": f"Processing {file.filename}..."})
        await broadcast(job_id, {"step": "converting", "message": "Converting document..."})
        image_data = process_upload(file_bytes, file.filename or "upload.bin", settings.max_image_dimension)
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
        ).model_dump()
        store.set_latest(job_id, result)
        await broadcast(job_id, {"step": "complete", "message": "Done"})
        return ScanResponse(job_id=job_id, result=result)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": "Failed to scan", "details": {"reason": str(exc)}})


@app.post("/ask", response_model=AskResponse, responses={400: {"model": ApiError}, 429: {"model": ApiError}})
async def ask_question(request: Request, body: AskRequest, job_id: str = Query(...)):
    if not store.allow_rate(_rate_key(request, "ask"), limit=60, window_seconds=60):
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded for /ask"})
    question = body.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question required"})
    doc = store.get_latest(job_id)
    if not doc:
        return JSONResponse(status_code=404, content={"error": "No scan found for job"})
    answer = ask_document_question(question, doc["preview_base64"], doc["media_type"], doc.get("full_text", ""))
    return AskResponse(question=question, answer=answer)


@app.get("/latest", response_model=ScanResponse, responses={404: {"model": ApiError}})
def get_latest(job_id: str | None = Query(default=None)):
    if not job_id:
        job_id = store.latest_job_id()
    if not job_id:
        return JSONResponse(status_code=404, content={"error": "No document scanned"})
    data = store.get_latest(job_id)
    if not data:
        return JSONResponse(status_code=404, content={"error": "No scan found for job"})
    return ScanResponse(job_id=job_id, result=data)


@app.get("/status")
def status():
    return {"ok": True}
