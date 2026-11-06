#!/usr/bin/env python3
"""
Clean up AWS_Report directory by removing large files not needed for model training.

Keeps:
- run_metadata.json
- reports/ (all .rpt files)
- logs/ (all .log and .json files)
- config.mk

Removes:
- results/*.gds (GDSII files)
- results/*.odb (OpenDB checkpoints)
- results/*.def (DEF files)
- results/*.spef (SPEF files)
- results/*.v (Verilog netlists - if any)
"""

import sys
from pathlib import Path

# File extensions to REMOVE (not needed for training)
REMOVE_EXTENSIONS = {
    '.gds',      # GDSII layout files
    '.odb',      # OpenDB checkpoint files
    '.def',      # DEF layout files
    '.spef',     # SPEF parasitic files
    '.v.gz',     # Compressed verilog (if any)
}

# Directories to clean (relative to each run directory)
TARGET_DIRS = ['results']

# Files to ALWAYS keep
KEEP_FILES = {
    'run_metadata.json',
    'config.mk',
}

def get_size(path: Path) -> int:
    """Get file size in bytes."""
    try:
        return path.stat().st_size
    except OSError:
        return 0

def format_size(bytes_val: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def clean_aws_report(aws_root: Path, dry_run: bool = False) -> dict:
    """Clean up AWS_Report directory."""
    stats = {
        'removed_files': 0,
        'removed_bytes': 0,
        'kept_files': 0,
        'errors': 0,
        'by_extension': {},
    }

    # Find all run directories (those containing run_metadata.json)
    for metadata_file in aws_root.rglob('run_metadata.json'):
        run_dir = metadata_file.parent

        for target_dir_name in TARGET_DIRS:
            target_dir = run_dir / target_dir_name
            if not target_dir.exists():
                continue

            for file_path in target_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                # Check if we should keep this file
                if file_path.name in KEEP_FILES:
                    stats['kept_files'] += 1
                    continue

                # Check extension
                should_remove = False
                for ext in REMOVE_EXTENSIONS:
                    if file_path.name.endswith(ext):
                        should_remove = True
                        break

                if should_remove:
                    size = get_size(file_path)
                    stats['removed_files'] += 1
                    stats['removed_bytes'] += size
                    ext = file_path.suffix
                    if ext == '.gz' and file_path.name.endswith('.v.gz'):
                        ext = '.v.gz'
                    stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + size

                    if not dry_run:
                        try:
                            file_path.unlink()
                        except OSError as e:
                            print(f"Error removing {file_path}: {e}")
                            stats['errors'] += 1
                    else:
                        print(f"Would remove: {file_path} ({format_size(size)})")
                else:
                    stats['kept_files'] += 1

    return stats

    # Also clean results directories that don't have their own metadata (e.g., duplicate folders)
    # Find all results directories under aws_root
    for results_dir in aws_root.rglob("results"):
        if not results_dir.is_dir():
            continue
        # Skip if already processed (has parent with run_metadata.json)
        parent_has_meta = any(p.name == "run_metadata.json" for p in results_dir.parent.rglob("run_metadata.json") if p.parent == results_dir.parent)
        if parent_has_meta:
            continue  # Already processed via metadata file
        
        for file_path in results_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if we should keep this file
            if file_path.name in KEEP_FILES:
                stats["kept_files"] += 1
                continue

            # Check extension
            should_remove = False
            for ext in REMOVE_EXTENSIONS:
                if file_path.name.endswith(ext):
                    should_remove = True
                    break

            if should_remove:
                size = get_size(file_path)
                stats["removed_files"] += 1
                stats["removed_bytes"] += size
                ext = file_path.suffix
                if ext == ".gz" and file_path.name.endswith(".v.gz"):
                    ext = ".v.gz"
                stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + size

                if not dry_run:
                    try:
                        file_path.unlink()
                    except OSError as e:
                        print(f"Error removing {file_path}: {e}")
                        stats["errors"] += 1
                else:
                    print(f"Would remove: {file_path} ({format_size(size)})")
            else:
                stats["kept_files"] += 1

    return stats

def remove_empty_dirs(aws_root: Path, dry_run: bool = False) -> int:
    """Remove empty directories after cleaning."""
    removed = 0
    # Walk bottom-up to remove empty dirs
    for dirpath in sorted(aws_root.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if dirpath.is_dir():
            try:
                if not any(dirpath.iterdir()):
                    if not dry_run:
                        dirpath.rmdir()
                    removed += 1
            except OSError:
                pass
    return removed

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean up AWS_Report directory for model training")
    parser.add_argument('--aws-root', type=Path, default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report"),
                        help="AWS_Report root directory")
    parser.add_argument('--dry-run', action='store_true',
                        help="Show what would be removed without actually removing")
    parser.add_argument('--remove-empty-dirs', action='store_true',
                        help="Also remove empty directories after cleaning")
    args = parser.parse_args()

    aws_root = args.aws_root
    if not aws_root.exists():
        print(f"AWS_Report not found at {aws_root}")
        sys.exit(1)

    print(f"Cleaning AWS_Report at: {aws_root}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 60)

    stats = clean_aws_report(aws_root, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Files to remove: {stats['removed_files']}")
    print(f"Space freed:     {format_size(stats['removed_bytes'])}")
    print(f"Files kept:      {stats['kept_files']}")
    print(f"Errors:          {stats['errors']}")

    if stats['by_extension']:
        print("\nBy extension:")
        for ext, size in sorted(stats['by_extension'].items(), key=lambda x: -x[1]):
            print(f"  {ext:8s}: {format_size(size)}")

    if args.remove_empty_dirs and not args.dry_run:
        print("\nRemoving empty directories...")
        removed = remove_empty_dirs(aws_root, dry_run=False)
        print(f"Removed {removed} empty directories")

    if args.dry_run:
        print("\nRun without --dry-run to actually perform cleanup.")

if __name__ == '__main__':
    main()