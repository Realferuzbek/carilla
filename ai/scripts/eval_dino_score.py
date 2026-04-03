"""
eval_dino_score.py — Paper 1 DINO-I identity score computation.

DINO-I measures how visually similar generated images are to real reference
images of the same subject, using DINO ViT-S/16 features and cosine similarity.
Higher score = better identity preservation.

Usage:
    python ai/scripts/eval_dino_score.py \
        --real_dir  ai/datasets/processed/sonata_luxury_v1/val_512 \
        --gen_dir   ai/experiments/results/E1 \
        --out_csv   ai/experiments/results/E1_dino_scores.csv

Requirements:
    pip install torch torchvision Pillow numpy pandas
"""

import argparse
import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms


# ── Image preprocessing (DINO standard) ───────────────────────────────────────
DINO_TRANSFORM = transforms.Compose([
    transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


def load_image(path: Path) -> torch.Tensor:
    img = Image.open(path).convert("RGB")
    return DINO_TRANSFORM(img).unsqueeze(0)  # (1, 3, 224, 224)


# ── Load DINO ViT-S/16 from torch.hub ─────────────────────────────────────────
def load_dino_model(device: torch.device) -> torch.nn.Module:
    print("Loading DINO ViT-S/16 from torch.hub...")
    model = torch.hub.load("facebookresearch/dino:main", "dino_vits16")
    model.eval()
    model.to(device)
    print("DINO model loaded.")
    return model


# ── Extract feature vector for one image ──────────────────────────────────────
@torch.no_grad()
def get_features(model: torch.nn.Module,
                 img_tensor: torch.Tensor,
                 device: torch.device) -> torch.Tensor:
    img_tensor = img_tensor.to(device)
    features = model(img_tensor)                     # (1, 384)
    return F.normalize(features, dim=-1).squeeze(0)  # (384,)


# ── Cosine similarity between two feature vectors ─────────────────────────────
def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    return torch.dot(a, b).item()


# ── Collect all image paths from a directory ──────────────────────────────────
def collect_images(directory: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    paths = sorted([p for p in directory.iterdir()
                    if p.suffix.lower() in exts])
    if not paths:
        raise ValueError(f"No images found in: {directory}")
    return paths


# ── Compute average DINO feature vector for a set of images ───────────────────
@torch.no_grad()
def average_features(model, paths: list[Path],
                     device: torch.device) -> torch.Tensor:
    feats = []
    for p in paths:
        img_t = load_image(p)
        f = get_features(model, img_t, device)
        feats.append(f)
    avg = torch.stack(feats).mean(dim=0)
    return F.normalize(avg, dim=-1)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Compute DINO-I identity score.")
    parser.add_argument("--real_dir", required=True,
                        help="Directory of real reference images (val set).")
    parser.add_argument("--gen_dir", required=True,
                        help="Directory of generated images for one experiment.")
    parser.add_argument("--out_csv", default="dino_scores.csv",
                        help="Output CSV path for per-image scores.")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    real_dir = Path(args.real_dir)
    gen_dir  = Path(args.gen_dir)
    out_csv  = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    model = load_dino_model(device)

    # Build a single reference vector from ALL real images (val set)
    real_paths = collect_images(real_dir)
    print(f"Reference images: {len(real_paths)} from {real_dir}")
    ref_feat = average_features(model, real_paths, device)

    # Score each generated image against the reference
    gen_paths = collect_images(gen_dir)
    print(f"Generated images: {len(gen_paths)} from {gen_dir}")

    rows = []
    scores = []
    for p in gen_paths:
        img_t = load_image(p)
        gen_feat = get_features(model, img_t, device)
        score = cosine_sim(ref_feat, gen_feat)
        rows.append({"image": p.name, "dino_i_score": round(score, 6)})
        scores.append(score)
        print(f"  {p.name}: {score:.4f}")

    mean_score = float(np.mean(scores))
    std_score  = float(np.std(scores))
    print(f"\nDINO-I  mean: {mean_score:.4f}  std: {std_score:.4f}  n={len(scores)}")

    # Write CSV
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "dino_i_score"])
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow({"image": "MEAN", "dino_i_score": round(mean_score, 6)})
        writer.writerow({"image": "STD",  "dino_i_score": round(std_score, 6)})

    print(f"Scores saved to: {out_csv}")


if __name__ == "__main__":
    main()