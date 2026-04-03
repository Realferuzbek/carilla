# ==============================================================================
# CARILLA — Paper 1 | LoRA Training + Generation + DINO-I Scoring
# Experiments: E1 (20 imgs), E2 (40 imgs), E3 (60 imgs), E4 (70 imgs)
#
# HOW TO USE THIS FILE:
#   Copy each CELL block into a separate cell in Google Colab.
#   Run cells TOP TO BOTTOM, ONE AT A TIME.
#   Never skip a cell. Never run a cell twice unless told to.
# ==============================================================================


# ════════════════════════════════════════════════════════════════
# CELL 1 — Install all packages (run ONCE at session start)
# ════════════════════════════════════════════════════════════════
"""
!pip install -q diffusers==0.27.2 transformers accelerate peft \
               torch torchvision xformers bitsandbytes \
               Pillow numpy pandas google-api-python-client
"""


# ════════════════════════════════════════════════════════════════
# CELL 2 — Auth + Drive + Config (run ONCE at session start)
# ════════════════════════════════════════════════════════════════
"""
from google.colab import auth, userdata
auth.authenticate_user()

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os, json, shutil, torch
from pathlib import Path

drive = build("drive", "v3")

# ── Secrets (set these in Colab Secrets panel, key icon on left sidebar) ──
HF_TOKEN = userdata.get("HF_TOKEN")
assert HF_TOKEN, "HF_TOKEN missing! Add it in Colab Secrets."

# ── Your Drive folder ID (the root Carilla folder) ──
CARILLA_ROOT_ID = "1JfnClYuOLaUhXsnL_opl8o8D3u-YyUj3"

# ── Fixed Paper 1 settings ──
MODEL_ID    = "stable-diffusion-v1-5/stable-diffusion-v1-5"
RESOLUTION  = 512
INFER_STEPS = 30
CFG         = 7.0
LORA_RANK   = 16
LR          = 1e-4
SEEDS       = [111, 222, 333, 444]

# ── Experiment definitions ──
EXPERIMENTS = {
    "E1": {"n_train": 20, "steps": 600,  "ckpt_every": 200},
    "E2": {"n_train": 40, "steps": 1200, "ckpt_every": 400},
    "E3": {"n_train": 60, "steps": 1800, "ckpt_every": 600},
    "E4": {"n_train": 70, "steps": 2000, "ckpt_every": 500},
}

print("✅ Config loaded.")
print("Experiments:", list(EXPERIMENTS.keys()))
"""


# ════════════════════════════════════════════════════════════════
# CELL 3 — Helper functions (run ONCE)
# ════════════════════════════════════════════════════════════════
"""
def get_or_create_folder(parent_id: str, name: str) -> str:
    \"\"\"Get a Drive folder ID by name under parent, or create it.\"\"\"
    q = (f"'{parent_id}' in parents and "
         f"mimeType='application/vnd.google-apps.folder' and "
         f"name='{name}' and trashed=false")
    res = drive.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        print(f"  Found existing folder: {name} ({files[0]['id']})")
        return files[0]["id"]
    meta = {"name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]}
    folder = drive.files().create(body=meta, fields="id").execute()
    print(f"  Created new folder: {name} ({folder['id']})")
    return folder["id"]


def upload_folder_to_drive(local_dir: str, drive_folder_id: str):
    \"\"\"Upload every file in local_dir to the given Drive folder.\"\"\"
    files = sorted(os.listdir(local_dir))
    print(f"  Uploading {len(files)} files to Drive...")
    for fname in files:
        local_path = os.path.join(local_dir, fname)
        if not os.path.isfile(local_path):
            continue
        mime = "application/json" if fname.endswith(".json") else \
               "text/csv"         if fname.endswith(".csv")  else "image/png"
        media = MediaFileUpload(local_path, mimetype=mime, resumable=True)
        body  = {"name": fname, "parents": [drive_folder_id]}
        drive.files().create(body=body, media_body=media, fields="id").execute()
        print(f"    ✅ {fname}")
    print("  Upload complete.")


def load_prompts(path: str) -> list:
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    assert len(lines) == 10, f"Expected 10 prompts, got {len(lines)}"
    print(f"  Loaded {len(lines)} prompts from {path}")
    return lines


print("✅ Helper functions ready.")
"""


# ════════════════════════════════════════════════════════════════
# CELL 4 — Clone your Carilla repo from GitHub (run ONCE)
# NOTE: Replace YOUR_GITHUB_USERNAME with your actual GitHub username
# ════════════════════════════════════════════════════════════════
"""
import subprocess

GITHUB_USERNAME = "YOUR_GITHUB_USERNAME"   # ← CHANGE THIS
REPO_NAME       = "carilla"                # ← your repo name on GitHub

result = subprocess.run(
    ["git", "clone", f"https://github.com/{GITHUB_USERNAME}/{REPO_NAME}.git",
     "/content/carilla"],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)

os.chdir("/content/carilla")
print("Working directory:", os.getcwd())
print("Repo contents:", os.listdir("."))
"""


