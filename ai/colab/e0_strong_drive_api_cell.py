"""Copy-paste Colab cell for reliable E0_strong generation + Drive API upload.

Usage:
- Copy the entire file content into a single Colab code cell and run it.
- This workflow generates images locally under /content first, then uploads via Drive API.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def install_required_packages() -> None:
    """Install minimal runtime dependencies for the Colab cell."""
    packages = [
        "diffusers",
        "transformers",
        "accelerate",
        "safetensors",
        "google-api-python-client",
    ]
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *packages])


install_required_packages()

import torch
from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline
import google.colab.auth
from google.colab import userdata
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===== Constants (edit these if needed) =====
MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
NUM_INFERENCE_STEPS = 30
GUIDANCE_SCALE = 7.0
WIDTH = 512
HEIGHT = 512
RUN_NAME = "E0_strong"
OUT_LOCAL = "/content/out/E0_strong"
REPO_ROOT = "/content/carilla"
PROMPTS_PATH = f"{REPO_ROOT}/ai/experiments/prompts_identity_v1.txt"
SEEDS_PATH = f"{REPO_ROOT}/ai/experiments/seeds_v1.txt"
CARILLA_ROOT_ID = "PASTE_DRIVE_PARENT_FOLDER_ID"


def _escape_drive_query_value(value: str) -> str:
    return value.replace("'", "\\'")


def _iter_drive_non_folder_items(service, folder_id: str) -> Iterable[dict]:
    page_token = None
    query = (
        f"'{folder_id}' in parents and trashed = false and "
        "mimeType != 'application/vnd.google-apps.folder'"
    )
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        for item in response.get("files", []):
            yield item
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def find_or_create_e0_strong_folder(service, parent_id: str) -> str:
    child_name = RUN_NAME
    escaped = _escape_drive_query_value(child_name)
    query = (
        f"'{parent_id}' in parents and trashed = false and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        f"name = '{escaped}'"
    )
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    matches = response.get("files", [])
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1:
        ids = ", ".join(item["id"] for item in matches)
        raise RuntimeError(
            f"Found multiple '{RUN_NAME}' folders under CARILLA_ROOT_ID. "
            f"Resolve duplicates manually. Folder IDs: {ids}"
        )

    created = (
        service.files()
        .create(
            body={
                "name": child_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return created["id"]


def clear_only_target_folder_files(service, folder_id: str) -> int:
    # WARNING: This deletes previous E0_strong files
    deleted = 0
    for item in list(_iter_drive_non_folder_items(service, folder_id)):
        service.files().delete(fileId=item["id"], supportsAllDrives=True).execute()
        deleted += 1
    return deleted


def upload_file_to_drive(service, folder_id: str, local_path: Path, mime_type: str) -> dict:
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
    body = {"name": local_path.name, "parents": [folder_id]}
    return (
        service.files()
        .create(
            body=body,
            media_body=media,
            fields="id, name",
            supportsAllDrives=True,
        )
        .execute()
    )


def main() -> None:
    assert HF_TOKEN, "Missing HF_TOKEN secret. Set it in Colab Secrets before running."
    assert (
        CARILLA_ROOT_ID != "PASTE_DRIVE_PARENT_FOLDER_ID"
    ), "Set CARILLA_ROOT_ID to your Drive parent folder ID."

    prompts_file = Path(PROMPTS_PATH)
    seeds_file = Path(SEEDS_PATH)
    assert prompts_file.exists(), f"Prompts file not found: {prompts_file}"
    assert seeds_file.exists(), f"Seeds file not found: {seeds_file}"

    prompts = [line.strip() for line in prompts_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    seeds = [int(line.strip()) for line in seeds_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(prompts) == 10, f"Expected exactly 10 prompts, got {len(prompts)}"
    assert seeds == [111, 222, 333, 444], f"Expected seeds [111, 222, 333, 444], got {seeds}"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    print("Authenticating Google account for Drive API...")
    google.colab.auth.authenticate_user()
    drive_service = build("drive", "v3")

    print(f"Loading pipeline: {MODEL_ID}")
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        token=HF_TOKEN,
        torch_dtype=dtype,
        use_safetensors=True,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=False)

    out_dir = Path(OUT_LOCAL)
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in out_dir.iterdir():
        if path.is_file():
            path.unlink()

    print(f"Generating images into local folder: {out_dir}")
    generated_files: list[str] = []
    for pi, prompt in enumerate(prompts, start=1):
        for seed in seeds:
            generator = torch.Generator(device=device).manual_seed(seed)
            image = pipe(
                prompt=prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                width=WIDTH,
                height=HEIGHT,
                generator=generator,
            ).images[0]
            filename = f"E0strong_p{pi:02d}_s{seed}.png"
            image.save(out_dir / filename)
            generated_files.append(filename)

    assert len(generated_files) == 40, f"Expected 40 generated images, got {len(generated_files)}"

    meta = {
        "run_name": RUN_NAME,
        "model_id": MODEL_ID,
        "scheduler": pipe.scheduler.__class__.__name__,
        "num_inference_steps": NUM_INFERENCE_STEPS,
        "guidance_scale": GUIDANCE_SCALE,
        "width": WIDTH,
        "height": HEIGHT,
        "seeds": seeds,
        "prompts": prompts,
        "filenames": sorted(generated_files),
        "generated_count": len(generated_files),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    target_folder_id = find_or_create_e0_strong_folder(drive_service, CARILLA_ROOT_ID)
    print(f"Using Drive folder ID: {target_folder_id}")

    deleted_count = clear_only_target_folder_files(drive_service, target_folder_id)
    print(f"Cleared {deleted_count} previous file(s) from Drive folder '{RUN_NAME}'.")

    upload_file_to_drive(drive_service, target_folder_id, meta_path, "application/json")
    for filename in sorted(generated_files):
        upload_file_to_drive(drive_service, target_folder_id, out_dir / filename, "image/png")

    uploaded_items = list(_iter_drive_non_folder_items(drive_service, target_folder_id))
    uploaded_names = sorted(item["name"] for item in uploaded_items)
    png_names = [name for name in uploaded_names if name.lower().endswith(".png")]
    assert len(png_names) == 40, f"Expected 40 PNG files in Drive, found {len(png_names)}"
    assert "meta.json" in uploaded_names, "meta.json is missing in Drive output folder."
    assert len(uploaded_items) == 41, f"Expected 41 files in Drive folder, found {len(uploaded_items)}"

    link = f"https://drive.google.com/drive/folders/{target_folder_id}"
    print("Upload complete.")
    print(f"Drive folder link: {link}")
    print(f"Final non-folder item count in '{RUN_NAME}': {len(uploaded_items)}")
    print("Sample output files:", ", ".join(png_names[:3]), "...")


HF_TOKEN = userdata.get("HF_TOKEN")
main()
