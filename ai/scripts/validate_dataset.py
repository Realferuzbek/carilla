"""Validate processed Paper 1 dataset outputs for `sonata_luxury_v1`.

Checks include:
- manifest schema and counts
- tag validity
- duplicate entries
- caption files and contents
- image file presence and dimensions (1024 / 512)
- split file formatting and consistency
- optional raw filename/tag validation
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable


LOGGER = logging.getLogger("validate_dataset")

AI_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROCESSED_DIR = AI_ROOT / "datasets" / "processed" / "sonata_luxury_v1"
DEFAULT_RAW_DIR = AI_ROOT / "datasets" / "raw" / "sonata_luxury_v1"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIEWS = {"front", "rear", "left", "right", "front45", "rear45", "closeup"}
ALLOWED_LIGHTING = {"day", "cloudy", "sunset", "indoor"}
ALLOWED_LOCATIONS = {"parking", "street", "garage"}
EXPECTED_MANIFEST_COLUMNS = [
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


@dataclass
class ValidationReport:
    """Collect PASS/WARN/ERROR messages and expose exit status."""

    passes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_pass(self, message: str) -> None:
        self.passes.append(message)

    def add_warn(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for dataset validation."""
    parser = argparse.ArgumentParser(
        description="Validate processed Paper 1 dataset artifacts (manifest, images, captions, splits).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed_dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Processed dataset root directory",
    )
    parser.add_argument(
        "--raw_dir",
        type=Path,
        default=None,
        help="Optional raw dataset directory to validate raw filenames/tags against the manifest",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional manifest CSV path override (defaults to <processed_dir>/manifest_generated.csv)",
    )
    parser.add_argument("--train_count", type=int, default=70, help="Expected train split count")
    parser.add_argument("--val_count", type=int, default=10, help="Expected validation split count")
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Strict validation mode (default behavior; included for explicit CI usage)",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure console logging."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def import_pandas_module():
    """Import pandas lazily so `--help` works without installed dependencies."""
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise SystemExit("Missing dependency: pandas. Install from ai/requirements.txt") from exc
    return pd


def normalize_rel_str(path_str: str) -> str:
    """Normalize a relative path string to POSIX separators."""
    return path_str.replace("\\", "/").strip()


def is_safe_relative_path(path_str: str) -> tuple[bool, str]:
    """Validate that a path string is a safe relative path."""
    if not path_str or not path_str.strip():
        return False, "path is empty"
    normalized = normalize_rel_str(path_str)
    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute():
        return False, "path must be relative"
    if re.match(r"^[A-Za-z]:", normalized):
        return False, "path must not include a Windows drive prefix"
    if ".." in pure_path.parts:
        return False, "path traversal ('..') is not allowed"
    return True, ""


def resolve_relative_file(processed_dir: Path, path_str: str) -> Path | None:
    """Resolve a manifest/split relative path under the processed root safely."""
    is_safe, reason = is_safe_relative_path(path_str)
    if not is_safe:
        return None
    normalized = normalize_rel_str(path_str)
    pure_path = PurePosixPath(normalized)
    return processed_dir.joinpath(*pure_path.parts)


def discover_raw_images(raw_dir: Path, report: ValidationReport) -> list[Path]:
    """Discover supported raw images and warn on non-image files."""
    if not raw_dir.exists():
        report.add_error(f"Raw directory not found: {raw_dir}")
        return []
    if not raw_dir.is_dir():
        report.add_error(f"Raw path is not a directory: {raw_dir}")
        return []

    files = sorted((path for path in raw_dir.iterdir() if path.is_file()), key=lambda path: path.name.lower())
    supported: list[Path] = []
    ignored_non_images: list[str] = []
    for path in files:
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported.append(path)
        elif not path.name.startswith("."):
            ignored_non_images.append(path.name)

    if ignored_non_images:
        report.add_warn(
            f"Ignoring {len(ignored_non_images)} non-image file(s) in raw directory: "
            + ", ".join(ignored_non_images[:5])
            + (", ..." if len(ignored_non_images) > 5 else "")
        )
    return supported


