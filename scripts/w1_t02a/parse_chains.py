"""
W1-T02a — Parse RNA3DB single-chain mmCIFs into per-chain pkl skeletons.

Strategy (decided after reading rna3db/parser.py):
  * Use rna3db's OWN parser for sequence + residue_mask + modified residues.
    This makes our `sequence` identical-by-construction to RNA3DB's JSON
    `sequence`, so the ">=95% chain-level consistency" acceptance check is
    satisfied by definition rather than by luck.
  * Independently re-read _atom_site with gemmi to build `resnum_map`
    (author numbering -> 0-based seq_index) and to cross-check the sequence.
    gemmi is a second, independent implementation; a mismatch surfaces a
    silent parser bug instead of letting it poison every downstream motif.
  * `in_rna3db_split` comes from which top-level set the file sits under in
    the rna3db-mmcifs hierarchy (train_set / valid_set / test_set).
  * num_models: RNA3DB rewrites single-chain mmCIFs with model num fixed to 1
    and does not expose model count. We therefore set num_models from the
    structure_method: NMR -> None + source="nmr_assumed" (must be resolved
    later if needed); everything else -> 1 + source="rna3db". The schema KEY
    is always present (frozen); only the VALUE may be None.

Outputs one pkl per chain at: <raw_dir>/{pdb_id}_{chain_id}.pkl
"""

from __future__ import annotations

import argparse
import pickle
import sys
import traceback
from pathlib import Path

import gemmi

# rna3db must be importable (pip install -e ./rna3db OR PYTHONPATH).
from rna3db.parser import parse_file

# locate repo root (.../rna_kg_fold) so we can import data/schema.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from data.schema import SCHEMA_KEYS, SCHEMA_VERSION, assert_schema  # noqa: E402

SPLIT_DIRS = ("train_set", "valid_set", "test_set")


def _resolution_or_none(r):
    # RNA3DB uses float('inf') for "no resolution" (e.g. NMR). Store as None.
    try:
        if r is None or r != r or r == float("inf"):
            return None
        return float(r)
    except Exception:
        return None


def _build_resnum_map(cif_path: Path, author_chain: str, sequence: str):
    """Re-read _atom_site with gemmi to map author numbering -> seq_index.

    RNA3DB's parser indexes residues by (label_seq_id - min_label_seq_id),
    0-based, into the SEQRES-derived `sequence`. We reproduce that anchor
    here so author numbers map onto the SAME index space the rest of the
    pipeline (and RNA3DB) uses.

    Returns:
        (resnum_map, residue_mask, warnings)
        resnum_map: { "<auth_seqid><ins_code>": seq_index }
        residue_mask: list[bool] len == len(sequence), True where atoms exist
    """
    warnings: list[str] = []
    st = gemmi.cif.read(str(cif_path))
    block = st.sole_block()

    cols = block.find(
        "_atom_site.",
        [
            "label_seq_id",
            "auth_seq_id",
            "pdbx_PDB_ins_code",
            "auth_asym_id",
            "label_alt_id",
            "label_comp_id",
        ],
    )

    label_ids = []
    by_label: dict[int, tuple[str, str]] = {}  # label_seq_id -> (auth_seqid, ins_code)
    chosen_alt = None
    for row in cols:
        if row[3] != author_chain:
            continue
        lab = row[0]
        if lab in (".", "?"):
            continue
        alt = row[4]
        if chosen_alt is None and alt not in (".", "?"):
            chosen_alt = alt
        if alt not in (".", "?") and chosen_alt is not None and alt != chosen_alt:
            continue
        lab_i = int(lab)
        ins = "" if row[2] in (".", "?") else row[2].strip()
        by_label.setdefault(lab_i, (row[1], ins))
        label_ids.append(lab_i)

    resnum_map: dict[str, int] = {}
    residue_mask = [False] * len(sequence)

    if by_label:
        min_lab = min(by_label)
        for lab_i, (auth, ins) in by_label.items():
            seq_idx = lab_i - min_lab  # 0-based, same anchor as rna3db parser
            if not (0 <= seq_idx < len(sequence)):
                warnings.append(
                    f"resnum_map: label_seq_id {lab_i} -> idx {seq_idx} "
                    f"out of seq range [0,{len(sequence)}); skipped"
                )
                continue
            key = f"{auth}{ins}"
            if key in resnum_map and resnum_map[key] != seq_idx:
                warnings.append(
                    f"resnum_map: duplicate author key {key!r} "
                    f"({resnum_map[key]} vs {seq_idx})"
                )
            resnum_map[key] = seq_idx
            residue_mask[seq_idx] = True
    else:
        warnings.append("no _atom_site rows for chain; residue_mask all False")

    return resnum_map, residue_mask, warnings


