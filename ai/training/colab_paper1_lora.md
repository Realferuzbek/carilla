# Paper 1 LoRA Colab Runbook (Google Colab, Text-to-Image Only)

This is a documentation-only runbook for executing Paper 1 in Google Colab.

Paper 1 scope is strictly:

- Text-to-image only
- Stable Diffusion 1.5 base model family
- Diffusers + Accelerate workflow in Colab
- Fixed prompts, seeds, inference settings, and training hyperparameters
- Experiments `E0`, `E1`, `E2`, `E3`

This runbook does not include notebook code yet.

## Scope and Goal

Goal: run a reproducible identity-learning LoRA study for `<carilla_gentra>` and compare:

- `E0`: Base SD 1.5 (no LoRA)
- `E1`: LoRA trained on 20 training images
- `E2`: LoRA trained on 60 training images
- `E3`: LoRA trained on 70 training images

Each experiment is evaluated with the same:

- 10 prompts
- 4 seeds
- inference settings (`512x512`, `steps=30`, fixed scheduler, fixed CFG)

Paper 1 comparison target:

- `10 prompts x 4 seeds = 40` outputs per experiment
- `4 experiments x 40 = 160` total evaluation images

## Do not start until dataset_prep.py succeeded

Do not start the Colab run until local dataset preparation and validation completed successfully.

Required local commands (examples):

```bash
python ai/scripts/dataset_prep.py
python ai/scripts/validate_dataset.py --raw_dir ai/datasets/raw/gentra_luxury_v1
```

Confirm these outputs exist locally before uploading to Google Drive:

- `ai/datasets/processed/gentra_luxury_v1/images_1024/`
- `ai/datasets/processed/gentra_luxury_v1/train_512/`
- `ai/datasets/processed/gentra_luxury_v1/val_512/`
- `ai/datasets/processed/gentra_luxury_v1/captions/`
- `ai/datasets/processed/gentra_luxury_v1/splits/train.txt`
- `ai/datasets/processed/gentra_luxury_v1/splits/val.txt`
- `ai/datasets/processed/gentra_luxury_v1/manifest_generated.csv`

This runbook assumes those artifacts are valid, internally consistent, and ready for training/evaluation.

## Paper 1 Experiment Definitions (E0-E3)

### E0 (Baseline, No LoRA)

- Base SD 1.5 text-to-image inference only
- No LoRA weights loaded
- Used as baseline for identity comparison

### E1 (LoRA-20)

- Train a LoRA using a deterministic 20-image subset of the 70-image train split
- Subset source: `splits/train.txt`
- Subset rule: first 20 lines (deterministic prefix)

### E2 (LoRA-60)

- Train a LoRA using a deterministic 60-image subset of the 70-image train split
- Subset source: `splits/train.txt`
- Subset rule: first 60 lines (deterministic prefix)

### E3 (LoRA-70)

- Train a LoRA using the full 70-image train split
- Source: all lines in `splits/train.txt`

Protocol invariants:

- `E1-E3` use identical training hyperparameters; only train set size changes
- `E0-E3` use identical prompts, seeds, and inference settings
- `E0-E3` are text-to-image only (no img2img)

## Fixed Evaluation Inputs (Prompts, Seeds, Inference Settings)

### Fixed Prompt and Seed Inputs

- Prompts file: `ai/experiments/prompts_identity_v1.txt` (10 prompts)
- Seeds file: `ai/experiments/seeds_v1.txt` (`111`, `222`, `333`, `444`)
- Prompt order: fixed, do not reorder
- Seed order: fixed, do not reorder
- Images per prompt-seed pair: `1`
- Negative prompt: empty string (fixed)

Evaluation volume:

- Per experiment: `10 x 4 = 40` images
- All experiments (`E0-E3`): `160` images

### Fixed Inference Settings (Do Not Change Within Paper 1)

- Base model family: `Stable Diffusion 1.5`
- Generation mode: text-to-image only
- Resolution: `512x512`
- Inference steps: `30`
- Guidance / CFG: `7.0`
- Scheduler / sampler: `DPMSolverMultistepScheduler`

Keep these settings identical for `E0`, `E1`, `E2`, and `E3`.