def parse_raw_filename(path: Path) -> tuple[str, str, str]:
    """Parse a raw filename and return (view, lighting, location)."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
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

    if view not in ALLOWED_VIEWS:
        raise ValueError(f"Invalid view '{view}' in {path.name}")
    if lighting not in ALLOWED_LIGHTING:
        raise ValueError(f"Invalid lighting '{lighting}' in {path.name}")
    if location not in ALLOWED_LOCATIONS:
        raise ValueError(f"Invalid location '{location}' in {path.name}")

    return view, lighting, location


def verify_image(path: Path) -> tuple[int, int]:
    """Open an image and return its dimensions."""
    try:
        from PIL import Image, UnidentifiedImageError  # type: ignore
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise SystemExit("Missing dependency: Pillow. Install from ai/requirements.txt") from exc
    try:
        with Image.open(path) as image:
            return image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(f"Unreadable image '{path}': {exc}") from exc


def load_manifest(manifest_path: Path, report: ValidationReport) -> pd.DataFrame | None:
    """Load manifest CSV into a DataFrame with string columns."""
    pd = import_pandas_module()
    if not manifest_path.exists():
        report.add_error(f"Manifest not found: {manifest_path}")
        return None
    if not manifest_path.is_file():
        report.add_error(f"Manifest path is not a file: {manifest_path}")
        return None

    try:
        df = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    except Exception as exc:  # pragma: no cover - parser/runtime dependent
        report.add_error(f"Failed to read manifest CSV '{manifest_path}': {exc}")
        return None

    for column in df.columns:
        df[column] = df[column].astype(str).str.strip()
    report.add_pass(f"Loaded manifest: {manifest_path} ({len(df)} row(s))")
    return df


def validate_manifest_schema(df: pd.DataFrame, report: ValidationReport) -> bool:
    """Validate required manifest columns."""
    missing = [col for col in EXPECTED_MANIFEST_COLUMNS if col not in df.columns]
    extras = [col for col in df.columns if col not in EXPECTED_MANIFEST_COLUMNS]
    if missing:
        report.add_error(f"Manifest missing required column(s): {missing}")
        return False
    if extras:
        report.add_warn(f"Manifest has extra column(s): {extras}")
    report.add_pass("Manifest schema contains required columns")
    return True


def validate_counts(df: pd.DataFrame, train_count: int, val_count: int, report: ValidationReport) -> None:
    """Validate row and split counts in the manifest."""
    expected_total = train_count + val_count
    actual_total = len(df)
    if actual_total != expected_total:
        report.add_error(
            f"Manifest row count mismatch: expected {expected_total}, found {actual_total}"
        )
    else:
        report.add_pass(f"Manifest row count matches expected total ({expected_total})")

    split_counts = df["split"].value_counts(dropna=False).to_dict()
    actual_train = int(split_counts.get("train", 0))
    actual_val = int(split_counts.get("val", 0))
    if actual_train != train_count:
        report.add_error(f"Train split count mismatch: expected {train_count}, found {actual_train}")
    else:
        report.add_pass(f"Train split count matches expected ({train_count})")
    if actual_val != val_count:
        report.add_error(f"Val split count mismatch: expected {val_count}, found {actual_val}")
    else:
        report.add_pass(f"Val split count matches expected ({val_count})")

    unknown_splits = sorted({value for value in df["split"].unique().tolist() if value not in {"train", "val"}})
    if unknown_splits:
        report.add_error(f"Manifest contains invalid split value(s): {unknown_splits}")


def validate_tag_values(df: pd.DataFrame, report: ValidationReport) -> None:
    """Validate tag columns and empties."""
    for column, allowed_values in (
        ("view", ALLOWED_VIEWS),
        ("lighting", ALLOWED_LIGHTING),
        ("location", ALLOWED_LOCATIONS),
    ):
        values = df[column].astype(str).str.strip()
        empty_mask = values.eq("")
        if empty_mask.any():
            report.add_error(f"Manifest has empty values in '{column}' ({int(empty_mask.sum())} row(s))")
        invalid_values = sorted(set(values[~values.isin(sorted(allowed_values))].tolist()) - {""})
        if invalid_values:
            report.add_error(f"Manifest has invalid {column} value(s): {invalid_values}")
        else:
            report.add_pass(f"Manifest '{column}' values are valid")


def _report_duplicates(df: pd.DataFrame, column: str, report: ValidationReport) -> None:
    """Report duplicate values in a manifest column (case-sensitive and case-insensitive)."""
    values = df[column].astype(str)
    dup_mask = values.duplicated(keep=False)
    if dup_mask.any():
        samples = sorted(set(values[dup_mask].tolist()))[:5]
        report.add_error(f"Duplicate manifest values in '{column}': {samples}")
    else:
        report.add_pass(f"No duplicate values in manifest '{column}'")

    lowered = values.str.lower()
    dup_lower_mask = lowered.duplicated(keep=False)
    if dup_lower_mask.any():
        samples_ci = sorted(set(values[dup_lower_mask].tolist()))[:5]
        report.add_error(f"Case-insensitive duplicates in manifest '{column}': {samples_ci}")


def validate_duplicates(df: pd.DataFrame, report: ValidationReport) -> None:
    """Validate duplicate rows and duplicate key path/name columns."""
    for column in ("filename_raw", "filename_1024", "filename_512"):
        _report_duplicates(df, column, report)


def derive_caption_rel_path(filename_512: str) -> str:
    """Derive the expected caption path from a 512 image path."""
    image_pure = PurePosixPath(normalize_rel_str(filename_512))
    return str(PurePosixPath("captions") / f"{image_pure.stem}.txt")


def validate_manifest_paths_and_files(
    df: pd.DataFrame,
    processed_dir: Path,
    report: ValidationReport,
) -> None:
    """Validate manifest path safety, file existence, and split/path consistency."""
    missing_files = 0
    path_errors = 0

    for row in df.to_dict(orient="records"):
        split = row["split"]
        filename_1024 = row["filename_1024"]
        filename_512 = row["filename_512"]

        for column_name, rel_path in (("filename_1024", filename_1024), ("filename_512", filename_512)):
            is_safe, reason = is_safe_relative_path(rel_path)
            if not is_safe:
                report.add_error(f"Manifest {column_name} '{rel_path}' is invalid: {reason}")
                path_errors += 1
                continue
            resolved = resolve_relative_file(processed_dir, rel_path)
            if resolved is None:
                report.add_error(f"Manifest {column_name} '{rel_path}' could not be resolved safely")
                path_errors += 1
                continue
            if not resolved.exists():
                report.add_error(f"Manifest {column_name} file not found: {resolved}")
                missing_files += 1

        norm_1024 = normalize_rel_str(filename_1024)
        norm_512 = normalize_rel_str(filename_512)
        if not norm_1024.startswith("images_1024/"):
            report.add_error(f"Manifest filename_1024 must be under images_1024/: {filename_1024}")
            path_errors += 1

        expected_512_prefix = "train_512/" if split == "train" else "val_512/" if split == "val" else None
        if expected_512_prefix is None:
            report.add_error(f"Manifest row has invalid split value for filename_512 routing: {split!r}")
            path_errors += 1
        elif not norm_512.startswith(expected_512_prefix):
            report.add_error(
                "Manifest filename_512 path does not match split "
                f"('{split}'): {filename_512}"
            )
            path_errors += 1

    if missing_files == 0 and path_errors == 0:
        report.add_pass("Manifest paths resolve safely and referenced image files exist")


def validate_captions(
    df: pd.DataFrame,
    processed_dir: Path,
    report: ValidationReport,
) -> None:
    """Validate manifest caption values and derived caption files."""
    empty_caption_rows = df["caption"].astype(str).str.strip().eq("")
    if empty_caption_rows.any():
        report.add_error(f"Manifest has empty caption values ({int(empty_caption_rows.sum())} row(s))")

    missing_caption_files = 0
    empty_caption_files = 0
    mismatched_caption_files = 0

    for row in df.to_dict(orient="records"):
        expected_caption_rel = derive_caption_rel_path(row["filename_512"])
        caption_path = resolve_relative_file(processed_dir, expected_caption_rel)
        if caption_path is None:
            report.add_error(f"Derived caption path is invalid: {expected_caption_rel}")
            continue
        if not caption_path.exists():
            report.add_error(f"Caption file not found: {caption_path}")
            missing_caption_files += 1
            continue
        try:
            caption_text = caption_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            report.add_error(f"Failed to read caption file '{caption_path}': {exc}")
            continue
        if not caption_text:
            report.add_error(f"Caption file is empty: {caption_path}")
            empty_caption_files += 1
            continue
        if caption_text != row["caption"].strip():
            report.add_error(
                "Caption mismatch between manifest and file "
                f"for '{row['filename_512']}' (caption file: {expected_caption_rel})"
            )
            mismatched_caption_files += 1

    if not empty_caption_rows.any() and missing_caption_files == 0 and empty_caption_files == 0 and mismatched_caption_files == 0:
        report.add_pass("Manifest captions and caption files are present, non-empty, and consistent")


def validate_image_sizes(
    df: pd.DataFrame,
    processed_dir: Path,
    report: ValidationReport,
) -> None:
    """Validate dimensions for 1024 and 512 output images."""
    size_errors = 0

    seen_paths: set[str] = set()
    for row in df.to_dict(orient="records"):
        for column_name, expected_size in (("filename_1024", (1024, 1024)), ("filename_512", (512, 512))):
            rel_path = normalize_rel_str(row[column_name])
            if rel_path in seen_paths:
                continue
            seen_paths.add(rel_path)
            resolved = resolve_relative_file(processed_dir, rel_path)
            if resolved is None or not resolved.exists():
                continue
            try:
                size = verify_image(resolved)
            except ValueError as exc:
                report.add_error(str(exc))
                size_errors += 1
                continue
            if size != expected_size:
                report.add_error(
                    f"Unexpected image size for {resolved}: expected {expected_size}, found {size}"
                )
                size_errors += 1

    if size_errors == 0:
        report.add_pass("Output image sizes are valid (1024x1024 and 512x512)")


def parse_split_file(
    split_file: Path,
    split_name: str,
    processed_dir: Path,
    report: ValidationReport,
) -> list[tuple[str, str]]:
    """Parse and validate a split file, returning normalized (image, caption) pairs."""
    if not split_file.exists():
        report.add_error(f"Split file not found: {split_file}")
        return []
    if not split_file.is_file():
        report.add_error(f"Split path is not a file: {split_file}")
        return []

    pairs: list[tuple[str, str]] = []
    local_errors = 0
    try:
        lines = split_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        report.add_error(f"Failed reading split file '{split_file}': {exc}")
        return []

    expected_image_prefix = "train_512/" if split_name == "train" else "val_512/"
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            report.add_error(f"{split_file} line {line_no}: blank lines are not allowed")
            local_errors += 1
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            report.add_error(
                f"{split_file} line {line_no}: expected '<image_path>\\t<caption_path>', got: {line!r}"
            )
            local_errors += 1
            continue
        image_rel, caption_rel = (normalize_rel_str(part) for part in parts)

        for label, rel_path in (("image", image_rel), ("caption", caption_rel)):
            is_safe, reason = is_safe_relative_path(rel_path)
            if not is_safe:
                report.add_error(
                    f"{split_file} line {line_no}: invalid {label} path '{rel_path}': {reason}"
                )
                local_errors += 1
                continue
            resolved = resolve_relative_file(processed_dir, rel_path)
            if resolved is None or not resolved.exists():
                report.add_error(f"{split_file} line {line_no}: {label} file not found: {rel_path}")
                local_errors += 1

        if not image_rel.startswith(expected_image_prefix):
            report.add_error(
                f"{split_file} line {line_no}: image path must start with '{expected_image_prefix}'"
            )
            local_errors += 1
        if not caption_rel.startswith("captions/"):
            report.add_error(f"{split_file} line {line_no}: caption path must start with 'captions/'")
            local_errors += 1

        pairs.append((image_rel, caption_rel))

    duplicate_pairs = {pair for pair in pairs if pairs.count(pair) > 1}
    if duplicate_pairs:
        report.add_error(f"{split_file}: duplicate split entries detected (showing up to 5): {list(sorted(duplicate_pairs))[:5]}")
    elif local_errors == 0:
        report.add_pass(f"Split file format is valid: {split_file.name} ({len(pairs)} line(s))")
    return pairs


def expected_split_pairs_from_manifest(df: pd.DataFrame, split_name: str) -> list[tuple[str, str]]:
    """Build expected split (image, caption) pairs from manifest rows."""
    subset = df[df["split"] == split_name]
    pairs: list[tuple[str, str]] = []
    for row in subset.to_dict(orient="records"):
        image_rel = normalize_rel_str(row["filename_512"])
        caption_rel = derive_caption_rel_path(image_rel)
        pairs.append((image_rel, caption_rel))
    return pairs


def validate_split_files(
    df: pd.DataFrame,
    processed_dir: Path,
    report: ValidationReport,
) -> None:
    """Validate train.txt and val.txt formatting and consistency with the manifest."""
    split_dir = processed_dir / "splits"
    train_pairs = parse_split_file(split_dir / "train.txt", "train", processed_dir, report)
    val_pairs = parse_split_file(split_dir / "val.txt", "val", processed_dir, report)

    expected_train_pairs = expected_split_pairs_from_manifest(df, "train")
    expected_val_pairs = expected_split_pairs_from_manifest(df, "val")

    if len(train_pairs) != len(expected_train_pairs):
        report.add_error(
            f"splits/train.txt line count mismatch: expected {len(expected_train_pairs)}, found {len(train_pairs)}"
        )
    else:
        report.add_pass(f"splits/train.txt line count matches manifest ({len(train_pairs)})")

    if len(val_pairs) != len(expected_val_pairs):
        report.add_error(
            f"splits/val.txt line count mismatch: expected {len(expected_val_pairs)}, found {len(val_pairs)}"
        )
    else:
        report.add_pass(f"splits/val.txt line count matches manifest ({len(val_pairs)})")

    if set(train_pairs) != set(expected_train_pairs):
        report.add_error("splits/train.txt entries do not match manifest-derived train pairs")
    else:
        report.add_pass("splits/train.txt entries match manifest-derived train pairs")

    if set(val_pairs) != set(expected_val_pairs):
        report.add_error("splits/val.txt entries do not match manifest-derived val pairs")
    else:
        report.add_pass("splits/val.txt entries match manifest-derived val pairs")


def validate_raw_dir_against_manifest(
    raw_dir: Path,
    df: pd.DataFrame,
    train_count: int,
    val_count: int,
    report: ValidationReport,
) -> None:
    """Optionally validate raw filenames/tags and compare raw set to manifest."""
    raw_images = discover_raw_images(raw_dir, report)
    if not raw_images:
        return

    errors_before = len(report.errors)
    parsed_names: list[str] = []
    for path in raw_images:
        try:
            parse_raw_filename(path)
            verify_image(path)
            parsed_names.append(path.name)
        except ValueError as exc:
            report.add_error(str(exc))

    lowered_names = [name.lower() for name in parsed_names]
    if len(lowered_names) != len(set(lowered_names)):
        report.add_error("Raw directory contains case-insensitive duplicate filenames")

    expected_total = train_count + val_count
    if len(raw_images) != expected_total:
        report.add_error(
            f"Raw image count mismatch: expected {expected_total}, found {len(raw_images)}"
        )
    else:
        report.add_pass(f"Raw image count matches expected total ({expected_total})")

    manifest_raw_names = sorted(df["filename_raw"].astype(str).tolist())
    raw_names_sorted = sorted(parsed_names)
    if sorted(name.lower() for name in manifest_raw_names) != sorted(name.lower() for name in raw_names_sorted):
        missing_in_manifest = sorted(set(raw_names_sorted) - set(manifest_raw_names))
        missing_in_raw = sorted(set(manifest_raw_names) - set(raw_names_sorted))
        if missing_in_manifest:
            report.add_error(
                f"Raw files missing from manifest (showing up to 5): {missing_in_manifest[:5]}"
            )
        if missing_in_raw:
            report.add_error(
                f"Manifest raw filenames missing from raw directory (showing up to 5): {missing_in_raw[:5]}"
            )
    else:
        report.add_pass("Raw filenames match manifest filename_raw entries")

    if len(report.errors) == errors_before:
        report.add_pass("Optional raw directory validation completed without errors")


def print_report(report: ValidationReport) -> None:
    """Print a structured validation report."""
    def _print_section(title: str, items: Iterable[str]) -> None:
        print(title)
        items_list = list(items)
        if not items_list:
            print("  (none)")
            return
        for item in items_list:
            print(f"  - {item}")

    _print_section("PASS:", report.passes)
    _print_section("WARN:", report.warnings)
    _print_section("ERROR:", report.errors)

    print("SUMMARY:")
    print(f"  - passes: {len(report.passes)}")
    print(f"  - warnings: {len(report.warnings)}")
    print(f"  - errors: {len(report.errors)}")
    print(f"  - exit_code: {1 if report.has_errors else 0}")


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    configure_logging()
    if args.strict:
        LOGGER.info("Strict validation mode enabled")

    if args.train_count < 0 or args.val_count < 0:
        print("ERROR: train_count and val_count must be non-negative")
        return 2

    processed_dir = args.processed_dir
    manifest_path = args.manifest or (processed_dir / "manifest_generated.csv")
    report = ValidationReport()

    if not processed_dir.exists():
        report.add_error(f"Processed directory not found: {processed_dir}")
        print_report(report)
        return 1
    if not processed_dir.is_dir():
        report.add_error(f"Processed path is not a directory: {processed_dir}")
        print_report(report)
        return 1

    df = load_manifest(manifest_path, report)
    if df is None:
        print_report(report)
        return 1

    schema_ok = validate_manifest_schema(df, report)
    if not schema_ok:
        print_report(report)
        return 1

    validate_counts(df, args.train_count, args.val_count, report)
    validate_tag_values(df, report)
    validate_duplicates(df, report)
    validate_manifest_paths_and_files(df, processed_dir, report)
    validate_captions(df, processed_dir, report)
    validate_image_sizes(df, processed_dir, report)
    validate_split_files(df, processed_dir, report)

    if args.raw_dir is not None:
        validate_raw_dir_against_manifest(args.raw_dir, df, args.train_count, args.val_count, report)

    print_report(report)
    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
