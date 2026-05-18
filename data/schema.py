"""
W1-T02 — Frozen per-chain pkl schema contract.

THIS FILE IS THE SINGLE SOURCE OF TRUTH FOR THE pkl KEY SET.

Rules (per task card, "坑4"):
  * W1-T02a creates every pkl with EXACTLY the keys in SCHEMA_KEYS.
  * atom_coords / atom_mask are written as None placeholders by T02a.
  * W1-T02b is ONLY allowed to fill atom_coords and atom_mask IN PLACE.
    It must not add, remove, or rename any key.
  * validate.py asserts set(pkl.keys()) == SCHEMA_KEYS for every file,
    both after T02a and after a simulated T02b write.

Design notes that are NOT free parameters (they are forced by how RNA3DB
itself parses mmCIF — see rna3db/parser.py):

  * `sequence` is the SEQRES-derived sequence (mmCIF _entity_poly_seq),
    with gaps filled by 'N' and modified residues mapped via the CCD-derived
    modifications cache (fallback 'N'). This is identical to the `sequence`
    field in RNA3DB's own JSON, which is what the >=95% chain-level
    consistency acceptance check compares against.

  * `seq_index` everywhere is 0-based and indexes directly into `sequence`.

  * `resnum_map` maps the PDB *author* numbering of residues that have
    coordinates to that 0-based seq_index. Residues present in SEQRES but
    absent from _atom_site (no coordinates) have NO author number and do
    NOT appear in resnum_map — this is a physical limitation of the data,
    not a design choice. Use `residue_mask` to know which seq positions
    are expected to receive coordinates in T02b.

  * `residue_mask[i] == True`  <=> sequence position i has experimental
    atoms in the structure (i.e. T02b will write coords there).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# THE FROZEN KEY SET. Do not edit without bumping SCHEMA_VERSION and updating
# BOTH W1-T02a and W1-T02b, plus every downstream consumer.
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "1.0.0"

SCHEMA_KEYS = frozenset(
    {
        # --- identity -------------------------------------------------------
        "pdb_id",  # str, lowercase, e.g. "7pkt"
        "chain_id",  # str, PDB author chain id, e.g. "7"
        # --- sequence -------------------------------------------------------
        "sequence",  # str over {A,C,G,U,N} (RNA3DB-canonical)
        # --- scalar metadata ------------------------------------------------
        "resolution",  # float | None (float('inf') -> stored as None)
        "release_date",  # str ISO-8601 "YYYY-MM-DD" | None
        "structure_method",  # str, lowercased exptl.method | None
        "num_models",  # int | None  (see num_models_source)
        "num_models_source",  # str: "rcsb" | "rna3db" | "nmr_assumed" | "unknown"
        "in_rna3db_split",  # str: "train_set" | "valid_set" | "test_set" | None
        # --- coordinate placeholders (T02b fills these IN PLACE) ------------
        "atom_coords",  # None  ->  T02b: np.ndarray [L, A, 3] float32
        "atom_mask",  # None  ->  T02b: np.ndarray [L, A]    bool
        # --- masks / mappings ----------------------------------------------
        "residue_mask",  # list[bool] length L; True = has experimental atoms
        "modified_residues",  # list[ (pos:int, orig:str3, mapped:str1) ]
        "resnum_map",  # dict: "{auth_seqid}{ins_code}" -> seq_index:int
        # --- provenance -----------------------------------------------------
        "schema_version",  # str, == SCHEMA_VERSION at creation time
        "rna3db_tag",  # str, the frozen release tag
        "parse_warnings",  # list[str]; per-chain non-fatal warnings
    }
)

# Keys W1-T02b is permitted to mutate. Everything else is read-only after T02a.
T02B_WRITABLE_KEYS = frozenset({"atom_coords", "atom_mask"})

# Keys that are allowed to hold None after T02a (placeholders / unknowns).
T02A_NULLABLE_KEYS = frozenset(
    {
        "atom_coords",
        "atom_mask",
        "resolution",
        "release_date",
        "structure_method",
        "num_models",
        "in_rna3db_split",
    }
)

# Scalar columns that go into metadata.parquet. Nested structures
# (resnum_map, modified_residues, masks, coords) are deliberately EXCLUDED —
# they live only in the pkl (per task card).
METADATA_SCALAR_COLUMNS = (
    "pdb_id",
    "chain_id",
    "length",  # == len(sequence); derived, not a pkl key
    "resolution",
    "release_date",
    "structure_method",
    "num_models",
    "num_models_source",
    "in_rna3db_split",
    "n_modified_residues",  # derived: len(modified_residues)
    "n_resolved_residues",  # derived: sum(residue_mask)
    "rna3db_tag",
    "schema_version",
)


def assert_schema(d: dict, *, stage: str) -> None:
    """Assert a per-chain dict conforms to the frozen schema.

    Args:
        d: the loaded pkl dict.
        stage: "t02a" (coords must be None) or "t02b" (coords must be set).

    Raises:
        AssertionError: with a precise diff of what is wrong.
    """
    keys = set(d.keys())
    expected = set(SCHEMA_KEYS)
    missing = expected - keys
    extra = keys - expected
    assert not missing, f"[{stage}] pkl missing keys: {sorted(missing)}"
    assert not extra, f"[{stage}] pkl has unexpected keys: {sorted(extra)}"

    if stage == "t02a":
        assert d["atom_coords"] is None, "[t02a] atom_coords must be None placeholder"
        assert d["atom_mask"] is None, "[t02a] atom_mask must be None placeholder"
    elif stage == "t02b":
        assert d["atom_coords"] is not None, "[t02b] atom_coords still None"
        assert d["atom_mask"] is not None, "[t02b] atom_mask still None"
    else:
        raise ValueError(f"unknown stage {stage!r}")

    # Type spot-checks that catch the most damaging silent corruptions.
    assert isinstance(d["sequence"], str) and d["sequence"], (
        "sequence must be non-empty str"
    )
    assert isinstance(d["residue_mask"], list), "residue_mask must be list"
    assert len(d["residue_mask"]) == len(d["sequence"]), (
        f"residue_mask len {len(d['residue_mask'])} != sequence len {len(d['sequence'])}"
    )
    assert isinstance(d["resnum_map"], dict), "resnum_map must be dict"
    assert d["schema_version"] == SCHEMA_VERSION, (
        f"schema_version {d['schema_version']!r} != {SCHEMA_VERSION!r}"
    )
    # Every resnum_map target must be a valid index into sequence.
    L = len(d["sequence"])
    for k, v in d["resnum_map"].items():
        assert isinstance(v, int) and 0 <= v < L, (
            f"resnum_map[{k!r}]={v} out of range [0,{L})"
        )