## Fixed Training Settings (E1-E3)

Use the same training settings for `E1`, `E2`, and `E3`:

- Training stack: `diffusers + accelerate` (Google Colab)
- Task: text-to-image LoRA training only
- LoRA rank: `16`
- Learning rate: `1e-4`
- Max training steps: `2000`
- Batch size: `1`
- Gradient accumulation: `4`
- Effective batch (informational): `4`

Paper 1 only varies:

- train subset size (`20`, `60`, `70`)

If you change any other training or inference parameter, it becomes a different study variant and should not be reported as Paper 1.

## Recommended Google Drive Layout (What Goes Where)

Recommended root:

- `MyDrive/carilla/paper1_lora/`

Create and use this structure in Google Drive:

```text
MyDrive/carilla/paper1_lora/
├── inputs/
│   ├── dataset_processed/
│   │   └── gentra_luxury_v1/
│   │       ├── images_1024/
│   │       ├── train_512/
│   │       ├── val_512/
│   │       ├── captions/
│   │       ├── splits/
│   │       │   ├── train.txt
│   │       │   └── val.txt
│   │       └── manifest_generated.csv
│   ├── prompts/
│   │   ├── prompts_identity_v1.txt
│   │   └── seeds_v1.txt
│   └── config/
├── models/
│   └── base/
├── runs/
│   ├── E1_lora20/
│   ├── E2_lora60/
│   └── E3_lora70/
├── eval/
│   ├── E0_base_sd/
│   ├── E1_lora20/
│   ├── E2_lora60/
│   └── E3_lora70/
└── logs/
```

### Exact “what goes where” (local repo -> Drive)

- `ai/datasets/processed/gentra_luxury_v1/images_1024/` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/images_1024/`
- `ai/datasets/processed/gentra_luxury_v1/train_512/` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/train_512/`
- `ai/datasets/processed/gentra_luxury_v1/val_512/` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/val_512/`
- `ai/datasets/processed/gentra_luxury_v1/captions/` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/captions/`
- `ai/datasets/processed/gentra_luxury_v1/splits/train.txt` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/splits/train.txt`
- `ai/datasets/processed/gentra_luxury_v1/splits/val.txt` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/splits/val.txt`
- `ai/datasets/processed/gentra_luxury_v1/manifest_generated.csv` -> `MyDrive/carilla/paper1_lora/inputs/dataset_processed/gentra_luxury_v1/manifest_generated.csv`
- `ai/experiments/prompts_identity_v1.txt` -> `MyDrive/carilla/paper1_lora/inputs/prompts/prompts_identity_v1.txt`
- `ai/experiments/seeds_v1.txt` -> `MyDrive/carilla/paper1_lora/inputs/prompts/seeds_v1.txt`
- Base SD 1.5 model (downloaded or pre-staged) -> `MyDrive/carilla/paper1_lora/models/base/`

Drive discipline:

- Treat `inputs/` as read-only during experiments
- Write all experiment outputs only under `runs/`, `eval/`, and `logs/`

## Colab Runtime Setup

This section describes what to do in Colab. Do not write notebook code from this document yet.

1. Open a new Google Colab notebook for Paper 1.
2. Set runtime type to GPU.
3. Acceptable GPUs include T4 or A100 (runtime availability varies).
4. Mount Google Drive.
5. Confirm the mounted path matches your intended root (`MyDrive/carilla/paper1_lora/`).
6. Confirm available disk space in Drive and temporary runtime storage.
7. Install the required Python packages for a `diffusers + accelerate` LoRA workflow.
8. Define notebook constants for:
   - project root in Drive
   - dataset paths
   - prompts/seeds files
   - run output folders
   - evaluation output folders
   - Paper 1 fixed hyperparameters and inference settings
9. Keep all notebook paths pointed to the Drive layout above.

## Notebook Cell Plan (Step-by-Step, No Code Yet)

Use this exact order as the notebook execution plan.

