# AI Recruitment Agent

Recruiter dashboard plus FastAPI: JD analysis, ATS sourcing, matching, ranking, outreach drafts, and interview proposals. The system does not invent candidates, send email, book a calendar, or hire without a recruiter.

## Run on a new laptop (easiest)

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Copy this project onto the laptop (`git clone` or a folder copy). Do **not** copy a `.env` that has real production keys.
3. In the project root run one command:

```bash
python run.py
```

4. Open http://localhost:3000

| | |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API docs | http://127.0.0.1:8000/docs |
| Demo login | `recruiter` / `recruiter-review` |

`run.py` creates `.env` from `.env.example` if needed, starts Postgres + API + dashboard, and opens the dashboard.
If you prefer platform scripts, `setup.ps1` and `setup.sh` still work.

Optional: put `GOOGLE_API_KEY` in `.env` if you want Gemini JD analysis. Leave `EMAIL_DRY_RUN=true` and `CALENDAR_DRY_RUN=true` unless you have live SES/calendar credentials.

Stop everything:

```bash
python stop.py
```

## Run without Docker (local Python + Node)

Needs Python 3.11+, Node 22+, and Postgres (or `docker compose up postgres -d`).

```powershell
python scripts\bootstrap_env.py
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
python scripts\seed_recruiter_dashboard.py
```

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000 and use the same demo login.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Configuration

Secrets stay in `.env`. Never commit them.

| Variable | Purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Gemini (JD analysis / embeddings) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `RECRUITER_USERNAME` / `RECRUITER_PASSWORD` | Dashboard login |
| `RECRUITER_SESSION_SECRET` | Session signing (16+ chars) |
| `EMAIL_DRY_RUN` | Keep `true` until SES/SendGrid is configured |
| `CALENDAR_DRY_RUN` | Keep `true` until Google Calendar is configured |
| `APP_ENV` | `development` on a laptop; `production` only with real secrets |
