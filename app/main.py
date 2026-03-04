"""FastAPI application that proxies requests to a local Ollama LLM instance."""

import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")

app = FastAPI(title="Ollama LLM Interface", version="1.0.0")


class OllamaRequest(BaseModel):
    prompt: str
    model: str
    stream: bool = False


# Aliases kept for clear endpoint semantics
ChatRequest = OllamaRequest
GenerateRequest = OllamaRequest


def _generate_to_chat_response(generate_response: dict) -> dict:
    content = generate_response.get("response", "")
    chat_response = dict(generate_response)
    chat_response.pop("response", None)
    chat_response["message"] = {"role": "assistant", "content": content}
    return chat_response


async def _probe_chat_support(client: httpx.AsyncClient) -> str:
    try:
        response = await client.post(f"{OLLAMA_HOST}/api/chat", json={})
        if response.status_code == 404:
            return "unsupported"
        if response.status_code in {200, 400, 422}:
            return "supported"
        return "unknown"
    except httpx.HTTPError:
        return "unknown"


@app.get("/health")
async def health():
    """Check that the service and Ollama backend are reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
            chat_support = await _probe_chat_support(client)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama backend unreachable at {OLLAMA_HOST}: {exc}",
        ) from exc

    health_payload = {
        "status": "ok",
        "ollama_host": OLLAMA_HOST,
        "chat_endpoint": chat_support,
    }
    if chat_support == "unsupported":
        health_payload["note"] = "Ollama /api/chat is unavailable; /chat requests will fallback to /api/generate."

    return health_payload


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
    payload = {"model": request.model, "prompt": request.prompt, "stream": request.stream}

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
    payload = {
        "model": request.model,
        "messages": [{"role": "user", "content": request.prompt}],
        "stream": request.stream,
    }
    fallback_payload = {
        "model": request.model,
        "prompt": request.prompt,
        "stream": request.stream,
    }

    if request.stream:
        async def _stream():
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST", f"{OLLAMA_HOST}/api/chat", json=payload
                    ) as resp:
                        if resp.status_code == 404:
                            async with client.stream(
                                "POST", f"{OLLAMA_HOST}/api/generate", json=fallback_payload
                            ) as fallback_resp:
                                fallback_resp.raise_for_status()
                                async for chunk in fallback_resp.aiter_bytes():
                                    yield chunk
                            return

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
            try:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/chat", json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise

            fallback_response = await client.post(
                f"{OLLAMA_HOST}/api/generate", json=fallback_payload
            )
            fallback_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _generate_to_chat_response(fallback_response.json())
