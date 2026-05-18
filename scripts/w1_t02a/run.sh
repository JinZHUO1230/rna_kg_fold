#!/usr/bin/env bash
# W1-T02a end-to-end. Run on a host that can reach *.githubusercontent.com
# (your cluster login node). The sandbox that generated this code cannot,
# due to an egress allowlist — that is an environment limit, not a code bug.
set -euo pipefail

# ---- single knob: the frozen RNA3DB tag --------------------------------
TAG="${RNA3DB_TAG:-2026-01-05-full-release}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REL="$ROOT/data/pdb_rna/rna3db_release"
RAW="$ROOT/data/pdb_rna/raw"

# ROOT: for `from data.schema import ...`
# ROOT/rna3db: for `from rna3db.parser import ...`
export PYTHONPATH="$ROOT:$ROOT/rna3db:${PYTHONPATH:-}"

echo "=== [1/5] download + unpack RNA3DB $TAG ==="
python "$SCRIPT_DIR/download_rna3db.py" --tag "$TAG" --out "$REL"

echo "=== [2/5] parse chains -> per-chain pkl skeletons ==="
# The mmcifs tarball unpacks to a dir whose layout has train_set/valid_set/
# test_set somewhere underneath. Point --mmcif-root at that parent.
MMCIF_ROOT="$(dirname "$(find "$REL" -type d -name train_set | head -1)")"
MODS_CACHE="$ROOT/rna3db/tests/test_data/modifications_cache.json"
python "$SCRIPT_DIR/parse_chains.py" \
  --mmcif-root "$MMCIF_ROOT" \
  --raw-out "$RAW" \
  --tag "$TAG" \
  --mods-cache "$MODS_CACHE"

echo "=== [3/5] build metadata.parquet (scalars only) ==="
python "$SCRIPT_DIR/build_metadata.py" --raw "$RAW" --out "$ROOT/data/pdb_rna/metadata.parquet"

echo "=== [4/5] validate (acceptance gate) ==="
# Point --rna3db-json at the release's parse/filter JSON for the hard
# >=95% chain-level consistency check.
RNA3DB_JSON="$(find "$REL" -name 'parse.json' -o -name 'filter.json' | head -1 || true)"
python "$SCRIPT_DIR/validate.py" --raw "$RAW" --sample 10 \
  ${RNA3DB_JSON:+--rna3db-json "$RNA3DB_JSON"}

echo "=== [5/5] EDA notebook ==="
"$ROOT/.venv/bin/jupyter" nbconvert --to notebook --execute "$ROOT/notebooks/w1_t02a_eda.ipynb" \
  --output w1_t02a_eda_executed --ExecutePreprocessor.timeout=600

echo "DONE. Review reports/rna3db_diff_report.md and fill placeholders."
