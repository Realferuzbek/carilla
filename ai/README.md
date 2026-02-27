# AI Experiments

This folder contains AI experiment scaffolding and notes.

## Paper 1 (Identity Learning, Text-to-Image, LoRA)

Paper 1 protocol (source of truth):

- Task: text-to-image identity learning with token `<carilla_gentra>`
- Dataset: 80 total images
- Split: 70 train / 10 val
- Experiments:
  - `E0`: base Stable Diffusion v1.5 (no LoRA)
  - `E1`: LoRA-20
  - `E2`: LoRA-60
  - `E3`: LoRA-70
- Fixed evaluation inputs:
  - Prompts: `ai/experiments/prompts_identity_v1.txt` (10 prompts, fixed order)
  - Seeds: `ai/experiments/seeds_v1.txt` (`111`, `222`, `333`, `444`, fixed order)
- Fixed method settings (same for all experiments):
  - Runtime: Google Colab
  - Model family: Stable Diffusion v1.5
  - Generation mode: text-to-image only
  - Resolution: `512x512`
  - Inference steps: `30`
  - Images per prompt: `4` (from fixed seeds `111`, `222`, `333`, `444`)
  - LoRA rank: `16`
  - Learning rate: `1e-4`
  - Training steps: `2000`
  - Batch size: `1`
  - Gradient accumulation: `4`
- Evaluation:
  - Human ratings for identity and realism on a `1-10` scale
  - CLIPScore

Caption format for Paper 1:

- Token must stay `<carilla_gentra>`
- Fields: `[view]`, `[location]`, `[lighting]`
- Lighting tags: `day`, `sunset`, `cloudy`
- Location tags: `parking`, `street`

## Paper 1 Dataset Preparation (CLI)

Paper 1 dataset prep expects raw image filenames in this format:

- `{view}_{lighting}_{location}_{id}.{ext}`
- Example: `front_day_parking_001.jpg`
- Example: `rear45_sunset_street_002.png`

Paper 1 controlled tags:

- Views: `front`, `rear`, `left`, `right`, `front45`, `rear45`, `closeup`
- Lighting: `day`, `cloudy`, `sunset`
- Location: `parking`, `street`

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

## Legacy (Not Used for Paper 1)

The following legacy `sport_gentra` artifacts are kept for history and are not part of Paper 1 runs:

- `ai/scripts/prepare_sport_gentra_dataset.py`
- `ai/training/colab_sport_gentra_lora.md`
- `ai/datasets/processed/sport_gentra/`
