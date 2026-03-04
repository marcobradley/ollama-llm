"""FastAPI application that proxies requests to a local Ollama LLM instance."""

import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.environ.get("MODEL", "llama3.2")

app = FastAPI(title="Ollama LLM Interface", version="1.0.0")


class OllamaRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: bool = False


# Aliases kept for clear endpoint semantics
ChatRequest = OllamaRequest
GenerateRequest = OllamaRequest


@app.get("/health")
async def health():
    """Check that the service and Ollama backend are reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama backend unreachable at {OLLAMA_HOST}: {exc}",
        ) from exc
    return {"status": "ok", "ollama_host": OLLAMA_HOST}


@app.get("/models")
async def list_models():
    """List models available on the Ollama backend."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch models from {OLLAMA_HOST}: {exc}",
        ) from exc
    return response.json()


@app.post("/generate")
async def generate(request: GenerateRequest):
    """Generate a completion for the given prompt."""
    model = request.model or DEFAULT_MODEL
    payload = {"model": model, "prompt": request.prompt, "stream": request.stream}

    if request.stream:
        async def _stream():
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST", f"{OLLAMA_HOST}/api/generate", json=payload
                    ) as resp:
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes():
                            yield chunk
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

        return StreamingResponse(_stream(), media_type="application/x-ndjson")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate", json=payload
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return response.json()


@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a chat message and receive a response."""
    model = request.model or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": request.prompt}],
        "stream": request.stream,
    }

    if request.stream:
        async def _stream():
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST", f"{OLLAMA_HOST}/api/chat", json=payload
                    ) as resp:
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes():
                            yield chunk
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

        return StreamingResponse(_stream(), media_type="application/x-ndjson")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat", json=payload
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return response.json()
