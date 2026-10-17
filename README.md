# AI JobHunter

AI JobHunter is a React/Vite and FastAPI application for discovering jobs,
comparing saved jobs with a verified resume, and organizing applications for
user review. MongoDB stores user-owned data; Tavily discovers public web
results; Gemini powers selected analysis services; Playwright supports
URL-validated application-page inspection.

## Safety and data model

- Web-search results are untrusted. A discovered result is not automatically
  an authentic job or a saved normalized job. Tavily prioritizes recognized
  job-board domains, but URL validation does not establish that a posting is
  genuine or still open; users should review the employer and posting.
- Clearly informational results (such as tutorials and documentation) are
  filtered before URL review and are reported as skipped search results.
- The dashboard distinguishes persisted search results from normalized jobs.
  HTTPS results that need URL verification are kept in the live-results list
  with a manual-review label, but are not eligible to save until they pass
  backend URL checks. A job is added to Saved Jobs only after the
  individual-posting and URL validation checks pass. New accounts
  automatically search for general current openings when no prior search
  results exist.
- Resume matching and application preparation require the user's verified
  resume.
- Generated or mapped application data is for user review. The application
  submission gate never submits an application.
- CAPTCHA, OTP, authentication, and anti-bot controls are not bypassed.
- Never put real API keys, MongoDB credentials, or signing secrets in source
  control.

## Requirements

- Python 3.10 or newer
- Node.js 20.19+ or 22.12+ (required by Vite 8)
- MongoDB (local instance or an Atlas connection string)
- Tavily and Gemini API keys for live search and AI-backed features

## Backend setup

In PowerShell:

```powershell
cd Backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
New-Item -Path .env -ItemType File
```

Add `MONGO_URI`, a long random `SECRET_KEY`, `TAVILY_API_KEY`, and
`GEMINI_API_KEY` to `Backend/.env` using your own values. Keep that file
private.
Set `FRONTEND_BASE_URL` to the deployed frontend URL; it is used for password
reset links and automatically added to the CORS allowlist. For this deployment,
use `https://ai-job-hunter-phi-two.vercel.app`. `FRONTEND_ORIGINS` can list
additional exact frontend origins, comma-separated. To enable forgot-password
emails, also set `SMTP_HOST`, `SMTP_PORT` (normally `587` with STARTTLS), and
`SMTP_FROM_EMAIL`. Set
`SMTP_USERNAME` and `SMTP_PASSWORD` together when the mail relay requires
authentication. Keep all SMTP credentials in the backend environment, never
in source control. Use the deployed HTTPS frontend URL for
`FRONTEND_BASE_URL`. Reset links are single-use and expire after 30 minutes.

Install the Chromium browser used by Playwright:

```powershell
python -m playwright install chromium
```

Start the API from the `Backend` directory:

```powershell
python -m uvicorn app.main:app --reload
```

If the virtual environment is in the repository root instead, run this from
the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn --app-dir Backend --env-file Backend\.env app.main:app --reload
```

In VS Code, the **Backend: Start FastAPI** task runs the root virtual
environment with `Backend` as its working directory.

The API documentation is available at `http://127.0.0.1:8000/docs`.

For local development only, if SMTP is not configured and you need to reset
an existing local account, stop the API and run
`python reset_local_password.py` from the `Backend` directory. The command
refuses non-local MongoDB hosts, prompts for the account email, and hides
the new password while typing.

## Frontend setup

In another terminal:

```powershell
cd Frontend
npm install
npm run dev
```

The Vite development server uses `http://127.0.0.1:8000` as the API default.
To use another backend URL, create a local `Frontend/.env.local` containing
`VITE_API_BASE_URL=http://your-backend-host:port`.
For deployment, set `VITE_API_BASE_URL` to the public backend URL at frontend
build time and set `FRONTEND_BASE_URL` on the backend to the deployed frontend
URL so it is allowed by CORS. For the current deployment, configure
`VITE_API_BASE_URL=https://ai-jobhunter-backend.onrender.com` in Vercel and
`FRONTEND_BASE_URL=https://ai-job-hunter-phi-two.vercel.app` in Render.

## Main user flow

1. Register and sign in; manage your account name and email from Profile.
2. Upload a PDF or DOCX resume, extract its text, and verify it.
3. Save target roles and locations in Job Preferences.
4. Search for jobs. Discovered results remain separate from verified Saved
   Jobs; review the result details and the backend normalization outcome.
5. Match a Saved Job against a verified resume.
6. Add a job to the application tracker, review it, and manually update its
   status. Inspect the application page or map form fields from the verified
   resume for review. Explicit approval and a separate safety check are
   required before any later human-controlled action.

## Tests and checks

From `Backend`:

```powershell
python -m pytest tests
```

The URL verification and safety tests are unit-level checks. The database
integration test requires a reachable MongoDB instance and uses unique test
records.

To run the isolated Playwright demo against the local HTML form (it uses
synthetic sample data and never submits anything):

```powershell
python -m playwright install chromium
python human_review_demo.py
```

From `Frontend`:

```powershell
npm run build
npm run lint
```

Some legacy lint findings may remain in untouched files; use the command output
to identify their locations.

## Current limitations

- Search discovery does not guarantee that results are individual postings;
  listings and URLs requiring manual review are intentionally not promoted to
  Saved Jobs.
- Matching is initiated by the user from a Saved Job. It does not run
  automatically for every discovered result.
- Application preparation, page inspection, and verified-resume field mapping
  are available for review. The form-filling helper is not yet integrated into
  the application-specific API/UI workflow. No API/UI action automatically
  submits a job application.
- AI/search features depend on external API availability and quotas.
