# AI JobHunter frontend

The React/Vite frontend provides authenticated registration and login, resume
management, job search and persisted discovery results, saved jobs, resume
matching, job preferences, and an application tracker.

## Development

From this directory:

```powershell
npm install
npm run dev
```

The default backend URL is `http://127.0.0.1:8000`. Override it with a local
`.env.local` file:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Run `npm run build` for a production build and `npm run lint` for ESLint.
Backend setup, environment variables, tests, and safety limitations are
documented in the repository-root [README](../README.md).
