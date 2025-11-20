## Carilla Dashboard Prototype!

A UI-rich dashboard for laptop users plus thumb-first phone navigation for Carilla’s tuning hub. Every surface is wired to a “Coming Soon” state while the full experiences are built.

### What’s inside
- Laptop dashboard with tuning hero, telemetry placeholder, and feature tiles labeled “Coming Soon.”
- Mobile-ready bottom navigation for Tune, Reels, Chat, and Profile, also marked “Coming Soon.”
- Interactive toast that confirms the “Coming Soon” state when tapping/clicking any feature.

### Run it locally
1) Open `frontend/index.html` in your browser (no build or dependencies required).
2) Resize the window below 720px to view the phone navigation bar.

### Backend (Node/Express)
- Install deps: `cd backend && npm install`
- Run dev: `npm run dev` (listens on `PORT` or 3000)
- Run prod: `npm start`
- Health: `GET /health` -> `{ ok: true }`
- Status: `GET /api/status` -> lists feature stubs
- Feature stubs: `GET /api/tuning`, `/api/reels`, `/api/chat`, `/api/profile` -> all return `{ status: "coming_soon" }`

### Deploy hints
- Vercel: if you only serve the static dashboard, set Framework to **Other/Static**, Root Directory `frontend`, empty build command, Output Directory `.`.
- Render backend: Root Directory `backend`, Build Command `npm install`, Start Command `npm start`, Env var `PORT` provided by Render.

### File map
- `frontend/index.html` — self-contained HTML/CSS/JS for the dashboard and mobile nav preview.
- `backend/src/server.js` — Express server with health, status, and feature stub routes.
- `backend/package.json` — scripts and dependencies for the backend service.
