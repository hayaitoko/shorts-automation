# Security

## Reporting a vulnerability

If you find a security issue in this project, please report it responsibly. Do not open a public issue for sensitive findings.

- Prefer a private report (e.g. GitHub Security Advisories or a private contact if you have it).
- Include steps to reproduce and impact.

## What we do to keep the repo safe

- **No hardcoded secrets**  
  Workflows and configs in the repo do not contain:
  - Passwords or API keys
  - Credential IDs that point to your n8n instance
  - Private IPs (internal addresses are replaced with placeholders like `whisper-asr`)

- **Credentials live in n8n**  
  After importing workflows, you configure Postgres, YouTube OAuth2, Ollama, and optional Discord in n8n. Those are never stored in this repository.

- **Environment variables**  
  Sensitive values (e.g. `POSTGRES_PASSWORD`) are set in a `.env` file that is **not** committed. See [.env.example](.env.example).

- **.gitignore**  
  We ignore `.env`, `.env.local`, credentials files, and similar so they are not accidentally committed.

## What you should do

- Never commit `.env` or any file containing real passwords or keys.
- Use a strong Postgres password and restrict DB access to trusted hosts.
- Keep n8n and Docker images updated.
- If you export workflows from n8n that contain credential references or private IPs, run [scripts/sanitize_workflows.py](scripts/sanitize_workflows.py) (or equivalent) before committing.
