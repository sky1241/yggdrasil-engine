"""
OpenAlex Smart Sync — Downloads/updates the local snapshot on D:/openalex/data/

Strategy:
  1. Finish the bulk download if incomplete
  2. Sync all new incremental folders
  3. If a NEW bulk appears (different date), swap old -> new
  4. Skip entities that rarely change (concepts, topics, etc.) unless --full

Usage:
  python openalex_sync.py              # sync works only (default)
  python openalex_sync.py --full       # sync everything (works + authors + all)
  python openalex_sync.py --dry-run    # show what would be downloaded
  python openalex_sync.py --check      # just show status, download nothing

Designed to be run weekly via Windows Task Scheduler.
"""

import subprocess
import sys
import os
import json
import argparse
from datetime import datetime

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
S3_BASE = "s3://openalex/data"
LOCAL_BASE = r"D:\openalex\data"
LOG_FILE = r"D:\openalex\sync.log"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_aws(args, dry_run=False):
    """Run an AWS CLI command. Returns (returncode, stdout)."""
    cmd = [AWS] + args + ["--no-sign-request"]
    if dry_run:
        cmd.append("--dryrun")
    log(f"  CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return result.returncode, result.stdout, result.stderr


def list_s3_folders(entity):
    """List all updated_date= folders on S3 for an entity."""
    rc, stdout, stderr = run_aws(["s3", "ls", f"{S3_BASE}/{entity}/"])
    folders = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if "PRE updated_date=" in line:
            folder = line.replace("PRE ", "").strip().rstrip("/")
            folders.append(folder)
    return sorted(folders)


def list_local_folders(entity):
    """List all updated_date= folders locally."""
    path = os.path.join(LOCAL_BASE, entity)
    if not os.path.exists(path):
        return []
    return sorted([
        d for d in os.listdir(path)
        if d.startswith("updated_date=") and os.path.isdir(os.path.join(path, d))
    ])


def find_bulk_folder(entity):
    """Find the bulk folder (the one with the most files) locally."""
    path = os.path.join(LOCAL_BASE, entity)
    if not os.path.exists(path):
        return None, 0

    best_folder = None
    best_count = 0
    for d in os.listdir(path):
        if not d.startswith("updated_date="):
            continue
        full = os.path.join(path, d)
        if os.path.isdir(full):
            count = len(os.listdir(full))
            if count > best_count:
                best_count = count
                best_folder = d
    return best_folder, best_count


def s3_folder_file_count(entity, folder):
    """Count files in an S3 folder."""
    rc, stdout, stderr = run_aws(["s3", "ls", f"{S3_BASE}/{entity}/{folder}/"])
    return len([l for l in stdout.strip().split("\n") if l.strip()])


def sync_entity(entity, dry_run=False):
    """Sync one entity (e.g., 'works', 'authors')."""
    log(f"\n{'='*60}")
    log(f"Syncing: {entity}")
    log(f"{'='*60}")

    s3_folders = list_s3_folders(entity)
    local_folders = list_local_folders(entity)

    log(f"  S3: {len(s3_folders)} folders")
    log(f"  Local: {len(local_folders)} folders")

    missing = [f for f in s3_folders if f not in local_folders]
    log(f"  Missing locally: {len(missing)} folders")

    # Sync the whole entity directory (aws s3 sync handles the diff)
    s3_path = f"{S3_BASE}/{entity}/"
    local_path = os.path.join(LOCAL_BASE, entity) + os.sep

    log(f"  Running s3 sync...")
    rc, stdout, stderr = run_aws(
        ["s3", "sync", s3_path, local_path, "--size-only"],
        dry_run=dry_run
    )

    if rc == 0:
        # Count what was downloaded
        dl_lines = [l for l in stdout.split("\n") if "download:" in l]
        log(f"  Downloaded: {len(dl_lines)} files")
    else:
        log(f"  ERROR (rc={rc}): {stderr[:500]}")

    return rc


def check_status():
    """Show current status without downloading anything."""
    entities = ["works", "authors", "concepts", "topics", "sources",
                "institutions", "publishers", "funders", "domains",
                "fields", "subfields"]

    print(f"\n{'Entity':<20} {'Local':<10} {'S3':<10} {'Missing':<10} {'Bulk':<30}")
    print("-" * 80)

    for entity in entities:
        local = list_local_folders(entity)
        s3 = list_s3_folders(entity)
        missing = len(s3) - len(local) if len(s3) > len(local) else 0

        bulk_folder, bulk_count = find_bulk_folder(entity)
        bulk_info = f"{bulk_folder} ({bulk_count} files)" if bulk_folder else "none"

        print(f"{entity:<20} {len(local):<10} {len(s3):<10} {missing:<10} {bulk_info}")

    # Disk space
    import shutil
    usage = shutil.disk_usage("D:\\")
    free_gb = usage.free / (1024**3)
    used_gb = usage.used / (1024**3)
    total_gb = usage.total / (1024**3)
    print(f"\nDisk D: {used_gb:.0f} GB used / {total_gb:.0f} GB total / {free_gb:.0f} GB free")


def main():
    parser = argparse.ArgumentParser(description="OpenAlex Smart Sync")
    parser.add_argument("--full", action="store_true",
                        help="Sync all entities (not just works)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading")
    parser.add_argument("--check", action="store_true",
                        help="Show status only, no downloads")
    parser.add_argument("--entity", type=str, default=None,
                        help="Sync a specific entity (e.g., 'authors')")
    args = parser.parse_args()

    if args.check:
        check_status()
        return

    log(f"\n{'#'*60}")
    log(f"OpenAlex Sync started — {'DRY RUN' if args.dry_run else 'LIVE'}")
    log(f"{'#'*60}")

    if args.entity:
        entities = [args.entity]
    elif args.full:
        entities = ["works", "authors", "concepts", "topics", "sources",
                     "institutions", "publishers", "funders", "domains",
                     "fields", "subfields"]
    else:
        entities = ["works"]

    for entity in entities:
        sync_entity(entity, dry_run=args.dry_run)

    # Also sync the manifest
    for entity in entities:
        log(f"Syncing manifest for {entity}...")
        run_aws([
            "s3", "cp",
            f"{S3_BASE}/{entity}/manifest",
            os.path.join(LOCAL_BASE, entity, "manifest"),
        ], dry_run=args.dry_run)

    log("\nSync complete.")


if __name__ == "__main__":
    main()
