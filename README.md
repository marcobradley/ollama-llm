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

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | URL of the local Ollama instance |
| `MODEL` | `llama3.2` | Default model used when none is specified in a request |

Edit `.env` to override these values before running `docker compose up`.

## API endpoints

### `GET /health`
Returns `200 OK` when both the service and the Ollama backend are reachable.

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

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'
```

Optional request fields:
- `model` (string) – override the default model
- `stream` (boolean, default `false`) – stream the response as NDJSON

### `POST /chat`
Send a user message and receive a chat response.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

Optional request fields:
- `model` (string) – override the default model
- `stream` (boolean, default `false`) – stream the response as NDJSON

Interactive API docs (Swagger UI) are available at `http://localhost:8000/docs`.

## Linux notes

On Linux, `host.docker.internal` is not added automatically by Docker. The `docker-compose.yml` already includes an `extra_hosts` entry that maps `host.docker.internal` to the host gateway, so no additional configuration is needed.

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