1. Install dependencies (`torch`, `diffusers`, `transformers`, `accelerate`, `safetensors`, and related utilities).
2. Mount Google Drive.
3. Define all path constants and Paper 1 fixed constants.
4. Load prompts from `inputs/prompts/prompts_identity_v1.txt`.
5. Load seeds from `inputs/prompts/seeds_v1.txt`.
6. Validate dataset paths and expected counts in Drive.
7. Read `inputs/dataset_processed/gentra_luxury_v1/splits/train.txt` and `val.txt`.
8. Build deterministic train subsets for `E1` and `E2` from `splits/train.txt`:
   - `E1`: first 20 lines
   - `E2`: first 60 lines
   - `E3`: all 70 lines
9. Load the base SD 1.5 text-to-image pipeline.
10. Set the fixed inference scheduler to `DPMSolverMultistepScheduler`.
11. Run `E0` baseline inference (no LoRA) for all 10 prompts x 4 seeds.
12. Configure fixed LoRA training hyperparameters (`lr=1e-4`, `steps=2000`, `batch=1`, `grad_accum=4`, `rank=16`).
13. Train `E1` LoRA using the 20-image subset and save checkpoints/final LoRA under `runs/E1_lora20/`.
14. Run `E1` inference using the trained LoRA for all 10 prompts x 4 seeds and save outputs under `eval/E1_lora20/`.
15. Train `E2` LoRA using the 60-image subset and save checkpoints/final LoRA under `runs/E2_lora60/`.
16. Run `E2` inference using the trained LoRA for all 10 prompts x 4 seeds and save outputs under `eval/E2_lora60/`.
17. Train `E3` LoRA using the full 70-image train split and save checkpoints/final LoRA under `runs/E3_lora70/`.
18. Run `E3` inference using the trained LoRA for all 10 prompts x 4 seeds and save outputs under `eval/E3_lora70/`.
19. Write/update a summary log in `logs/` with all fixed settings and output locations.
20. Verify final output counts per experiment.

Paper 1 notebook guardrails:

- Do not include img2img cells
- Do not vary scheduler, steps, CFG, resolution, prompts, or seeds across `E0-E3`
- Do not mix text-to-image and img2img outputs in the same eval folders

## Running E0 (Base SD, No LoRA)

`E0` is the baseline and must be run before comparing LoRA outputs.

Execution rules:

- Use the same base SD 1.5 model family used for LoRA training
- Do not load any LoRA weights
- Use the fixed prompts and seeds files
- Use the fixed inference settings:
  - `512x512`
  - `steps=30`
  - `CFG=7.0`
  - `DPMSolverMultistepScheduler`

Output target:

- `MyDrive/carilla/paper1_lora/eval/E0_base_sd/`

Expected output count:

- `40` images

## Running E1/E2/E3 (LoRA Training + Inference)

Run the three LoRA experiments sequentially and keep everything else fixed.

### Training (E1, E2, E3)

For each experiment:

- Start from the same SD 1.5 base model
- Apply the same LoRA configuration and hyperparameters
- Only change the train subset size (`20`, `60`, `70`)
- Save checkpoints and final LoRA weights into that experiment's `runs/` folder

Training output folders:

- `MyDrive/carilla/paper1_lora/runs/E1_lora20/`
- `MyDrive/carilla/paper1_lora/runs/E2_lora60/`
- `MyDrive/carilla/paper1_lora/runs/E3_lora70/`

### Inference (E1, E2, E3)

After each LoRA training run:

- Load the experiment's final LoRA weights
- Use the same prompts and seeds as `E0`
- Use the same inference settings as `E0`
- Save exactly `40` evaluation images for that experiment

Evaluation output folders:

- `MyDrive/carilla/paper1_lora/eval/E1_lora20/`
- `MyDrive/carilla/paper1_lora/eval/E2_lora60/`
- `MyDrive/carilla/paper1_lora/eval/E3_lora70/`

## Output Naming and Result Organization

Use a consistent naming convention so prompt/seed pairs are directly comparable across `E0-E3`.

Recommended file naming pattern:

- `prompt01_seed111.png`
- `prompt01_seed222.png`
- `prompt10_seed444.png`

If you use a different pattern, keep it consistent across all experiments and encode both prompt index and seed.

Recommended per-experiment metadata sidecar (CSV or Markdown in each eval folder):

