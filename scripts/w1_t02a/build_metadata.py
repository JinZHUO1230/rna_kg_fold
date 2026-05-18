"""
W1-T02a — Build metadata.parquet (scalar index columns ONLY).

Per task card: nested structures (resnum_map, modified_residues, masks,
coords) stay in the pkl. The parquet holds only flat scalars for fast
filtering / EDA / downstream join keys.
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import pandas as pd

# locate repo root (.../rna_kg_fold) so we can import data/schema.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from data.schema import METADATA_SCALAR_COLUMNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = []
    for p in sorted(args.raw.glob("*.pkl")):
        with open(p, "rb") as f:
            d = pickle.load(f)
        rows.append(
            {
                "pdb_id": d["pdb_id"],
                "chain_id": d["chain_id"],
                "length": len(d["sequence"]),
                "resolution": d["resolution"],
                "release_date": d["release_date"],
                "structure_method": d["structure_method"],
                "num_models": d["num_models"],
                "num_models_source": d["num_models_source"],
                "in_rna3db_split": d["in_rna3db_split"],
                "n_modified_residues": len(d["modified_residues"]),
                "n_resolved_residues": sum(d["residue_mask"]),
                "rna3db_tag": d["rna3db_tag"],
                "schema_version": d["schema_version"],
            }
        )

    df = pd.DataFrame(rows, columns=list(METADATA_SCALAR_COLUMNS))
    # Stable ordering = reproducible artifact.
    df = df.sort_values(["pdb_id", "chain_id"]).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"[metadata] {len(df)} rows -> {args.out}")
    print(df.dtypes.to_string())
    print(df.head(10).to_string())


if __name__ == "__main__":
    main()
