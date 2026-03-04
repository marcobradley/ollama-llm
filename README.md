# ollama-llm

A Docker container that provides a REST API interface to a locally running [Ollama](https://ollama.com/) instance. Designed for use with **Windows + Docker Desktop**, where the host machine is reachable from containers via `host.docker.internal`.

## Prerequisites

| Requirement | Notes |
|---|---|
| [Ollama](https://ollama.com/download) | Running on your Windows host (default port `11434`) |
| [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) | v4.0+ recommended |
| At least one Ollama model | e.g. `ollama pull llama3.2` |

## Quick start

```bash
# 1. Clone the repository
git clone https://github.com/marcobradley/ollama-llm.git
cd ollama-llm

# 2. Copy the example environment file (edit if needed)
cp .env.example .env

# 3. Build and start the container
docker compose up --build
```

The API is now available at `http://localhost:8000`.

If you run the prebuilt image directly, map host port `8000` to container port `8000`:

```powershell
docker run --rm -p 8000:8000 mbradleyhome/ollama-api:latest
```

Do not map to `11434` (for example `-p 8000:11434`), because port `11434` belongs to Ollama on your host, not to this API container.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | URL of the local Ollama instance |

Edit `.env` to override these values before running `docker compose up`.

## API endpoints

### `GET /health`
Returns `200 OK` when both the service and the Ollama backend are reachable.
The response also includes `chat_endpoint` with one of:
- `supported` – Ollama chat API is available
- `unsupported` – Ollama chat API is not available (`/chat` falls back to `/generate`)
- `unknown` – chat capability could not be determined

```bash
curl http://localhost:8000/health
```

### `GET /models`
Lists all models available on the Ollama backend.

```bash
curl http://localhost:8000/models
```

### `POST /generate`
Generate a completion for a prompt.

```powershell
curl.exe -X POST "http://localhost:8000/generate" `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"llama3.2:1b\",\"prompt\":\"Why is the sky blue?\"}"
```

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:1b", "prompt": "Why is the sky blue?"}'
```

Request fields:
- `model` (string, required) – model name (e.g. `llama3.2:1b`)
- `stream` (boolean, default `false`) – stream the response as NDJSON

### `POST /chat`
Send a user message and receive a chat response.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/chat" `
   -Method POST `
   -ContentType "application/json" `
  -Body '{ "model": "llama3.2:1b", "prompt": "Hello, how are you?" }'
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:1b", "prompt": "Hello, how are you?"}'
```

Request fields:
- `model` (string, required) – model name (e.g. `llama3.2:1b`)
- `stream` (boolean, default `false`) – stream the response as NDJSON

If your local Ollama does not support `/api/chat` and returns `404`, this endpoint automatically falls back to `/api/generate`.

Interactive API docs (Swagger UI) are available at `http://localhost:8000/docs`.

## Common errors

- `405 Method Not Allowed` on `/chat` or `/generate`
  - Cause: request was sent with `GET`.
  - Fix: use `POST` with JSON body.

- `422 Unprocessable Entity` with `Field required` for `model`
  - Cause: request body is missing `model`.
  - Fix: include a model name, for example `"model":"llama3.2:1b"`.

- `503` from `/health` or `502` from `/chat`/`/generate` with backend unreachable/connection failed
  - Cause: this API cannot reach Ollama at `OLLAMA_HOST`.
  - Fix: verify Ollama responds on `http://localhost:11434/api/tags` and that containers can resolve/reach `host.docker.internal`.

- Docker error: `Bind for 0.0.0.0:8000 failed: port is already allocated`
  - Cause: another container/process is already using host port `8000`.
  - Fix: stop the conflicting process/container, or run on a different host port (for example `-p 8001:8000`).

## Linux notes

On Linux, `host.docker.internal` is not always added automatically by Docker. If needed, add this under your service in `docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## Project structure

```
.
├── app/
│   ├── main.py           # FastAPI application
│   └── requirements.txt  # Python dependencies
├── .env.example          # Example environment variables
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Container definition
└── README.md
```