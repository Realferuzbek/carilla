# Carilla — AI-Assisted Car Tuning Workflow (Prototype)

Carilla is a **prototype-stage** product for an AI-assisted car tuning workflow: users upload car photos, the system logs a tuning “job”, and the product is designed to evolve into generating tuned outputs programmatically.

Live demo: https://carilla.vercel.app/

> Transparency (code-backed): the backend currently stores uploads and job logs, while most product surfaces return “coming soon” descriptors. AI tuning outputs are not generated yet in this repo.

---

## What problem this tackles

Car tuning decisions are visual and iterative. Users want to explore styles, compare variants, and keep a structured history of what they tried.  
Carilla is built toward turning this workflow into:
- structured photo inputs,
- trackable tuning jobs,
- and (next) AI-generated tuned results.

---

## What is implemented in this repo (code-backed)

This repo contains three parts:

1) **Frontend UI prototype** (`frontend/`)  
2) **Backend API** (`backend/`)  
3) **AI tooling (dataset prep + training notes)** (`ai/`)

---

## Frontend (UI prototype)

- Static “Carilla Dashboard” UI: `frontend/index.html`
- Presents the product navigation concept:
  - `home`
  - `reels`
  - `tuning`
  - `profile`
- The frontend is a UI prototype and is not wired to the backend in code.

---

## Backend API (Express)

Backend lives in `backend/`.

### Feature descriptor endpoints (currently “coming soon”)
These endpoints respond with a small JSON descriptor `{ key, title, message }`:
- `GET /api/tuning`
- `GET /api/reels`
- `GET /api/chat`
- `GET /api/profile`

### Photo upload + job logging (implemented)
#### Upload a car photo
- `POST /api/tuning/upload`
  - Expects `multipart/form-data` with field name: `photo`
  - Allowed image types: `image/jpeg`, `image/png`, `image/webp`
  - Stores the uploaded image on disk
  - Appends a new entry to the tuning log JSON
  - Responds with a `job` object and a message confirming storage (AI output not wired yet)

#### Read the tuning job log
- `GET /api/tuning/log`
  - Returns an array of logged jobs (or `[]` when empty)

### Local persistence locations (created automatically)
- `backend/uploads/user_cars/` — uploaded user photos
- `backend/uploads/tuned_results/` — reserved for future tuned outputs (currently unused)
- `backend/data/tuning_log.json` — append-only log of uploaded jobs

---

## AI tooling (dataset prep + training notes)

AI-related code lives in `ai/` and is **not integrated** into the backend yet.

### Dataset preparation
- Script: `ai/scripts/prepare_sport_gentra_dataset.py`
  - Reads raw images from: `ai/datasets/raw/sport_gentra/`
  - Outputs processed images + captions under: `ai/datasets/processed/sport_gentra/`

### Training notes
- `ai/training/colab_sport_gentra_lora.md`
  - Colab-oriented LoRA training steps (documentation)

> Positioning: the repo contains a specific dataset path (`sport_gentra`), but Carilla itself is described generally as a car-tuning workflow prototype.

---

## Tech stack

- **Frontend**: HTML + CSS + vanilla JavaScript (static prototype)
- **Backend**: Node.js + Express + Multer + CORS
- **AI tooling**: Python (Pillow) + training notes (Markdown)

---

## Run locally

### Frontend (UI)
Option A: open directly  
- Open `frontend/index.html` in your browser

Option B: serve static (recommended)
```bash
cd frontend
python -m http.server 5173
```
Then open:
- `http://localhost:5173/`

### Backend (API)
```bash
cd backend
npm ci
npm run dev
```

Quick API checks:
```bash
# Feature descriptor
curl http://localhost:3000/api/tuning

# Upload an image
curl -X POST http://localhost:3000/api/tuning/upload \
  -F "photo=@/path/to/image.jpg"

# Read job log
curl http://localhost:3000/api/tuning/log
```

### AI dataset prep (optional)
```bash
pip install pillow
python ai/scripts/prepare_sport_gentra_dataset.py
```

---

## Security notes (current state)

- CORS is wide-open in code and there is **no authentication** layer in the backend yet.
- Upload validation is limited to MIME checks (jpeg/png/webp).
- For production: add auth, rate limiting, stricter validation, and safe storage policies.

---

## My role & contributions

I led Carilla as the **product owner and context/architecture engineer**:
- defined the product scope, user flows, and roadmap milestones
- designed the overall system direction (UI → API → AI pipeline integration)
- handled environment setup, deployment configuration, and debugging
- used AI-assisted coding tools to accelerate implementation while owning final decisions and shipping

---

## Roadmap 

- Wire the frontend prototype to the backend API (show upload status + job history)
- Replace “coming soon” surfaces (`reels`, `chat`, `profile`) with real implementations
- Integrate an AI tuning pipeline:
  - run inference on uploaded photos
  - write tuned outputs into `backend/uploads/tuned_results`
  - mark jobs complete + serve tuned results via API
- Expand dataset tooling beyond the current dataset layout

---

## License
MIT (see `LICENSE`)