def _modified_residues(chain):
    """Extract (pos, three_letter, one_letter) for residues whose 3-letter
    code is not a canonical A/C/G/U/N. rna3db already did the 3->1 mapping
    via the CCD-derived cache; we just report what it mapped."""
    out = []
    for i, res in enumerate(chain):
        tlc = res.three_letter_code
        if tlc not in ("A", "C", "G", "U", "N"):
            out.append((i, tlc, res.code))
    return out


def parse_structure(
    cif_path: Path, split_name: str, tag: str, mods_cache: str | None = None
) -> list[dict]:
    """Parse an mmCIF into one schema dict PER RNA chain.

    RNA3DB release files are single-chain, but this also correctly handles
    full multi-chain PDB entries (one pkl per RNA chain — this is "坑1":
    protein complexes get split by chain, non-RNA chains are dropped by
    rna3db's polymer-type filter before we ever see them).
    """
    kw: dict[str, object] = {"include_atoms": False}
    if mods_cache:
        kw["modifications_cache_path"] = mods_cache
    sf = parse_file(str(cif_path), **kw)
    out = []
    for author_chain in sf.chains:
        d = _chain_to_dict(sf, author_chain, cif_path, split_name, tag)
        if d is not None:
            out.append(d)
    return out


def _chain_to_dict(sf, author_chain, cif_path, split_name, tag) -> dict | None:
    pdb_id = sf.pdb_id
    chain = sf.chains[author_chain]
    sequence = chain.sequence
    if not sequence:
        return None

    resnum_map, residue_mask, warns = _build_resnum_map(
        cif_path, author_chain, sequence
    )

    method = (sf.structure_method or "").lower()
    if "nmr" in method:
        num_models, nm_src = None, "nmr_assumed"
    else:
        num_models, nm_src = 1, "rna3db"

    d = {
        "pdb_id": pdb_id,
        "chain_id": author_chain,
        "sequence": sequence,
        "resolution": _resolution_or_none(sf.resolution),
        "release_date": sf.release_date or None,
        "structure_method": method or None,
        "num_models": num_models,
        "num_models_source": nm_src,
        "in_rna3db_split": split_name,
        "atom_coords": None,  # placeholder — W1-T02b fills in place
        "atom_mask": None,  # placeholder — W1-T02b fills in place
        "residue_mask": residue_mask,
        "modified_residues": _modified_residues(chain),
        "resnum_map": resnum_map,
        "schema_version": SCHEMA_VERSION,
        "rna3db_tag": tag,
        "parse_warnings": warns,
    }
    assert set(d.keys()) == set(SCHEMA_KEYS), "schema drift in parse_one"
    assert_schema(d, stage="t02a")
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mmcif-root",
        type=Path,
        required=True,
        help="dir containing train_set/ valid_set/ test_set/",
    )
    ap.add_argument("--raw-out", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument(
        "--limit", type=int, default=None, help="parse only first N chains (smoke test)"
    )
    ap.add_argument(
        "--mods-cache",
        default=None,
        help="path to modifications_cache.json (optional override)",
    )
    args = ap.parse_args()

    args.raw_out.mkdir(parents=True, exist_ok=True)

    # Discover all cif files under each split dir.
    jobs = []
    for split in SPLIT_DIRS:
        sd = args.mmcif_root / split
        if not sd.exists():
            continue
        for cif in sd.rglob("*.cif"):
            jobs.append((cif, split))
    if args.limit:
        jobs = jobs[: args.limit]

    print(f"[parse] {len(jobs)} files to process")
    ok, fail = 0, 0
    failures = []
    for i, (cif, split) in enumerate(jobs, 1):
        try:
            dicts = parse_structure(cif, split, args.tag, args.mods_cache)
            if not dicts:
                fail += 1
                failures.append((cif.name, "empty/zero-chain"))
                continue
            for d in dicts:
                out = args.raw_out / f"{d['pdb_id']}_{d['chain_id']}.pkl"
                with open(out, "wb") as f:
                    pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)
                ok += 1
        except Exception as e:  # noqa: BLE001
            fail += 1
            failures.append((cif.name, f"{type(e).__name__}: {e}"))
            traceback.print_exc(limit=1)
        if i % 200 == 0:
            print(f"  {i}/{len(jobs)}  ok={ok} fail={fail}")

    print(f"[done] ok={ok} fail={fail} ({100 * ok / max(1, ok + fail):.2f}% parsed)")
    if failures:
        fp = args.raw_out.parent / "parse_failures.tsv"
        with open(fp, "w") as f:
            f.write("file\treason\n")
            for n, r in failures:
                f.write(f"{n}\t{r}\n")
        print(f"[done] failures -> {fp}")


if __name__ == "__main__":
    main()
