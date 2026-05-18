# RNA3DB Diff & Provenance Report — W1-T02a

> Fill the `<...>` placeholders after running `run.sh` on a host with
> `*.githubusercontent.com` access. Numbers below are auto-fillable from
> `data/pdb_rna/metadata.parquet`, `parse_failures.tsv`, and the
> `download_manifest.json`.

## 1. Frozen release

| field | value |
|---|---|
| RNA3DB tag (frozen) | `2026-01-05-full-release` |
| Task-card suggested tag | `2025-10-01-incremental-release` |
| Reason for deviation | Card explicitly permits "或更新版". Full (not incremental) release → complete recompute, broader chain coverage for the downstream KG; Rfam 15.0, Infernal 1.1.4. **Action required: confirm no W3-T06 baseline was already frozen on 2025-10-01.** |
| `rna3db-jsons.tar.gz` sha256 | `<from download_manifest.json>` |
| `rna3db-mmcifs.tar.xz` sha256 | `<from download_manifest.json>` |

## 2. Schema contract

- `SCHEMA_KEYS` defined in `src/schema.py`, `SCHEMA_VERSION = 1.0.0`.
- `17` keys, frozen. `atom_coords` / `atom_mask` are the ONLY keys
  W1-T02b may write (`T02B_WRITABLE_KEYS`).
- `validate.py` asserts the key set both at T02a and after a *simulated*
  T02b in-place write — proven on test data: key set unchanged.

## 3. Parse coverage

| metric | value | threshold |
|---|---|---|
| chains in RNA3DB clant list | `<N_total>` | — |
| chains parsed → pkl | `<N_ok>` | — |
| parse success rate | `<pct>%` | ≥ 95% |
| chain-level consistency vs RNA3DB JSON `sequence` | `<pct>%` | ≥ 95% (hard) |

Failure breakdown (from `parse_failures.tsv`): `<paste top reasons>`

> Note: because we reuse `rna3db.parser`, the `sequence` field is
> identical-by-construction to RNA3DB's own JSON `sequence`. Consistency
> < 100% would indicate either a corrupt mmCIF in the release tarball or a
> chain present in the JSON but absent from the mmCIF hierarchy (or vice
> versa) — list any such chains here.

## 4. Key parsing decisions (with rationale)

1. **Parser**: reuse `rna3db.parser.parse_file`, not a fresh gemmi
   implementation. Guarantees the >=95% consistency acceptance by
   construction. gemmi is used as an *independent* second reader to build
   `resnum_map` and to cross-check sequence (silent-bug tripwire).
2. **`sequence` semantics**: SEQRES-derived (`_entity_poly_seq`), gaps
   filled `N`, modified nt mapped via CCD cache (fallback `N`). This is
   forced by RNA3DB, not a free choice.
3. **`resnum_map`**: `"{auth_seqid}{ins_code}" -> 0-based seq_index`,
   anchored to `min(label_seq_id)` so the index space matches RNA3DB and
   every downstream motif consumer. Residues in SEQRES without
   coordinates have no author number and are intentionally absent from
   the map; use `residue_mask` for "will receive coords in T02b".
   **Verified on 1ehz (tRNA-Phe): all 14 modified positions map to the
   literature-documented author numbers with zero offset error.**
4. **`num_models`**: RNA3DB does not expose model count and rewrites
   single-chain mmCIFs with model=1. Policy: non-NMR → `1`
   (`num_models_source="rna3db"`); NMR → `None`
   (`num_models_source="nmr_assumed"`, resolve later if needed). The
   schema KEY is always present; only the VALUE may be None. This avoids
   per-chain RCSB hits (the whole point of using the RNA3DB tarball).

## 5. EDA highlights

See `notebooks/eda.ipynb` (executed copy: `eda_executed.ipynb`).

- length distribution: `<summary>`
- resolution distribution: `<summary>`, `<n>` chains None (NMR/unknown)
- release-year distribution: `<summary>`
- modified-nt top-20: `<paste>`
- chains < 50% resolved: `<n>` (sparse atom_mask expected in T02b)
- chains with `parse_warnings`: `<n>` — `<note any needing human review>`

## 6. Open items for human (30-min sanity check)

- [ ] Confirm tag choice vs any frozen W3-T06 baseline.
- [ ] Spot-check 5 random chains' resnum_map vs PDB website numbering
      (1ehz already verified by automated biology check).
- [ ] Decide whether `num_models=None` for NMR chains is acceptable for
      W1-T03/T04 or must be resolved now.
