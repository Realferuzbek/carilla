# E0_strong Colab Drive API Run

This guide runs E0_strong in Google Colab with a reliable flow:

1. Generate locally under `/content/out/E0_strong`
2. Upload outputs to Google Drive using the Drive API

This avoids relying on mounted Drive writes for final persistence.

## Requirements

- Colab GPU runtime recommended.
- Repo available in Colab at `REPO_ROOT` (default: `/content/carilla`).
- Colab Secret named `HF_TOKEN` (Hugging Face access token).
- Google Drive parent folder ID where `E0_strong` will be created/found.

## Files used

- Prompts (read-only): `ai/experiments/prompts_identity_v1.txt`
- Seeds: `ai/experiments/seeds_v1.txt`
- Colab cell source: `ai/colab/e0_strong_drive_api_cell.py`

## Run steps

1. Open Colab and clone/mount your repo so files exist at `REPO_ROOT`.
2. Open `ai/colab/e0_strong_drive_api_cell.py`.
3. Copy the full file content into a single Colab code cell.
4. In constants, set:
   - `CARILLA_ROOT_ID = "<your_parent_folder_id>"`
   - `REPO_ROOT` only if your repo path differs.
5. Ensure Colab Secret `HF_TOKEN` exists.
6. Run the cell once.

## Safety behavior

- The script creates/finds exactly one Drive child folder named `E0_strong` under `CARILLA_ROOT_ID`.
- If multiple `E0_strong` folders are found under the same parent, it fails safely.
- Before upload it clears only non-folder files inside that selected `E0_strong` folder.
- It does not recurse into subfolders and does not delete outside that folder.
- The cell includes the warning comment:
  - `WARNING: This deletes previous E0_strong files`

## Expected outputs

- Local output folder: `/content/out/E0_strong`
- Drive output folder: `<CARILLA_ROOT_ID>/E0_strong`
- Final file count in Drive `E0_strong`: `41`
  - `40` PNG images
  - `1` `meta.json`

## Naming convention

- Image filename format:
  - `E0strong_p{pi:02d}_s{seed}.png`
- Example:
  - `E0strong_p01_s111.png`
  - `E0strong_p10_s444.png`

## Sanity checks after run

1. Drive folder `E0_strong` has exactly `41` non-folder items.
2. All image names follow `E0strong_p{pi:02d}_s{seed}.png`.
3. `meta.json` exists and lists config, prompts, seeds, and filenames.
