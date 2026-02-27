# Paper 1 LoRA Colab Runbook (Google Colab, Text-to-Image Only)

This runbook documents the fixed Paper 1 protocol for identity learning with `<carilla_gentra>`.

## Paper 1 Protocol (Fixed)

- Dataset: `80` total images
- Split: `70` train / `10` val
- Experiments:
  - `E0`: Base SD v1.5 (no LoRA)
  - `E1`: LoRA-20
  - `E2`: LoRA-60
  - `E3`: LoRA-70
- Task mode: text-to-image only
- Runtime: Google Colab
- Base model family: Stable Diffusion v1.5
- Resolution: `512x512`
- Inference steps: `30`
- LoRA rank: `16`
- Learning rate: `1e-4`
- Training steps: `2000`
- Batch size: `1`
- Gradient accumulation: `4`

Protocol rule:

- Keep the same settings for all experiments. The only experiment difference is train subset size (`20`, `60`, `70`) for `E1`, `E2`, `E3`.

## Source-of-Truth Inputs (Do Not Change)

- Prompts file: `ai/experiments/prompts_identity_v1.txt`
- Seeds file: `ai/experiments/seeds_v1.txt`
- Fixed seeds: `111`, `222`, `333`, `444`
- Prompt count: `10`
- Images per prompt: `4` (one image for each fixed seed)

Output counts:

- Per experiment: `10 prompts x 4 seeds = 40` images
- All experiments (`E0-E3`): `160` images

## Pre-Run Requirement

Run local preparation and validation before Colab:

```bash
python ai/scripts/dataset_prep.py
python ai/scripts/validate_dataset.py --raw_dir ai/datasets/raw/gentra_luxury_v1
```

Confirm these processed artifacts exist before upload:

- `ai/datasets/processed/gentra_luxury_v1/images_1024/`
- `ai/datasets/processed/gentra_luxury_v1/train_512/`
- `ai/datasets/processed/gentra_luxury_v1/val_512/`
- `ai/datasets/processed/gentra_luxury_v1/captions/`
- `ai/datasets/processed/gentra_luxury_v1/splits/train.txt`
- `ai/datasets/processed/gentra_luxury_v1/splits/val.txt`
- `ai/datasets/processed/gentra_luxury_v1/manifest_generated.csv`

## Experiment Definitions (E0-E3)

- `E0`: Run base SD v1.5 inference only (no LoRA weights).
- `E1`: Train LoRA on deterministic first `20` lines of `splits/train.txt`, then run evaluation.
- `E2`: Train LoRA on deterministic first `60` lines of `splits/train.txt`, then run evaluation.
- `E3`: Train LoRA on full `70` lines of `splits/train.txt`, then run evaluation.

## Colab Execution Order (No New Features)

1. Install required packages for diffusers + accelerate LoRA workflow.
2. Mount Google Drive and set project paths.
3. Load fixed prompts from `ai/experiments/prompts_identity_v1.txt`.
4. Load fixed seeds from `ai/experiments/seeds_v1.txt`.
5. Validate dataset files in Drive.
6. Run `E0` inference for all prompt-seed pairs.
7. Train `E1` with fixed settings, then run `E1` inference.
8. Train `E2` with fixed settings, then run `E2` inference.
9. Train `E3` with fixed settings, then run `E3` inference.
10. Verify output counts and log final settings.

## Reproducibility Checklist

- Same prompt file used for all `E0-E3` runs.
- Same seed file used for all `E0-E3` runs.
- Same base model family (`SD v1.5`) used for all runs.
- Same text-to-image settings used for all runs (`512x512`, `30` steps).
- Same LoRA training settings for `E1-E3` (`rank=16`, `lr=1e-4`, `steps=2000`, `batch=1`, `grad_accum=4`).
- Only train subset size changes across `E1`, `E2`, `E3`.
- No img2img outputs are included in Paper 1 results.

## What Not To Change During Paper 1

- Identity token: `<carilla_gentra>`
- Prompt source file: `ai/experiments/prompts_identity_v1.txt`
- Seed source file: `ai/experiments/seeds_v1.txt`
- Fixed seeds: `111`, `222`, `333`, `444`
- Model family: `Stable Diffusion v1.5`
- Generation mode: text-to-image only
- Resolution: `512x512`
- Inference steps: `30`
- LoRA rank: `16`
- Learning rate: `1e-4`
- Training steps: `2000`
- Batch size: `1`
- Gradient accumulation: `4`

Changing any of the above means the run is not the same Paper 1 protocol.
