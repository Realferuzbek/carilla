# AI Experiments

This folder contains AI experiment scaffolding and notes. Existing `sport_gentra` materials are kept as-is.

## Paper 1 (Stable Diffusion LoRA, Identity Learning)

Paper 1 focuses on **identity learning** for a text-to-image LoRA using the custom token `<carilla_gentra>`.

Planned study setup:

- Task: text-to-image identity learning (Stable Diffusion LoRA)
- Dataset size: 80 total images
- Split: 70 train / 10 validation
- Prompt set: 10 identity prompts (`experiments/prompts_identity_v1.txt`)
- Seed set: 4 seeds (`experiments/seeds_v1.txt` -> `111, 222, 333, 444`)
- Evaluation groups: `E0`, `E1`, `E2`, `E3` (tracked in experiment notes/results later)

Paper 1 scaffolding added:

- Raw dataset target: `datasets/raw/gentra_luxury_v1/`
- Manifest template: `datasets/manifests/gentra_luxury_v1_manifest.csv`
- Colab runbook placeholder: `training/colab_paper1_lora.md`

Notes:

- This is scaffolding only. Training implementation, dependencies, and execution scripts are intentionally not added yet.
- Keep prompts/seeds versioned so future papers can compare runs cleanly.

## Paper 1 Dataset Preparation (CLI)

Paper 1 dataset prep expects raw image filenames in this format:

- `{view}_{lighting}_{location}_{id}.{ext}`
- Example: `front_day_parking_001.jpg`
- Example: `rear45_sunset_street_002.png`

Allowed tags:

- Views: `front`, `rear`, `left`, `right`, `front45`, `rear45`, `closeup`
- Lighting: `day`, `cloudy`, `sunset`, `indoor`
- Location: `parking`, `street`, `garage`

Center-crop note:

- The prep script center-crops to square before resizing, so keep the car roughly centered in source photos.

Install minimal Python dependencies:

```bash
python -m pip install -r ai/requirements.txt
```

Example commands (Windows-friendly):

```bash
python ai/scripts/dataset_prep.py
python ai/scripts/dataset_prep.py --overwrite
python ai/scripts/validate_dataset.py
python ai/scripts/validate_dataset.py --raw_dir ai/datasets/raw/gentra_luxury_v1
```