# ════════════════════════════════════════════════════════════════
# CELL 5 — Download dataset from Drive to Colab local storage
# This downloads your processed dataset (after you ran dataset_prep.py)
# and put the processed folder into Drive manually once.
# ════════════════════════════════════════════════════════════════
"""
# ── Find your dataset folder in Drive ──
DATASET_DRIVE_FOLDER_NAME = "sonata_luxury_v1_processed"  # name you'll give it in Drive
DATASET_LOCAL_PATH = "/content/dataset"

def download_folder_from_drive(folder_id: str, local_path: str):
    \"\"\"Download all files from a Drive folder to local path.\"\"\"
    os.makedirs(local_path, exist_ok=True)
    page_token = None
    while True:
        res = drive.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,mimeType)",
            pageToken=page_token
        ).execute()
        for f in res.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                sub_local = os.path.join(local_path, f["name"])
                download_folder_from_drive(f["id"], sub_local)
            else:
                dest = os.path.join(local_path, f["name"])
                content = drive.files().get_media(fileId=f["id"]).execute()
                with open(dest, "wb") as fh:
                    fh.write(content)
                print(f"  ⬇ {f['name']}")
        page_token = res.get("nextPageToken")
        if not page_token:
            break

# Get the dataset folder ID (it should be inside your CARILLA_ROOT_ID)
dataset_folder_id = get_or_create_folder(CARILLA_ROOT_ID, DATASET_DRIVE_FOLDER_NAME)
download_folder_from_drive(dataset_folder_id, DATASET_LOCAL_PATH)

# Load the train split file
train_split = [l.strip() for l in
               open(f"{DATASET_LOCAL_PATH}/splits/train.txt", encoding="utf-8")
               if l.strip()]
print(f"\\nTotal train images available: {len(train_split)}")
print("First 3:", train_split[:3])
"""


