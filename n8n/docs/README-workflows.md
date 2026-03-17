# Shorts pipelines (indexing + upload)

Two workflows: **index** clips into Postgres and move to `processed/`, then **upload** by class from Postgres, then delete files.

---

## 1. Index Shorts (Transcribe, Classify, to DB)

**File:** `Upload Workflow v1.json` (workflow name: *Index Shorts (Transcribe, Classify, to DB)*)

**Flow:**  
Find oldest MP4 (excluding `processed/`) → transcribe (ffmpeg → WAV → Whisper) → classify (content class + tags) → generate title → insert row into `clips` → **move file** to `processed/`.

**Configure:**

- **Find:** Only picks files under `/home/node/.n8n-files/shorts` that are **not** under `.../shorts/processed/`. Put new MP4s in `shorts/` or a subfolder other than `processed`.
- **Move:** Files are moved to `.../shorts/processed/<filename>.mp4`. Create that folder on the host, or let the move command create it with `mkdir -p`.
- **Postgres:** Attach your n8n Postgres credential (for example `n8n-postgres` on a mapped host port). The `clips` table needs `file_path`, `title`, `transcript`, `clip_class`, `tags`, and `status` along with the usual metadata columns such as `clip_id`, `created_at`, and `reserved_at`. The *Insert Clip (Postgres)* node is set up to use a parameterized INSERT so column mapping and the `tags` array are handled explicitly. If n8n warns about parameters, double‑check that the credential is set and that the expression is plugged into the right option for query parameters.
- **Classify:** Uses Ollama with the same credential as the title node. The list of content classes (cars, tech, music, gaming, and so on) lives in the prompt inside the *Classify Video* node. Edit that prompt if you want to change the classes.

**Important:** After indexing, the file lives in `processed/` and is **not** picked again by this workflow.

---

## 2. Upload Shorts (Schedule, Postgres, YouTube)

**File:** `Upload Shorts (Schedule, Postgres, YouTube).json`

**Flow:**  
Get next group from `channel_groups` → compute next class (round robin) → find oldest **queued** clip for that class → reserve clip → read file from `file_path` (processed path) → upload to YouTube → wait 15 min → delete file → mark clip **posted** → advance scheduler (`class_idx`, `next_due_at`).

**Configure:**

- **Postgres:** Same credential as above. Needs:
  - `channel_groups`: `group_key`, `credential_key`, `class_cycle` (TEXT[]), `class_idx`, `min_gap_minutes`, `next_due_at`, `active`.
  - `clips`: rows with `status = 'queued'` and `clip_class` matching the current class.
- **YouTube:** Attach your YouTube OAuth credential (e.g. “Antigoyslop”) to the *Upload to YouTube* node. The node uses binary property `data` (the MP4) and `title` from the clip row.
- **Query parameters:** If your n8n Postgres node expects a different option name than `queryParams`, change it in the node options (e.g. “Query Parameters”) so `$1` gets the value from the expression.

**Scheduler:**

- At least one row in `channel_groups` with `active = true` and `next_due_at <= now()`.
- `class_cycle`: list of content classes, e.g. `{cars,tech,music}`. The workflow picks the next class by `class_idx` and finds a queued clip with that `clip_class`.
- After a successful run, `class_idx` is advanced and `next_due_at` is set to `now() + min_gap_minutes`.

**If no clip is found** for the current class, the “If Clip Found” false branch currently has no nodes; you can later add carousel (try next class) or an “no video” alert.

---

## Folder layout (inside container)

- **Unprocessed (indexing picks from here):**  
  `/home/node/.n8n-files/shorts/` (and subfolders), **except** `.../shorts/processed/`.
- **Processed (upload reads from here, then deletes):**  
  `/home/node/.n8n-files/shorts/processed/`.

On the host, that usually maps from `/mnt/shorts/`; ensure `processed` exists (or is created by the move command) and that the upload workflow only deletes files after a successful upload + wait.

---

## Summary

| Step | Indexing workflow | Upload workflow |
|------|-------------------|------------------|
| Source | Oldest MP4 in `shorts/` (not in `processed/`) | Queued clip in Postgres for current class |
| After run | File **moved** to `shorts/processed/`, row in `clips` with `status = 'queued'` | File **deleted**; clip `status = 'posted'`; scheduler advanced |

You run indexing to fill the queue; you run the upload workflow (manual or on a schedule) to post by class and free disk by deleting the file after upload.

---

## 3. Feed Playlist + Trim Playlist (YouTube source playlist)

If you **scrape content from a YouTube playlist** (e.g. with a separate “prefekt” workflow), two workflows keep that playlist stocked and under the 5,000-video limit:

| Workflow | File | What it does |
|----------|------|----------------|
| **Feed Playlist** | `Feed Playlist (Search YouTube by Category, Add to Playlist).json` | Every 12h: search long-form, **filter to ≤ 45 min**, add to playlist (no duplicates). Pipeline turns them into shorts. |
| **Trim Playlist** | `Trim Playlist (Delete Oldest When 80% Full).json` | Daily at 06:00: if playlist has **> 100 videos**, (playlist’ delete oldest to **cap at 100** (storage). |

**Setup:** See **FEED-PLAYLIST-DESIGN.md** for playlist limit, API key, playlist ID, and credentials. Run **`sql/playlist_seen_videos.sql`** once so the Feed workflow can avoid adding duplicate videos (Postgres stores already-seen video IDs).
