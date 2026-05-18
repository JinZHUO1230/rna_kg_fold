"""
W1-T02a — Download & unpack a fixed RNA3DB release.

Fetches the two assets we need:
  * rna3db-mmcifs.tar.xz  -> hierarchical single-chain mmCIFs split into
                             train_set / valid_set / test_set.
                             This is what solves "坑1" (protein-complex chain
                             separation) for free, and removes the per-chain
                             RCSB download (API rate-limit risk).
  * rna3db-jsons.tar.gz   -> authoritative scalar metadata + the split JSON
                             (source of `in_rna3db_split`).

NOTE on the 403 you may see in a sandbox: GitHub release downloads 302-redirect
to release-assets.githubusercontent.com. If your environment whitelists only
github.com, the redirect target is blocked. Run this on a host that can reach
*.githubusercontent.com (your cluster login node is fine).

Usage:
    python -m src.download_rna3db --tag 2026-01-05-full-release \\
        --out data/pdb_rna/rna3db_release
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://github.com/marcellszi/rna3db/releases/download"

# Assets we pull. mmcifs is the big one (LZMA .xz).
ASSETS = ("rna3db-jsons.tar.gz", "rna3db-mmcifs.tar.xz")


def _download(url: str, dest: Path, *, max_retries: int = 6) -> None:
    """Stream a URL to disk with exponential backoff.

    Backoff schedule: 2,4,8,16,32,64 s. Honours HTTP Retry-After when present.
    """
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {dest.name} already present ({dest.stat().st_size} B)")
        return

    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rna3db-w1t02a"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length", 0))
                done = 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = 100 * done / total
                        print(
                            f"\r  {dest.name}: {done >> 20} / {total >> 20} MiB "
                            f"({pct:5.1f}%)",
                            end="",
                            file=sys.stderr,
                        )
            print(file=sys.stderr)
            tmp.replace(dest)
            return
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            wait = 2**attempt
            ra = getattr(getattr(e, "headers", None), "get", lambda *_: None)(
                "Retry-After"
            )
            if ra and str(ra).isdigit():
                wait = int(ra)
            print(
                f"  [retry {attempt}/{max_retries}] {dest.name}: {e} "
                f"-> sleeping {wait}s",
                file=sys.stderr,
            )
            if tmp.exists():
                tmp.unlink()
            if attempt == max_retries:
                raise
            time.sleep(wait)


def _safe_extract(tar_path: Path, out_dir: Path) -> None:
    """Extract a tarball, rejecting path traversal entries."""
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"  [skip] {out_dir.name} already extracted")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = "r:xz" if tar_path.suffix == ".xz" else "r:gz"
    with tarfile.open(tar_path, mode) as t:  # type: ignore[call-overload]
        for m in t.getmembers():
            p = (out_dir / m.name).resolve()
            if not str(p).startswith(str(out_dir.resolve())):
                raise RuntimeError(f"unsafe tar member: {m.name}")
        t.extractall(out_dir)
    print(f"  [ok] extracted {tar_path.name} -> {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tag", required=True, help="RNA3DB release tag, e.g. 2026-01-05-full-release"
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--assets", nargs="+", default=list(ASSETS))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"rna3db_tag": args.tag, "assets": {}}

    for asset in args.assets:
        url = f"{BASE}/{args.tag}/{asset}"
        dest = args.out / asset
        print(f"[get] {url}")
        _download(url, dest)
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        manifest["assets"][asset] = {
            "sha256": h.hexdigest(),
            "bytes": dest.stat().st_size,
        }
        _safe_extract(dest, args.out / asset.split(".")[0])

    # Record the tag + checksums into metadata provenance.
    (args.out / "download_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] manifest -> {args.out / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
