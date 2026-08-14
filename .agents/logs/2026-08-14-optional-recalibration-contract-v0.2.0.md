# SpectroCube: optional recalibration contract v0.2.0 — 2026-08-14

SpectroCube 0.2.0 was prepared on `main` from clean base
`c46b0c4621ec8d56d7d7209d122b571fb109405e`. This log is part of the single
release commit; its immutable hash is recorded in the Echelle workflow handoff
after that commit is created.

## Decisions

- `detector_pixel` is an optional real numeric coordinate aligned exactly to
  `wavelength`. Its required attributes are `units = "pixel"`, a non-empty
  `detector_axis`, a non-empty `reference_frame`, and a non-negative integer
  `index_origin`.
- `echelle_order` is an optional non-negative integer coordinate aligned
  exactly to `wavelength`.
- `wavelength_polynomials_json` is an optional strict JSON global attribute
  with schema `spectrocube.wavelength-polynomials/v1`, descending-power
  coefficients, detector-pixel input in pixels, wavelength output in nm, and
  unique non-negative order identifiers.
- `applied_absolute_calibration_factor` is an optional finite, strictly
  positive real data variable aligned exactly to `wavelength`. It requires
  non-empty `units` and `source_units`, the exact application string
  `stored_intensity = source_signal * applied_absolute_calibration_factor`,
  and an absolute cube.
- The four representations are independently optional. The only bundle-level
  relationship is exact order-ID agreement when `echelle_order` and the
  polynomial JSON are both present.
- Validation reports errors without mutation. `from_dataset`, NetCDF
  save/load, and package APIs preserve unknown legal attributes, coordinates,
  and data variables.
- No lockfile was introduced: this neutral library follows the lower-bound
  dependency convention and declares reproducible build/test tools in extras.

## Changed

- Added strict validation, public names/constants, explicit `ds` typing, and
  the 0.2.0 runtime version.
- Added focused legacy, partial-presence, invalid-input, cross-reference,
  preservation, NetCDF, installed-resource, and version-synchronization tests.
- Synchronized the root, documentation, and installed-package specification;
  added a public changelog and complete user/consumer documentation.
- Added `AGENTS.md`, the small `.agents` operational-memory surface, external
  environment rules, release gates, and an sdist manifest.
- Made the Unicode CLI status output robust on legacy Windows console
  encodings; the regression test launches the validator with CP-1252.

## Verification

All generated outputs used an external scratch tree, not the repository.

- Existing Python 3.14.5 environment, source checkout:
  `python -m pytest --basetemp <external>/pytest-current` -> 87 passed before
  the CLI regression and 88 passed after it; `ruff check --no-cache src tests`
  -> passed; scoped `black --check` -> passed.
- Fresh plain Python 3.12.13 venv, copied final candidate:
  `python -m pytest --basetemp <external>/pytest-py312-final` -> 87 passed at
  that checkpoint; Ruff and scoped Black -> passed; `pyright --pythonpath
  <venv>/Scripts/python.exe src` -> 0 errors; `python -m mypy --cache-dir
  <external>/mypy src` -> no issues;
  `python -m mkdocs build --strict --site-dir <external>/site-py312-final` ->
  passed. The final CLI-only addition was covered by the later 3.14 run.
- Fresh plain Python 3.14.5 venv, copied final candidate:
  `python -m pytest --basetemp <external>/pytest-py314-cli-final` -> 88 passed;
  Ruff and scoped Black -> passed; Pyright -> 0 errors; mypy -> no issues. The
  preceding strict MkDocs build passed under the same environment.
- `python -m build --no-isolation --outdir <external>/release-artifacts-final
  .` -> wheel and sdist built; `python -m twine check <artifacts>` -> both
  passed.
- Archive inspection -> installed `SPEC.md`, installed `CHANGELOG.md`, root
  specification/changelog, authored docs, and entry-point metadata present;
  caches, generated sites, and build debris absent.
- Fresh plain Python 3.14.5 venv installed the built wheel. Installed
  import/version/resource, both CLI help commands, both validators, CLI info,
  plain-cube validation/NetCDF round trip, and complete optional-contract
  validation/extras/NetCDF round trip all passed.

Artifacts:

| File | Bytes | SHA-256 |
|---|---:|---|
| `spectrocube-0.2.0-py3-none-any.whl` | 19,309 | `67df746116e04a15ae50293f217837c585c5c9c394e1574f53d83ceca12edc45` |
| `spectrocube-0.2.0.tar.gz` | 34,389 | `f48e3a191d636f38f63c8ba9f200066de735514fdc92bb034466f344c35082a4` |

## Risks and limitations

- Packet 7 defines and validates the neutral storage contract only. It does
  not populate fields, select calibration epochs, maintain a snapshot
  registry, or implement post-hoc recalibration.
- Current NetCDF4 wheels emit a non-fatal NumPy ABI runtime warning on first
  import and xarray emits NumPy 2.5 assignment deprecations during NetCDF
  tests. Both clean Python 3.12 and 3.14 runs completed all round trips.
- Release artifacts remain local; no tag or push was made.

## Next

Packet 8 belongs to `echelle_spectra`: populate all aligned fields with the
same wavelength reorder/mask, retain raw-detector pixel meaning, serialize its
existing descending-power per-order fits, and record the factor that maps the
pre-calibration signal units to the stored absolute intensity.

provider usage: unavailable; child-agent count: 0.

agent: codex gpt-5
