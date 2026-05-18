"""
W1-T02a — Acceptance validation.

Checks (mapped to the task card's 验收标准):
  1. Every pkl has EXACTLY the frozen SCHEMA_KEYS, atom_coords/atom_mask=None.
  2. Random deserialization spot-check (default 10): loads, structurally valid.
  3. Simulated W1-T02b in-place write: set atom_coords/atom_mask to dummy
     arrays, re-assert key set is UNCHANGED (proves "坑4": b is pure fill).
  4. resnum_map range correctness for every file.
  5. Optional: chain-level consistency vs RNA3DB JSON (sequence equality).

Exit code is non-zero if any hard check fails (for CI / run.sh gating).
"""

from __future__ import annotations

import argparse
import pickle
import random
import sys
from pathlib import Path

# locate repo root (.../rna_kg_fold) so we can import data/schema.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from data.schema import (  # noqa: E402
    SCHEMA_KEYS,
    T02B_WRITABLE_KEYS,
    assert_schema,
)


def _simulate_t02b(d: dict) -> dict:
    """Mimic what W1-T02b will do: fill ONLY the two coord keys in place."""
    import numpy as np

    L = len(d["sequence"])
    A = 3  # arbitrary atom count for the simulation
    before = set(d.keys())
    d["atom_coords"] = np.zeros((L, A, 3), dtype="float32")
    d["atom_mask"] = np.zeros((L, A), dtype=bool)
    after = set(d.keys())
    assert before == after, (
        f"T02b simulation changed key set: added {after - before}, "
        f"removed {before - after}"
    )
    mutated = {k for k in d if k in ("atom_coords", "atom_mask")}
    assert mutated <= T02B_WRITABLE_KEYS
    assert_schema(d, stage="t02b")
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument(
        "--rna3db-json",
        type=Path,
        default=None,
        help="optional parse/filter/split JSON for consistency check",
    )
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    pkls = sorted(args.raw.glob("*.pkl"))
    if not pkls:
        print("FAIL: no pkl files found")
        sys.exit(1)
    print(f"[validate] {len(pkls)} pkl files")

    hard_fail = 0

    # --- Check 1: every file conforms to frozen schema (stage t02a) --------
    bad = []
    for p in pkls:
        try:
            with open(p, "rb") as f:
                d = pickle.load(f)
            assert_schema(d, stage="t02a")
        except Exception as e:  # noqa: BLE001
            bad.append((p.name, str(e)))
    if bad:
        hard_fail += 1
        print(f"  [FAIL] {len(bad)} files violate schema; first 5:")
        for n, msg in bad[:5]:
            print(f"    {n}: {msg}")
    else:
        print(
            f"  [PASS] all {len(pkls)} files match frozen SCHEMA_KEYS "
            f"({len(SCHEMA_KEYS)} keys), coords=None"
        )

    # --- Check 2+3: random deserialization + simulated T02b in-place ------
    random.seed(args.seed)
    sample = random.sample(pkls, min(args.sample, len(pkls)))
    t02b_bad = []
    for p in sample:
        try:
            with open(p, "rb") as f:
                d = pickle.load(f)
            _simulate_t02b(d)
        except Exception as e:  # noqa: BLE001
            t02b_bad.append((p.name, str(e)))
    if t02b_bad:
        hard_fail += 1
        print(f"  [FAIL] simulated T02b broke {len(t02b_bad)} files:")
        for n, msg in t02b_bad[:5]:
            print(f"    {n}: {msg}")
    else:
        print(
            f"  [PASS] {len(sample)} sampled pkls survive simulated "
            f"T02b in-place write (key set unchanged)"
        )

    # --- Check 4: resnum_map range correctness ---------------------------
    rng_bad = []
    for p in pkls:
        with open(p, "rb") as f:
            d = pickle.load(f)
        L = len(d["sequence"])
        for k, v in d["resnum_map"].items():
            if not (isinstance(v, int) and 0 <= v < L):
                rng_bad.append((p.name, k, v, L))
        # residue_mask must be exactly the set of resnum_map targets
        masked = {i for i, b in enumerate(d["residue_mask"]) if b}
        mapped = set(d["resnum_map"].values())
        if masked != mapped:
            rng_bad.append((p.name, "mask!=map", len(masked ^ mapped), L))
    if rng_bad:
        hard_fail += 1
        print(f"  [FAIL] resnum_map issues: {len(rng_bad)}; first 5: {rng_bad[:5]}")
    else:
        print(
            "  [PASS] resnum_map in-range & consistent with residue_mask for all files"
        )

    # --- Check 5: chain-level consistency vs RNA3DB JSON (optional) -------
    if args.rna3db_json and args.rna3db_json.exists():
        import json

        def _iter_chains(obj):
            # parse/filter JSON is flat; cluster/split JSON is nested.
            if all(isinstance(v, dict) and "sequence" in v for v in obj.values()):
                yield from obj.items()
            else:
                for comp in obj.values():
                    for clus in comp.values():
                        yield from clus.items()

        ref = dict(_iter_chains(json.load(open(args.rna3db_json))))
        total = match = 0
        for p in pkls:
            with open(p, "rb") as f:
                d = pickle.load(f)
            key = f"{d['pdb_id']}_{d['chain_id']}"
            if key in ref:
                total += 1
                if ref[key].get("sequence") == d["sequence"]:
                    match += 1
        if total:
            pct = 100 * match / total
            status = "PASS" if pct >= 95 else "FAIL"
            if pct < 95:
                hard_fail += 1
            print(
                f"  [{status}] RNA3DB chain-level consistency: "
                f"{match}/{total} = {pct:.2f}% (threshold 95%)"
            )
        else:
            print("  [WARN] no overlapping chains with provided JSON")
    else:
        print("  [skip] no RNA3DB JSON provided for consistency check")

    print()
    if hard_fail:
        print(f"VALIDATION FAILED ({hard_fail} hard checks failed)")
        sys.exit(1)
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
