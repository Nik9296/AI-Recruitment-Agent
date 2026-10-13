Recruiter review dashboard (Next.js + React).

On a new laptop, start the whole stack from the repo root with `.\setup.ps1` (Windows) or `./setup.sh` (macOS/Linux). Then open http://localhost:3000 and sign in with `recruiter` / `recruiter-review`.

To run only the UI against a local API:

```
npm install
npm run dev
```

`API_PROXY_TARGET` (default `http://127.0.0.1:8000`) is the FastAPI origin. The dashboard calls `/api/v1/...` on the same origin; Next.js rewrites those requests to FastAPI.