# ════════════════════════════════════════════════════════════════
# CELL 6 — Run ONE experiment (change EXP_NAME to run each one)
#
# Run this cell for E1 first.
# When it finishes → change EXP_NAME = "E2" → run again.
# Repeat for E3, E4.
# ════════════════════════════════════════════════════════════════
"""
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from diffusers.loaders import AttnProcsLayers
from diffusers.models.attention_processor import LoRAAttnProcessor
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms as T
from PIL import Image
import torch.nn.functional as F
from accelerate import Accelerator
from transformers import CLIPTokenizer, CLIPTextModel

# ── CHANGE THIS to run each experiment: "E1", "E2", "E3", "E4" ──
EXP_NAME = "E1"

exp     = EXPERIMENTS[EXP_NAME]
N_TRAIN = exp["n_train"]
STEPS   = exp["steps"]
CKPT_EVERY = exp["ckpt_every"]

print(f"\\n{'='*60}")
print(f"  Running: {EXP_NAME}")
print(f"  Training images: {N_TRAIN}")
print(f"  Training steps:  {STEPS}")
print(f"  Checkpoint every: {CKPT_EVERY} steps")
print(f"{'='*60}\\n")

# ── Local paths for this experiment ──
TRAIN_IMG_DIR = f"{DATASET_LOCAL_PATH}/train_512"
VAL_IMG_DIR   = f"{DATASET_LOCAL_PATH}/val_512"
CAPTION_DIR   = f"{DATASET_LOCAL_PATH}/captions"
OUT_LOCAL     = f"/content/out/{EXP_NAME}"
CKPT_DIR      = f"/content/checkpoints/{EXP_NAME}"
os.makedirs(OUT_LOCAL, exist_ok=True)
os.makedirs(CKPT_DIR,  exist_ok=True)

# ── Build subset of N_TRAIN images from train split ──
subset_files = train_split[:N_TRAIN]
print(f"Using {len(subset_files)} training images.")

# ── Dataset class ──
class CarDataset(Dataset):
    def __init__(self, img_dir, caption_dir, file_list, tokenizer, size=512):
        self.img_dir     = img_dir
        self.caption_dir = caption_dir
        self.files       = file_list
        self.tokenizer   = tokenizer
        self.size        = size
        self.transform   = T.Compose([
            T.Resize((size, size)),
            T.ToTensor(),
            T.Normalize([0.5], [0.5]),
        ])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        fname    = self.files[idx]
        img_path = os.path.join(self.img_dir, fname)
        cap_path = os.path.join(self.caption_dir,
                                fname.rsplit(".", 1)[0] + ".txt")

        image   = Image.open(img_path).convert("RGB")
        image   = self.transform(image)
        caption = open(cap_path, encoding="utf-8").read().strip()

        tokens = self.tokenizer(
            caption,
            padding="max_length",
            truncation=True,
            max_length=self.tokenizer.model_max_length,
            return_tensors="pt",
        )
        return {"pixel_values": image, "input_ids": tokens.input_ids.squeeze(0)}

# ── Load model components ──
from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler

tokenizer  = CLIPTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer",
                                           token=HF_TOKEN)
text_enc   = CLIPTextModel.from_pretrained(MODEL_ID, subfolder="text_encoder",
                                           token=HF_TOKEN)
vae        = AutoencoderKL.from_pretrained(MODEL_ID, subfolder="vae",
                                           token=HF_TOKEN)
unet       = UNet2DConditionModel.from_pretrained(MODEL_ID, subfolder="unet",
                                                  token=HF_TOKEN)
noise_sched = DDPMScheduler.from_pretrained(MODEL_ID, subfolder="scheduler",
                                            token=HF_TOKEN)

# ── Freeze VAE and text encoder; only train UNet via LoRA ──
vae.requires_grad_(False)
text_enc.requires_grad_(False)

# ── Apply LoRA to UNet ──
lora_config = LoraConfig(
    r=LORA_RANK,
    lora_alpha=LORA_RANK,
    target_modules=["to_q", "to_v", "to_k", "to_out.0"],
    lora_dropout=0.0,
    bias="none",
)
unet = get_peft_model(unet, lora_config)
unet.print_trainable_parameters()

# ── Dataloader ──
dataset    = CarDataset(TRAIN_IMG_DIR, CAPTION_DIR, subset_files, tokenizer)
dataloader = DataLoader(dataset, batch_size=1, shuffle=True)

# ── Optimizer ──
optimizer  = torch.optim.AdamW(unet.parameters(), lr=LR)

# ── Move to GPU ──
device = "cuda"
unet.to(device)
text_enc.to(device)
vae.to(device)

# ── Training loop ──
unet.train()
global_step = 0
losses = []

print(f"Starting training for {STEPS} steps...")

while global_step < STEPS:
    for batch in dataloader:
        if global_step >= STEPS:
            break

        pixel_values = batch["pixel_values"].to(device, dtype=torch.float16)
        input_ids    = batch["input_ids"].to(device)

        # Encode image to latent space
        with torch.no_grad():
            latents = vae.encode(pixel_values).latent_dist.sample() * 0.18215

        # Sample noise and timestep
        noise     = torch.randn_like(latents)
        timesteps = torch.randint(0, noise_sched.config.num_train_timesteps,
                                  (latents.shape[0],), device=device).long()
        noisy_lat = noise_sched.add_noise(latents, noise, timesteps)

        # Get text embeddings
        with torch.no_grad():
            enc_hidden = text_enc(input_ids)[0]

        # Predict noise
        pred = unet(noisy_lat, timesteps, enc_hidden).sample
        loss = F.mse_loss(pred.float(), noise.float())

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        losses.append(loss.item())
        global_step += 1

        if global_step % 50 == 0:
            avg = sum(losses[-50:]) / min(len(losses), 50)
            print(f"  step {global_step}/{STEPS} | loss {avg:.4f}")

        # ── Save checkpoint ──
        if global_step % CKPT_EVERY == 0 or global_step == STEPS:
            ckpt_path = os.path.join(CKPT_DIR, f"step_{global_step:04d}")
            unet.save_pretrained(ckpt_path)
            print(f"  💾 Checkpoint saved: {ckpt_path}")

print(f"\\n✅ Training complete: {EXP_NAME}")
"""


