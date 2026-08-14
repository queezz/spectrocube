# SpectroCube rules

Always-tense rules for the neutral container contract.

## Ownership

- SpectroCube owns structure, validation, serialization, and neutral
  vocabulary.
- Instrument packages own extraction, calibration algorithms, field
  population, provenance registries, and recalibration commands.
- Readers may consume optional fields but do not make them mandatory for
  unrelated writers.

## Data contract

- `wavelength` and every canonical aligned auxiliary field use the same
  `wavelength` dimension.
- Optional fields validate independently. Only metadata indispensable to the
  field's own interpretation is required.
- Structured NetCDF attributes use explicitly versioned, strict JSON strings.
- Validation reports clear errors and does not mutate a Dataset.
- Conversion and save/load preserve unknown legal extras exactly; no validator
  silently sorts, coerces, fills, or drops user data.

## Portability

- Runtime code supports every Python declared in `pyproject.toml`.
- Installed distributions carry the current specification and public
  changelog as package resources.
- Environments, caches, build trees, generated sites, and test files stay
  outside Git and, for release work, outside Dropbox.
- Lab may launch convenience commands, but documented installation and gates
  use plain Python and the external venv directly.

## Releases

- Patch: compatible corrections to implementation or prose.
- Minor: a new optional format capability or public package surface.
- Major: an intentional incompatible format or API contract.
- A release synchronizes every public version surface and changelog entry in
  the same cohesive commit.
- Git tags and pushes are queezz's actions only.
