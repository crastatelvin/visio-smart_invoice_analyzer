# Architecture Decisions - VISIO

## Scope
This implementation targets a single-user demo path with production-minded interfaces.

## Why job IDs for websocket and ask/scan?
Job IDs isolate progress and results per scan and avoid global websocket cross-talk.

## Why canonical backend preview?
The same processed image is used for model analysis and UI preview, avoiding mismatch on PDFs or transformed images.

## Why JSON model output?
JSON schema is easier to validate than delimiter-based text and allows controlled fallback behavior.

## Why in-memory storage now?
It keeps setup simple for build day while preserving a clear seam (`storage.py`) for Redis/DB later.