# ════════════════════════════════════════════════════════════════
# CELL 7 — Generate 40 images with trained LoRA
# Run this immediately after CELL 6 finishes for each experiment.
# ════════════════════════════════════════════════════════════════
"""
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from peft import PeftModel

print(f"\\nGenerating images for {EXP_NAME}...")

prompts_list = load_prompts("/content/carilla/ai/experiments/prompts_identity_v1.txt")

# ── Load base pipeline + inject trained LoRA ──
pipe = StableDiffusionPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    safety_checker=None,
    token=HF_TOKEN
).to("cuda")
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

# Load the FINAL checkpoint (last step)
final_ckpt = os.path.join(CKPT_DIR, f"step_{STEPS:04d}")
pipe.unet = PeftModel.from_pretrained(pipe.unet, final_ckpt)
pipe.unet.merge_adapter()  # fuse LoRA into weights for faster inference
pipe.unet.to("cuda", dtype=torch.float16)

# ── Generate 10 prompts × 4 seeds = 40 images ──
count = 0
for pi, prompt in enumerate(prompts_list, start=1):
    for seed in SEEDS:
        g   = torch.Generator(device="cuda").manual_seed(seed)
        img = pipe(
            prompt,
            num_inference_steps=INFER_STEPS,
            guidance_scale=CFG,
            generator=g,
            width=RESOLUTION,
            height=RESOLUTION,
        ).images[0]
        fname = f"{EXP_NAME}_p{pi:02d}_s{seed}.png"
        img.save(os.path.join(OUT_LOCAL, fname))
        count += 1

# Save meta.json
meta = {
    "experiment": EXP_NAME,
    "model_id": MODEL_ID,
    "n_train": N_TRAIN,
    "steps": STEPS,
    "lora_rank": LORA_RANK,
    "lr": LR,
    "infer_steps": INFER_STEPS,
    "cfg": CFG,
    "seeds": SEEDS,
    "prompts": prompts_list,
}
with open(os.path.join(OUT_LOCAL, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)

print(f"Generated {count} images + meta.json → {OUT_LOCAL}")

# ── Upload everything to Drive ──
exp_drive_folder_id = get_or_create_folder(CARILLA_ROOT_ID, EXP_NAME)
upload_folder_to_drive(OUT_LOCAL, exp_drive_folder_id)
print(f"\\n🔗 View on Drive: https://drive.google.com/drive/folders/{exp_drive_folder_id}")

# Clean up local GPU memory before next experiment
del pipe
torch.cuda.empty_cache()
print("GPU memory cleared. Ready for next experiment.")
"""


# ════════════════════════════════════════════════════════════════
# CELL 8 — DINO-I Scoring (run ONCE after ALL experiments done)
# Scores E1, E2, E3, E4 against real val images.
# ════════════════════════════════════════════════════════════════
"""
import torch, torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from pathlib import Path
import numpy as np, csv, os

# ── DINO ViT-S/16 model ──
print("Loading DINO model...")
dino_model = torch.hub.load("facebookresearch/dino:main", "dino_vits16")
dino_model.eval().to("cuda")
print("DINO loaded ✅")

DINO_TRANSFORM = transforms.Compose([
    transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

@torch.no_grad()
def get_feat(img_path):
    img = Image.open(img_path).convert("RGB")
    t   = DINO_TRANSFORM(img).unsqueeze(0).to("cuda")
    f   = dino_model(t)
    return F.normalize(f, dim=-1).squeeze(0)

def avg_feat(directory):
    paths = list(Path(directory).glob("*.jpg")) + list(Path(directory).glob("*.png"))
    feats = [get_feat(p) for p in paths]
    return F.normalize(torch.stack(feats).mean(0), dim=-1)

# ── Build reference vector from val set ──
print("\\nBuilding reference from val set...")
ref_feat = avg_feat(f"{DATASET_LOCAL_PATH}/val_512")
print(f"Reference built from {len(list(Path(f'{DATASET_LOCAL_PATH}/val_512').glob('*')))} val images.")

# ── Score each experiment ──
summary = []
for exp_name in ["E1", "E2", "E3", "E4"]:
    gen_dir = f"/content/out/{exp_name}"
    if not os.path.exists(gen_dir):
        print(f"  ⚠ {exp_name} not found, skipping.")
        continue

    gen_paths = list(Path(gen_dir).glob("*.png"))
    scores    = [torch.dot(ref_feat, get_feat(p)).item() for p in gen_paths]
    mean_s    = float(np.mean(scores))
    std_s     = float(np.std(scores))
    n         = len(scores)

    print(f"  {exp_name}: DINO-I = {mean_s:.4f} ± {std_s:.4f}  (n={n})")
    summary.append({"experiment": exp_name, "dino_i_mean": round(mean_s, 6),
                    "dino_i_std": round(std_s, 6), "n_images": n})

# ── Save summary CSV ──
csv_local = "/content/out/dino_i_summary.csv"
os.makedirs("/content/out", exist_ok=True)
with open(csv_local, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["experiment","dino_i_mean","dino_i_std","n_images"])
    w.writeheader()
    w.writerows(summary)

# ── Upload CSV to Drive ──
results_folder_id = get_or_create_folder(CARILLA_ROOT_ID, "DINO_scores")
upload_folder_to_drive("/content/out", results_folder_id)
print(f"\\n✅ DINO-I summary saved and uploaded.")
print(f"🔗 https://drive.google.com/drive/folders/{results_folder_id}")
"""