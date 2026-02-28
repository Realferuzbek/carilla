"""Paper 1 dataset preparation CLI for Stable Diffusion LoRA identity learning.

This script prepares the `sonata_luxury_v1` dataset for Paper 1 by:

- Parsing raw filenames with strict tags
- Center-cropping images to square (car should be roughly centered in frame)
- Writing PNG outputs at 1024 and 512 resolutions
- Generating per-image captions
- Creating deterministic train/val splits
- Writing manifest and split files for downstream training/evaluation
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("Missing dependency: Pillow. Install from ai/requirements.txt") from exc

try:
    from tqdm import tqdm
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("Missing dependency: tqdm. Install from ai/requirements.txt") from exc


LOGGER = logging.getLogger("dataset_prep")

AI_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = AI_ROOT / "datasets" / "raw" / "sonata_luxury_v1"
DEFAULT_OUT_DIR = AI_ROOT / "datasets" / "processed" / "sonata_luxury_v1"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIEWS = {"front", "rear", "left", "right", "front45", "rear45", "closeup"}
ALLOWED_LIGHTING = {"day", "cloudy", "sunset", "indoor"}
ALLOWED_LOCATIONS = {"parking", "street", "garage"}
MANIFEST_COLUMNS = [
    "filename_raw",
    "filename_1024",
    "filename_512",
    "split",
    "view",
    "lighting",
    "location",
    "caption",
]

RAW_STEM_PATTERN = re.compile(
    r"^(?P<view>[^_]+)_(?P<lighting>[^_]+)_(?P<location>[^_]+)_(?P<id>[A-Za-z0-9-]+)$"
)

VIEW_PHRASES = {
    "front": "front view",
    "rear": "rear view",
    "left": "left side view",
    "right": "right side view",
    "front45": "front 45 degree view",
    "rear45": "rear 45 degree view",
    "closeup": "close-up detail view",
}
LIGHTING_PHRASES = {
    "day": "daylight",
    "cloudy": "cloudy lighting",
    "sunset": "sunset lighting",
    "indoor": "indoor lighting",
}
LOCATION_PHRASES = {
    "parking": "in a parking area",
    "street": "on a street",
    "garage": "in a garage",
}

TARGET_SIZE_1024 = (1024, 1024)
TARGET_SIZE_512 = (512, 512)


@dataclass(frozen=True)
class RawSample:
    """Validated raw input sample parsed from filename tags."""

    raw_path: Path
    view: str
    lighting: str
    location: str
    stem_id: str
    ext: str

    @property
    def raw_filename(self) -> str:
        return self.raw_path.name

    @property
    def processed_stem(self) -> str:
        return self.raw_path.stem


@dataclass(frozen=True)
class ProcessedSample:
    """Processed output record used for manifest and split file generation."""

    filename_raw: str
    filename_1024: str
    filename_512: str
    split: str
    view: str
    lighting: str
    location: str
    caption: str
    caption_path: str

    def to_manifest_row(self) -> dict[str, str]:
        """Return a row dict matching the manifest CSV schema."""
        return {
            "filename_raw": self.filename_raw,
            "filename_1024": self.filename_1024,
            "filename_512": self.filename_512,
            "split": self.split,
            "view": self.view,
            "lighting": self.lighting,
            "location": self.location,
            "caption": self.caption,
        }


@dataclass(frozen=True)
class OutputDirs:
    """Normalized output directories under a processed dataset root."""

    root: Path
    images_1024: Path
    train_512: Path
    val_512: Path
    captions: Path
    splits: Path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepare Paper 1 dataset outputs (1024/512 PNGs, captions, splits, manifest). "
            "Uses center-crop to square, so keep the car roughly centered in source photos."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--raw_dir", type=Path, default=DEFAULT_RAW_DIR, help="Raw image directory")
    parser.add_argument(
        "--out_dir", type=Path, default=DEFAULT_OUT_DIR, help="Processed output root directory"
    )
    parser.add_argument("--train_count", type=int, default=70, help="Number of train samples")
    parser.add_argument("--val_count", type=int, default=10, help="Number of validation samples")
    parser.add_argument("--seed", type=int, default=20240226, help="Deterministic split seed")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files (raw files are never deleted)",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure console logging."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def center_crop_to_square(image: Image.Image) -> Image.Image:
    """Return a centered square crop from an image.

    This assumes the main subject (the car) is roughly centered in the frame.
    """
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def normalize_rel_path(path: Path, root: Path) -> str:
    """Return a POSIX-style path relative to the given root."""
    return path.relative_to(root).as_posix()


def discover_raw_images(raw_dir: Path) -> list[Path]:
    """Discover supported raw image files from the top level of `raw_dir`."""
    if not raw_dir.exists():
        raise SystemExit(f"Raw directory not found: {raw_dir}")
    if not raw_dir.is_dir():
        raise SystemExit(f"Raw path is not a directory: {raw_dir}")

    files = sorted((p for p in raw_dir.iterdir() if p.is_file()), key=lambda p: p.name.lower())
    supported: list[Path] = []
    ignored_non_images: list[str] = []

    for path in files:
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported.append(path)
        elif not path.name.startswith("."):
            ignored_non_images.append(path.name)

    if ignored_non_images:
        preview = ", ".join(ignored_non_images[:5])
        if len(ignored_non_images) > 5:
            preview += ", ..."
        LOGGER.warning(
            "Ignoring %d non-image files in raw directory: %s",
            len(ignored_non_images),
            preview,
        )

    if not supported:
        exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise SystemExit(f"No supported images found in {raw_dir} (expected extensions: {exts})")

    LOGGER.info("Discovered %d raw image(s) in %s", len(supported), raw_dir)
    return supported


def parse_raw_filename(path: Path) -> RawSample:
    """Parse and validate a raw image filename."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported extension: {path.name}")

    match = RAW_STEM_PATTERN.match(path.stem)
    if not match:
        raise ValueError(
            f"Invalid filename pattern for {path.name}. Expected "
            "{view}_{lighting}_{location}_{id}.{ext}"
        )

    view = match.group("view")
    lighting = match.group("lighting")
    location = match.group("location")
    stem_id = match.group("id")

    if view not in ALLOWED_VIEWS:
        raise ValueError(f"Invalid view '{view}' in {path.name}. Allowed: {sorted(ALLOWED_VIEWS)}")
    if lighting not in ALLOWED_LIGHTING:
        raise ValueError(
            f"Invalid lighting '{lighting}' in {path.name}. Allowed: {sorted(ALLOWED_LIGHTING)}"
        )
    if location not in ALLOWED_LOCATIONS:
        raise ValueError(
            f"Invalid location '{location}' in {path.name}. Allowed: {sorted(ALLOWED_LOCATIONS)}"
        )

    return RawSample(
        raw_path=path,
        view=view,
        lighting=lighting,
        location=location,
        stem_id=stem_id,
        ext=ext,
    )


