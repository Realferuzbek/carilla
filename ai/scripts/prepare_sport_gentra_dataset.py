from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "datasets" / "raw" / "sport_gentra"
OUT_IMAGES_DIR = ROOT / "datasets" / "processed" / "sport_gentra" / "images"
CAPTIONS_PATH = ROOT / "datasets" / "processed" / "sport_gentra" / "captions.txt"

DEFAULT_CAPTION = (
    "ultra realistic photo of a black Chevrolet Gentra 2024 in aggressive sport tuning, "
    "wide body kit, carbon fiber details, parked in a premium studio, soft lighting, 8k detail"
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TARGET_SIZE = (768, 768)


def center_crop_to_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    right = left + side
    bottom = top + side
    return image.crop((left, top, right, bottom))


def gather_images():
    if not RAW_DIR.exists():
        sys.exit(f"Raw directory not found: {RAW_DIR}")

    images = [
        path
        for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not images:
        sys.exit(f"No images found in {RAW_DIR} (looking for .jpg, .jpeg, .png, .webp)")

    return sorted(images)


def ensure_output_dirs():
    OUT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    CAPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)


def process_images(images):
    ensure_output_dirs()
    processed_count = 0

    with CAPTIONS_PATH.open("w", encoding="utf-8") as captions_file:
        for idx, image_path in enumerate(images):
            with Image.open(image_path) as img:
                rgb_image = img.convert("RGB")
                cropped = center_crop_to_square(rgb_image)
                resized = cropped.resize(TARGET_SIZE, Image.LANCZOS)

            filename = f"sport_gentra_{idx:04d}.png"
            out_path = OUT_IMAGES_DIR / filename
            resized.save(out_path, format="PNG")

            captions_file.write(DEFAULT_CAPTION + "\n")
            processed_count += 1

    return processed_count


def main():
    images = gather_images()
    processed = process_images(images)

    print(f"Processed {processed} images.")
    print(f"Images saved to: {OUT_IMAGES_DIR}")
    print(f"Captions saved to: {CAPTIONS_PATH}")


if __name__ == "__main__":
    main()