- experiment ID (`E0`, `E1`, `E2`, `E3`)
- prompts file name
- seeds file name
- base model identifier
- LoRA weights path (empty / N/A for `E0`)
- scheduler (`DPMSolverMultistepScheduler`)
- CFG (`7.0`)
- steps (`30`)
- resolution (`512x512`)
- generation timestamp

Comparison rule:

- Compare outputs only across matched prompt+seed pairs (e.g., `prompt03_seed222` in `E0` vs `E1` vs `E2` vs `E3`)

## Reproducibility Checklist

Before finalizing results, confirm:

- Same prompts file used for all experiments: `prompts_identity_v1.txt`
- Same seeds file used for all experiments: `seeds_v1.txt`
- Same base model family (SD 1.5) used for all experiments
- Same scheduler used for all experiments
- Same inference resolution/steps/CFG used for all experiments
- `E1-E3` training hyperparameters are identical except subset size
- `E1/E2` subsets came from deterministic prefix of `splits/train.txt`
- No img2img outputs were generated or mixed into Paper 1 results

## Common Failure Modes / Troubleshooting

### Drive mount path mismatch

- Symptom: notebook cannot find dataset or prompts
- Fix: re-check mounted Drive path and all notebook path constants

### Missing dataset files or wrong folder placement

- Symptom: subset loading or training input setup fails
- Fix: compare your Drive tree against the exact layout in this runbook, especially `inputs/dataset_processed/gentra_luxury_v1/`

### Count mismatch vs expected `70/10`

- Symptom: train/val lists or manifest counts do not match expectations
- Fix: stop and re-run local validation:
  - `python ai/scripts/validate_dataset.py --raw_dir ai/datasets/raw/gentra_luxury_v1`

### OOM / VRAM issues in Colab

- Symptom: training/inference crashes with CUDA out-of-memory
- Fix: restart runtime and reduce memory pressure in implementation (for example, enable memory-efficient options in the notebook code)
- Do not change Paper 1 evaluation settings (`512x512`, `steps=30`, `CFG=7.0`, scheduler) without documenting that the run is no longer the same Paper 1 protocol

### Interrupted Colab session

- Symptom: runtime disconnects mid-training
- Fix: restart from the last saved checkpoint in the experiment's `runs/` folder and keep the same fixed settings

### Accidentally changed prompts/seeds/settings mid-run

- Symptom: outputs are not comparable across experiments
- Fix: discard affected outputs and rerun the experiment from a clean state with the fixed protocol

### Img2img used by mistake

- Symptom: mixed generation modes in outputs
- Fix: discard those outputs; Paper 1 is text-to-image only

## What Not to Change During Paper 1

Do not change any of the following while running Paper 1:

- Prompts file (`ai/experiments/prompts_identity_v1.txt`)
- Seeds file (`ai/experiments/seeds_v1.txt`)
- Base model family (`SD 1.5`)
- Scheduler / sampler (`DPMSolverMultistepScheduler`)
- Guidance / CFG (`7.0`)
- Inference steps (`30`)
- Inference resolution (`512x512`)
- Training hyperparameters (`lr=1e-4`, `steps=2000`, `batch=1`, `grad_accum=4`, `rank=16`)
- Task scope (text-to-image only; no img2img)
- Dataset split and subset rule (deterministic prefix of `splits/train.txt`)

Changing any of the above means you are no longer running the same Paper 1 protocol.

## Completion Checklist

Use this checklist to close out a Paper 1 run:

- `dataset_prep.py` completed successfully
- `validate_dataset.py` passed successfully
- Google Drive layout matches this runbook
- `E0` baseline completed with `40` images in `eval/E0_base_sd/`
- `E1` completed with trained LoRA artifacts in `runs/E1_lora20/` and `40` eval images
- `E2` completed with trained LoRA artifacts in `runs/E2_lora60/` and `40` eval images
- `E3` completed with trained LoRA artifacts in `runs/E3_lora70/` and `40` eval images
- All experiments used identical prompts, seeds, scheduler, CFG, steps, and resolution
- Logs/metadata were saved under `MyDrive/carilla/paper1_lora/logs/` (and/or per-eval folders)
- No img2img outputs are included in Paper 1 results
