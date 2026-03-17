# Docker services for this project

This folder contains small Docker setups for Postgres, Ollama, and Whisper. They are meant to be boring and predictable. Secrets are not baked into the files. Values like passwords live in a `.env` file in the project root. See [.env.example](../.env.example).

## What you need installed

- Docker and Docker Compose
- For Ollama and Whisper you will want an NVIDIA GPU and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- A Docker network that these containers can share. By default the files use a network called `dockge_default`. You can create it with:

```bash
docker network create dockge_default
```

If you already have a network you prefer, you can change the network section in each compose file.

## 1. Postgres (n8n_queue)

Postgres holds everything the workflows care about: clips, channel groups, daily upload counters, feed inventory targets, and so on.

From the project root:

```bash
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD to something real

docker compose -f docker/postgres/docker-compose.yml up -d
```

After the container is running, run the schema once with `psql` or your usual client, using [migration/full_schema_n8n_queue.sql](../migration/full_schema_n8n_queue.sql).

## 2. Ollama

Ollama is used as the language model for:

- Picking interesting segments
- Classifying clips into content classes
- Generating titles

Start it with:

```bash
docker compose -f docker/ollama/docker-compose.yml up -d
# Then pull at least one model, for example:
docker exec -it ollama ollama pull llama3.1:8b
```

In n8n, create an Ollama credential that points to `http://ollama:11434` if n8n runs in the same Docker network, or to your host and port if n8n runs outside of Docker.

## 3. Whisper ASR

Whisper provides transcription for the indexing and clip‑creation workflows.

Bring it up with:

```bash
docker compose -f docker/whisper/docker-compose.yml up -d
```

The workflows expect Whisper to be reachable as `http://whisper-asr:9010` when n8n is in the same Docker network. If you run n8n on your host machine, change the HTTP Request nodes to use `http://localhost:9010` or your host IP instead.

## A few safety notes

- Do not commit `.env` or any file that contains real passwords or API keys.
- The Postgres compose file refuses to start if `POSTGRES_PASSWORD` is missing, which is on purpose.
- Workflows stored in this repo are sanitized. They do not include credential IDs or private IP addresses. After you import them, you still need to wire up Postgres, YouTube OAuth, Discord webhooks, Ollama, and Whisper in the n8n UI.
