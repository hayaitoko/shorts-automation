# YouTube Shorts Automation

This project is a set of n8n workflows and a small Postgres schema that turn long‑form YouTube videos into short clips you can schedule and upload.

It uses n8n, Docker, Ollama (LLM), Whisper ASR, Postgres, Google OAuth2, ffmpeg, and yt‑dlp to create short‑form content for multiple accounts across multiple categories.

You get:

- A queue of long videos to pull from
- A clip generator that uses Whisper for transcripts and Ollama for choosing segments
- A simple scheduler that uploads clips from Postgres and keeps track of what ran

Everything is built around one Postgres database called `n8n_queue`.

---

## What it does

At a high level:

- **Discover videos**  
A feed workflow talks to the YouTube Data API, searches by content category, respects your quota, and adds new video IDs into a Postgres table.
- **Reset daily counters**  
A tiny workflow runs on a schedule and resets per‑channel upload counts in Postgres.
- **Create clips**  
A workflow takes queued video IDs, downloads the source video with `yt-dlp`, sends audio to Whisper, asks Ollama to pick several segments, and renders those segments to MP4 files in a `holding` folder.
- **Index clips**  
Another workflow watches that `holding` folder, runs transcription and classification again, generates a title with Ollama, and writes rows into the `clips` table while moving files into a `processed` folder.
- **Upload**  
Finally, the upload workflow looks at the scheduler tables, picks the next content class to post, reserves a clip in Postgres, reads the processed file from disk, uploads it to YouTube, waits a bit, deletes the file, and marks the clip as posted.

All of the state that matters (what clips exist, which ones are queued, what was posted) lives in Postgres, not inside n8n nodes.

---

## Quick start

1. **Clone and configure**
  - Copy [.env.example](.env.example) to `.env`.
  - Set at least `POSTGRES_PASSWORD` to something strong. Keep `.env` out of git.
2. **Start the core services** (more detail in [docs/docker.md](docs/docker.md))
  - Postgres: `docker compose -f docker/postgres/docker-compose.yml up -d`
  - Ollama (optional but recommended): `docker compose -f docker/ollama/docker-compose.yml up -d`, then pull a model such as `llama3.1:8b`
  - Whisper ASR (optional): `docker compose -f docker/whisper/docker-compose.yml up -d`
3. **Set up the database**
  - Create the `n8n_queue` database and user.
  - Run [full_schema_n8n_queue.sql](migration/full_schema_n8n_queue.sql) once.
4. **Import workflows into n8n**
  - Import the JSON files from [n8n/workflows](n8n/workflows/).
  - Point the Postgres nodes at your `n8n_queue` database.
  - Add YouTube OAuth2, Ollama, and optional Discord credentials in the n8n UI.
  - In the Whisper HTTP nodes, keep `http://whisper-asr:9010` if n8n and Whisper share a Docker network, or change it to `http://localhost:9010` or your host IP if n8n runs outside Docker.
5. **File paths**
  - Make sure the folders used in the workflows exist and are mounted into the n8n container.
  - Out of the box the workflows assume paths similar to `/var/lib/n8n/shorts/raw`, `/var/lib/n8n/shorts/holding`, and `/var/lib/n8n/shorts/processed`. Adjust them if your mount points differ.

---

## Workflows (n8n)

Here is where each piece of the pipeline lives:


| Workflow                     | File                                                                                                                                             | What it is used for                                                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Feed Playlist**            | [Feed Playlist (Youtube API).json](n8n/workflows/Feed%20Playlist%20(Youtube%20API).json)                                                         | Searches YouTube by content class, keeps an eye on quota, writes new video IDs into `incoming_videos`, and records what has already been seen.                             |
| **Daily Upload Count Reset** | [Daily Upload Count Reset.json](n8n/workflows/Daily%20Upload%20Count%20Reset.json)                                                               | Once a day, runs `UPDATE daily_upload_counts SET count = 0`. Keeps daily limits easy to reason about.                                                                      |
| **Create Shorts**            | [Create Shorts (Playlist, Create Clips, Render Clips).json](n8n/workflows/Create%20Shorts%20(Playlist,%20Create%20Clips,%20Render%20Clips).json) | Takes queued items from `incoming_videos`, downloads the full video, sends audio to Whisper, asks Ollama to pick segments, and renders clips to `holding`.                 |
| **Index Shorts**             | [Index Shorts (Transcribe, Classify, to DB).json](n8n/workflows/Index%20Shorts%20(Transcribe,%20Classify,%20to%20DB).json)                       | Looks at the `holding` folder, gets a transcript, classifies the content, generates a title, and inserts rows into the `clips` table before moving files into `processed`. |
| **Upload Shorts**            | [Upload Shorts (Schedule, Postgres, YouTube).json](n8n/workflows/Upload%20Shorts%20(Schedule,%20Postgres,%20YouTube).json)                       | Drives the posting schedule. Chooses the next class to post, reserves a clip, uploads to YouTube, waits, deletes the file, and marks the row as posted.                    |


If you want a bit more color on how the indexing and upload pieces fit together, see [n8n/docs/README-workflows.md](n8n/docs/README-workflows.md).

---

## Docker

You can run the supporting services with the compose files in `docker/`:


| Stack        | Path                                                                     | Role                                                                              |
| ------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **Postgres** | [docker/postgres/docker-compose.yml](docker/postgres/docker-compose.yml) | Hosts the `n8n_queue` database. Reads credentials from `.env`.                    |
| **Ollama**   | [docker/ollama/docker-compose.yml](docker/ollama/docker-compose.yml)     | Runs a local LLM that n8n uses for titles, classification, and segment selection. |
| **Whisper**  | [docker/whisper/docker-compose.yml](docker/whisper/docker-compose.yml)   | Runs Whisper for transcription on port 9010.                                      |


For network and environment variable details, check [docs/docker.md](docs/docker.md).

---

## Security

This repo is meant to be safe to publish. A few things are built in:

- There are no secrets in the workflows. Credential objects and private IPs are stripped before committing.
- Postgres, YouTube OAuth2, Ollama, and Discord credentials all live in n8n itself, not in git.
- The workflows use `http://whisper-asr:9010` as a service name inside Docker. If you run n8n directly on the host, point that URL at `localhost` or your own host IP instead.
- The Postgres password comes from `.env`. The compose file refuses to start if it is missing.

On your side, do not add `.env` or any file with tokens or API keys to git. The defaults in [.gitignore](.gitignore) and [.env.example](.env.example) are there to make that hard to do by accident.

---

## Project layout

```
├── .env.example          # Template for env vars (copy to .env)
├── .gitignore            # Excludes .env, credentials, etc.
├── README.md              # This file
├── full_schema_n8n_queue.sql # SQL schema
├── docs/
│   └── docker.md         # Docker setup
├── docker/
│   ├── ollama/           # Ollama compose
│   ├── postgres/         # Postgres compose
│   └── whisper/          # Whisper ASR compose
├── n8n/
│   ├── docs/             # Workflow design notes
│   ├── sql/              # Extra SQL (playlist_seen_videos, etc.)
│   └── workflows/        # n8n workflow JSON (sanitized)
└── scripts/
    └── sanitize_workflows.py   # One-time: strip credentials from exports
```

---

## License

Use and adapt as you like. Ensure compliance with YouTube’s Terms of Service and API quotas when running at scale.