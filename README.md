# Carilla — AI-assisted car tuning workflow (concept demo)

Carilla is a concept demo of an AI-assisted car tuning product: capture a car’s current setup and goals, collect the right photos, and (once a dataset exists) generate structured tuning suggestions and before/after summaries.

**Status:** Concept demo — AI tuning is pending dataset collection.

## Demo

- Live: https://carilla.vercel.app

## Visuals

Add screenshots to make this admissions/reviewer-friendly:

- `docs/screenshots/dashboard.png` — dashboard tiles + status banner
- `docs/screenshots/tuning.png` — Tuning (Exact knobs) feature preview
- `docs/screenshots/mobile.png` — mobile dashboard + bottom navigation

(Visuals are currently not in the repo: **TBD**.)

## Features

- Dashboard with clear feature readiness labels: **Prototype UI / Needs data / Planned**
- Feature Preview pages for each module with structured sections:
  - Purpose
  - What it will do
  - Inputs / Outputs
  - MVP scope
  - Current status
  - Next steps
- Modules included in the concept demo:
  - **Home — Signal view:** at-a-glance “garage pulse” and readiness overview
  - **Reels — Motion drops:** short clips and build highlights (requires data/storage wiring)
  - **Tuning — Exact knobs:** photo + setup-note intake to prepare AI tuning jobs (requires dataset + model)
  - **Profile — Identity:** account/access/settings model (planned)

## Tech Stack

- **Frontend:** Static single-page UI (HTML/CSS/JavaScript)
- **Backend (optional scaffold):** Node.js API server (intended for uploads/metadata; AI not implemented)
- **Deployment:** Vercel (serving the frontend demo)

## How It Works

- The UI is a single-page experience with lightweight view state (dashboard → feature detail).
- Feature pages are generated from a shared “Feature Preview” template.
- Feature content is driven by a centralized feature data map so desktop and mobile views stay consistent.
- A backend scaffold exists to support future wiring (uploads, job records, results), but the live demo is primarily a frontend concept.

## Evidence / Results

What is real today:
- Live concept demo is deployed and reviewable: https://carilla.vercel.app
- Product status is communicated in the UI (concept demo; dataset required before AI tuning outputs)

What is intentionally not claimed yet (TBD):
- No model training or inference results (no accuracy/quality metrics yet)
- No user/adoption metrics
- No performance audit scores (e.g., Lighthouse)

## My Role & Contributions

**Role:** Solo builder (concept, product design, implementation, deployment).

I owned:
- Product decomposition into clear modules (Home/Reels/Tuning/Profile)
- UI prototype and interaction flow (desktop + mobile)
- Structured Feature Preview system (purpose → scope → status → next steps)
- Honest readiness/status communication (Prototype UI / Needs data / Planned)
- Backend direction as a scaffold for future uploads/jobs (not marketed as complete)

## Project Report

Deep technical report: **TBD** (will document architecture, data requirements, evaluation plan, and limitations once the AI pipeline work begins).

## Roadmap

- Add screenshots/GIFs to the repo so reviewers can skim visually
- Define a minimum dataset spec (required angles, quality checks, labels, metadata)
- Collect and label the initial dataset for the target vehicle platform
- Wire uploads → storage and create “tuning job” records
- Implement a baseline approach (e.g., retrieval-first) before any advanced model work
- Add an evaluation protocol (human review + consistency checks + latency targets)
- Integrate tuning outputs into the UI with provenance/explanations

## License

TBD (add a license file if you want others to reuse the code).

## Contact

- GitHub: https://github.com/Realferuzbek
- Repo: https://github.com/Realferuzbek/carilla