def verify_image_readable(path: Path) -> None:
    """Verify that an image can be opened by Pillow."""
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(f"Unreadable image '{path.name}': {exc}") from exc


def validate_raw_set(raw_paths: Iterable[Path]) -> list[RawSample]:
    """Validate raw file names, tags, image readability, and output name collisions."""
    samples: list[RawSample] = []
    errors: list[str] = []
    processed_stems_seen: dict[str, str] = {}

    for raw_path in raw_paths:
        try:
            sample = parse_raw_filename(raw_path)
            verify_image_readable(raw_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        stem_key = sample.processed_stem.lower()
        existing_name = processed_stems_seen.get(stem_key)
        if existing_name is not None:
            errors.append(
                "Duplicate processed stem collision (case-insensitive): "
                f"{existing_name} and {sample.raw_filename}"
            )
            continue
        processed_stems_seen[stem_key] = sample.raw_filename
        samples.append(sample)

    if errors:
        joined = "\n".join(f"- {message}" for message in errors)
        raise SystemExit(f"Raw dataset validation failed:\n{joined}")

    samples.sort(key=lambda sample: sample.raw_filename.lower())
    LOGGER.info("Validated %d raw image filename(s) and tag(s)", len(samples))
    return samples


def build_caption(sample: RawSample) -> str:
    """Build a caption from parsed tags using the Paper 1 template."""
    view_phrase = VIEW_PHRASES[sample.view]
    location_phrase = LOCATION_PHRASES[sample.location]
    lighting_phrase = LIGHTING_PHRASES[sample.lighting]
    return (
        "photo of <carilla_sonata>, "
        f"{view_phrase}, "
        "Hyundai Sonata, white, 2020, Asia/Uzbekistan spec, '6-series', "
        f"{location_phrase}, "
        f"{lighting_phrase}, "
        "realistic car photo"
    )


def allocate_val_quotas_by_view(
    grouped_samples: dict[str, list[RawSample]],
    val_count: int,
    rng: random.Random,
) -> dict[str, int]:
    """Allocate validation counts per view using proportional quotas.

    Uses floor allocation plus iterative largest-remainder distribution.
    Raises `RuntimeError` if an exact allocation cannot be produced.
    """
    group_counts = {view: len(items) for view, items in grouped_samples.items()}
    total = sum(group_counts.values())
    if total == 0:
        if val_count == 0:
            return {}
        raise RuntimeError("Cannot allocate validation quotas from an empty dataset")

    targets = {view: (count * val_count) / total for view, count in group_counts.items()}
    quotas = {view: min(count, int(math.floor(targets[view]))) for view, count in group_counts.items()}
    remaining = val_count - sum(quotas.values())
    if remaining < 0:
        raise RuntimeError("Quota allocation over-assigned validation samples")

    # Seeded tie-breakers keep allocation deterministic across runs.
    tie_breakers = {view: rng.random() for view in group_counts}

    while remaining > 0:
        candidates = [view for view, count in group_counts.items() if quotas[view] < count]
        if not candidates:
            raise RuntimeError("Unable to allocate exact validation count across view groups")
        candidates.sort(
            key=lambda view: (
                targets[view] - quotas[view],
                group_counts[view] - quotas[view],
                tie_breakers[view],
            ),
            reverse=True,
        )
        quotas[candidates[0]] += 1
        remaining -= 1

    if sum(quotas.values()) != val_count:
        raise RuntimeError("Final quota allocation does not match requested validation count")

    return quotas


def fallback_random_split(
    samples: list[RawSample],
    val_count: int,
    seed: int,
) -> tuple[list[RawSample], list[RawSample]]:
    """Fallback deterministic random split using a fixed seed."""
    rng = random.Random(seed)
    shuffled = list(samples)
    rng.shuffle(shuffled)
    val_samples = shuffled[:val_count]
    train_samples = shuffled[val_count:]
    return sort_samples(train_samples), sort_samples(val_samples)


def sort_samples(samples: Iterable[RawSample]) -> list[RawSample]:
    """Sort samples deterministically by raw filename."""
    return sorted(samples, key=lambda sample: sample.raw_filename.lower())


def split_samples(
    samples: list[RawSample],
    train_count: int,
    val_count: int,
    seed: int,
) -> tuple[list[RawSample], list[RawSample]]:
    """Split samples into train and val, preferring deterministic stratification by view."""
    total_expected = train_count + val_count
    if train_count < 0 or val_count < 0:
        raise SystemExit("train_count and val_count must be non-negative")
    if len(samples) != total_expected:
        raise SystemExit(
            "Valid raw image count must exactly match train_count + val_count. "
            f"Found {len(samples)} valid image(s), expected {total_expected} "
            f"({train_count} train + {val_count} val)."
        )

    if val_count == 0:
        return sort_samples(samples), []

    grouped: dict[str, list[RawSample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.view].append(sample)

    try:
        rng = random.Random(seed)
        for view_items in grouped.values():
            rng.shuffle(view_items)
        quotas = allocate_val_quotas_by_view(grouped, val_count, rng)

        train_samples: list[RawSample] = []
        val_samples: list[RawSample] = []
        for view in sorted(grouped.keys()):
            items = grouped[view]
            view_val_count = quotas.get(view, 0)
            val_samples.extend(items[:view_val_count])
            train_samples.extend(items[view_val_count:])

        if len(train_samples) != train_count or len(val_samples) != val_count:
            raise RuntimeError(
                "Stratified split produced incorrect counts: "
                f"train={len(train_samples)}, val={len(val_samples)}"
            )

        LOGGER.info("Split strategy: deterministic stratified-by-view (best effort)")
        return sort_samples(train_samples), sort_samples(val_samples)
    except RuntimeError as exc:
        LOGGER.warning("Stratified split unavailable (%s). Falling back to deterministic random split.", exc)
        train_samples, val_samples = fallback_random_split(samples, val_count, seed)
        if len(train_samples) != train_count or len(val_samples) != val_count:
            raise SystemExit(
                "Fallback random split produced incorrect counts: "
                f"train={len(train_samples)}, val={len(val_samples)}"
            )
        LOGGER.info("Split strategy: deterministic random fallback")
        return train_samples, val_samples


def ensure_output_dirs(out_dir: Path) -> OutputDirs:
    """Create output directories if missing and return typed handles."""
    images_1024 = out_dir / "images_1024"
    train_512 = out_dir / "train_512"
    val_512 = out_dir / "val_512"
    captions = out_dir / "captions"
    splits = out_dir / "splits"
    for directory in (images_1024, train_512, val_512, captions, splits):
        directory.mkdir(parents=True, exist_ok=True)
    return OutputDirs(
        root=out_dir,
        images_1024=images_1024,
        train_512=train_512,
        val_512=val_512,
        captions=captions,
        splits=splits,
    )


def build_output_paths(sample: RawSample, split: str, dirs: OutputDirs) -> tuple[Path, Path, Path]:
    """Build output file paths for a sample and split."""
    stem = sample.processed_stem
    image_1024 = dirs.images_1024 / f"{stem}.png"
    image_512_root = dirs.train_512 if split == "train" else dirs.val_512
    image_512 = image_512_root / f"{stem}.png"
    caption_path = dirs.captions / f"{stem}.txt"
    return image_1024, image_512, caption_path


def preflight_output_conflicts(
    assignments: list[tuple[str, RawSample]],
    dirs: OutputDirs,
    overwrite: bool,
) -> None:
    """Validate target paths for collisions and overwrite rules before writing files."""
    seen_rel_paths_ci: dict[str, str] = {}
    duplicate_errors: list[str] = []
    all_targets: list[Path] = []

    for split, sample in assignments:
        image_1024, image_512, caption_path = build_output_paths(sample, split, dirs)
        all_targets.extend([image_1024, image_512, caption_path])
        for path in (image_1024, image_512, caption_path):
            rel = normalize_rel_path(path, dirs.root)
            key = rel.lower()
            existing = seen_rel_paths_ci.get(key)
            if existing is not None and existing != rel:
                duplicate_errors.append(
                    f"Case-insensitive output path collision: '{existing}' vs '{rel}'"
                )
            else:
                seen_rel_paths_ci[key] = rel

    manifest_path = dirs.root / "manifest_generated.csv"
    split_train_path = dirs.splits / "train.txt"
    split_val_path = dirs.splits / "val.txt"
    all_targets.extend([manifest_path, split_train_path, split_val_path])

    if duplicate_errors:
        joined = "\n".join(f"- {message}" for message in duplicate_errors)
        raise SystemExit(f"Output collision check failed:\n{joined}")

    if overwrite:
        return

    existing_targets = [path for path in all_targets if path.exists()]
    if existing_targets:
        preview = "\n".join(f"- {path}" for path in sorted(existing_targets, key=lambda p: str(p).lower()))
        raise SystemExit(
            "Output files already exist. Re-run with --overwrite to replace them.\n"
            f"{preview}"
        )


def process_single_sample(
    sample: RawSample,
    split: str,
    dirs: OutputDirs,
) -> ProcessedSample:
    """Process one sample and write image/caption outputs."""
    image_1024_path, image_512_path, caption_path = build_output_paths(sample, split, dirs)
    caption = build_caption(sample)

    try:
        with Image.open(sample.raw_path) as image:
            rgb_image = image.convert("RGB")
            cropped = center_crop_to_square(rgb_image)
            resized_1024 = cropped.resize(TARGET_SIZE_1024, Image.LANCZOS)
            resized_512 = cropped.resize(TARGET_SIZE_512, Image.LANCZOS)
            resized_1024.save(image_1024_path, format="PNG")
            resized_512.save(image_512_path, format="PNG")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise SystemExit(f"Failed processing '{sample.raw_filename}': {exc}") from exc

    caption_path.write_text(caption + "\n", encoding="utf-8")

    return ProcessedSample(
        filename_raw=sample.raw_filename,
        filename_1024=normalize_rel_path(image_1024_path, dirs.root),
        filename_512=normalize_rel_path(image_512_path, dirs.root),
        split=split,
        view=sample.view,
        lighting=sample.lighting,
        location=sample.location,
        caption=caption,
        caption_path=normalize_rel_path(caption_path, dirs.root),
    )


def write_manifest(rows: list[ProcessedSample], manifest_path: Path) -> None:
    """Write the generated manifest CSV."""
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_manifest_row())


def write_split_files(rows: list[ProcessedSample], splits_dir: Path) -> None:
    """Write train/val split files with image and caption paths."""
    train_lines: list[str] = []
    val_lines: list[str] = []
    for row in rows:
        line = f"{row.filename_512}\t{row.caption_path}"
        if row.split == "train":
            train_lines.append(line)
        elif row.split == "val":
            val_lines.append(line)
        else:  # pragma: no cover - internal invariant
            raise SystemExit(f"Unexpected split value while writing split files: {row.split}")

    (splits_dir / "train.txt").write_text("\n".join(train_lines) + ("\n" if train_lines else ""), encoding="utf-8")
    (splits_dir / "val.txt").write_text("\n".join(val_lines) + ("\n" if val_lines else ""), encoding="utf-8")


def log_split_summary(train_samples: list[RawSample], val_samples: list[RawSample]) -> None:
    """Log split counts and per-view distribution."""
    LOGGER.info("Split counts: train=%d, val=%d", len(train_samples), len(val_samples))
    train_by_view = Counter(sample.view for sample in train_samples)
    val_by_view = Counter(sample.view for sample in val_samples)
    LOGGER.info("Train distribution by view: %s", dict(sorted(train_by_view.items())))
    LOGGER.info("Val distribution by view: %s", dict(sorted(val_by_view.items())))


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    configure_logging()

    raw_dir = args.raw_dir
    out_dir = args.out_dir

    raw_paths = discover_raw_images(raw_dir)
    samples = validate_raw_set(raw_paths)

    train_samples, val_samples = split_samples(
        samples=samples,
        train_count=args.train_count,
        val_count=args.val_count,
        seed=args.seed,
    )
    log_split_summary(train_samples, val_samples)

    dirs = ensure_output_dirs(out_dir)
    assignments: list[tuple[str, RawSample]] = [("train", sample) for sample in train_samples] + [
        ("val", sample) for sample in val_samples
    ]
    preflight_output_conflicts(assignments, dirs, overwrite=args.overwrite)

    LOGGER.info("Writing processed outputs to %s", dirs.root)
    processed_rows: list[ProcessedSample] = []
    for split, sample in tqdm(assignments, desc="Processing images", unit="image"):
        processed_rows.append(process_single_sample(sample, split, dirs))

    processed_rows.sort(key=lambda row: (0 if row.split == "train" else 1, row.filename_raw.lower()))
    manifest_path = dirs.root / "manifest_generated.csv"
    write_manifest(processed_rows, manifest_path)
    write_split_files(processed_rows, dirs.splits)

    LOGGER.info("Wrote manifest: %s", manifest_path)
    LOGGER.info("Wrote split files: %s", dirs.splits)
    LOGGER.info("Completed dataset preparation successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
