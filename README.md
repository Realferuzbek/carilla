Frontend – Dashboard & Phone Shell

Location: frontend/index.html

Deployment: https://carilla.vercel.app/

The frontend is a single, carefully designed HTML/CSS/JS file that powers both desktop and mobile layouts.

Desktop dashboard

Dark, gradient background tuned for long viewing.

Four primary feature tiles:

Home – Signal view
Calm overview of the “garage pulse”: cars, builds, and activity.

Reels – Motion drops
Video-first lane for builds, pulls, and sound.

Tuning – Exact knobs
Core surface for AI tuning previews (photo → tuned photo).

Profile – Identity
Owner identity, cars, and preferences in one place.

Each tile is wired to a “Coming soon” state, but the UI flow, copy, and interactions are already production-style.

Mobile shell

Below ~720px width, the layout flips into a phone-first experience:

Bottom navigation bar: Home, Reels, Tuning, Profile

Cards adapt to thumb-reach and smaller screens.

This lets the same codebase be demoed both as a desktop dashboard and a mobile-style app.

The current frontend is static (no React build or bundler), which keeps deployment simple and reliable while the AI layer is being built.

Backend – Node/Express Scaffold

Location: backend/

The backend is minimal but real: it already behaves like a small product API, not a mock.

Stack

Node.js + Express

CORS enabled

JSON responses only

Feature metadata endpoints

These endpoints power the current “Coming soon” surfaces and will be extended later:

GET /api/tuning

GET /api/reels

GET /api/chat

GET /api/profile

Each returns a small JSON payload:

{
  "key": "tuning",
  "title": "Precision Tuning Studio",
  "message": "Detailed tuning endpoints are being wired."
}


This keeps the frontend decoupled from copy and allows future feature-level analytics.

Upload pipeline for Tuning (without AI yet)

Carilla already accepts and stores user car photos, ready for the AI layer:

POST /api/tuning/upload

Accepts a single file under field name photo

Validates MIME type (JPEG / PNG / WEBP)

Saves originals into:

backend/uploads/user_cars/


Appends an entry to:

backend/data/tuning_log.json


with:

id (job id)

created_at (ISO timestamp)

original_path

tuned_path (currently null)

status ("uploaded" for now)

GET /api/tuning/log

Returns the current log as JSON for debugging and inspection.

This gives the project a real storage surface and audit trail for tuning jobs, even before the AI model is integrated.

AI Workspace – Preparing the Tuning Engine

Location: ai/

The AI directory contains the structure and scripts for the future tuning engine.

Dataset layout
ai/
  datasets/
    raw/
      sport_gentra/              # raw photos: 50–100 real Sport-tuned Gentrаs
    processed/
      sport_gentra/
        images/                  # centre-cropped 768×768 PNGs
        captions.txt             # one text caption per image


The planned dataset:

50–100 photos of real black Sport-tuned Chevrolet Gentrаs

Hero angle: front-left 3/4, chest height, 3–5m distance

Shot on a modern phone camera, no heavy filters

Preprocessing script

File: ai/scripts/prepare_sport_gentra_dataset.py

Responsibilities:

Read raw photos from datasets/raw/sport_gentra/

Centre-crop each image to a square

Resize to 768 × 768

Save normalized PNGs into processed/sport_gentra/images/

For each image, append a caption line to processed/sport_gentra/captions.txt, e.g.:

“ultra realistic photo of a black Chevrolet Gentra 2024 in aggressive sport tuning, wide body kit, carbon fiber details, parked in a premium studio, soft lighting, 8k detail”

This turns a real-world photoshoot into a clean training dataset.

Colab training spec (LoRA)

File: ai/training/colab_sport_gentra_lora.md

This markdown file describes a Google Colab notebook that will:

Use PyTorch + diffusers with a photoreal Stable Diffusion–style base model.

Train a LoRA on the Sport Gentra dataset at 768×768 resolution.

Optimize only LoRA parameters (not the full model).

Save a single LoRA weights file (e.g. sport_gentra_lora.safetensors).

Include a test cell that:

loads the base model + LoRA

runs img2img on a sample Gentra photo

visualizes the tuned result inside Colab.

This keeps the research/ML side reproducible and separate from the product code.

Planned Tuning Pipeline (Near-Term Roadmap)

Once the dataset is captured and the first LoRA is trained, the system will evolve into a full end-to-end pipeline:

Data collection

Capture 50–100 high-quality Sport Gentra photos.

Store in ai/datasets/raw/sport_gentra/.

Training

Run the preprocessing script locally.

Train a Sport Gentra LoRA in Colab using the spec in ai/training/colab_sport_gentra_lora.md.

Iterate until photo-real quality is reached.

Inference service

Build a Python FastAPI service that:

Accepts a user Gentra photo.

Runs img2img with:

a photoreal diffusion base model,

the Sport Gentra LoRA,

an internal text prompt describing the Sport style.

(Optionally) uses ControlNet to preserve geometry.

Outputs a tuned photo at the hero angle.

Integration with Node backend

Extend POST /api/tuning/upload to call the FastAPI service.

Save tuned results into backend/uploads/tuned_results/.

Update tuning_log.json with tuned_path and "processed" status.

Frontend wiring

Connect the Tuning – Exact knobs tile to a detail view where users can:

Upload a photo of their Gentra.

See a before/after comparison when the tuned image is ready.

Even though the first release will support only one car, one angle, one style, the pipeline is designed to be reusable for additional models and styles by retraining new LoRAs.

Feature surfaces – product intent

For admissions or reviewers, here is how each tile maps to future functionality:

Home – Signal view
High-level “garage pulse”: overview of cars, builds, upcoming tuning jobs, and recent activity.

Reels – Motion drops
Video-first lane for builds, pulls, exhaust clips, and behind-the-scenes content, tagged by car and tuning setup.

Tuning – Exact knobs
Core AI product. Realistic previews of tuning setups for the user’s exact car using a diffusion + LoRA pipeline.

Profile – Identity
User accounts, garage list, history of tuning jobs, saved setups, and privacy settings.

How to run locally
Frontend
cd frontend
# open index.html directly in your browser


Or serve it with any simple static file server.

Backend
cd backend
npm install
npm run dev   # or: npm start


Test endpoints:

# feature metadata
curl http://localhost:3000/api/tuning

# upload a test image
curl -X POST http://localhost:3000/api/tuning/upload \
  -F "photo=@/path/to/your/gentra.jpg"


Uploaded files appear under backend/uploads/user_cars/, and jobs are logged in backend/data/tuning_log.json.

Author & responsibilities

Feruzbek Qurbonov

Product + UX design for the Carilla dashboard (desktop + mobile).

Implementation of the static frontend shell.

Design and implementation of the Node/Express backend scaffold:

Feature metadata endpoints

Image upload + logging for tuning jobs.

Design of the AI workspace:

Dataset layout and preprocessing pipeline

Colab training spec for a Sport Gentra LoRA

Long-term vision and constraints:

Quality over quantity (one car, one angle, one style to start)

Real photos as input, no cartoonish looks

Clean separation between product, infrastructure, and ML.

This prototype is a thin vertical slice of a larger idea: it is intentionally small, but built like the first step of a real product.