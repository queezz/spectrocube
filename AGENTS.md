# AGENTS.md

SpectroCube is the instrument-neutral xarray/NetCDF container between spectrum
writers such as `echelle_spectra` and downstream readers such as SpectroView
and Fulcher extraction. Instrument calibration and processing stay in their
own repositories.

## Environment

Use the external environment at `~/.venvs/spectrocube`; never create a virtual
environment, cache, build tree, or generated site inside this Dropbox checkout.

Windows:

```powershell
$spectrocubeScratch = Join-Path ([System.IO.Path]::GetTempPath()) ("spectrocube-gates-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $spectrocubeScratch | Out-Null
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m pytest --basetemp (Join-Path $spectrocubeScratch "pytest")
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m ruff check --no-cache src tests
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m black --check src/spectrocube/__init__.py src/spectrocube/cli.py src/spectrocube/core.py tests/conftest.py tests/test_cli.py tests/test_optional_recalibration_contract.py tests/test_package_contract.py
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\pyright.exe" --pythonpath "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" src
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m mypy --cache-dir (Join-Path $spectrocubeScratch "mypy") src
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m mkdocs build --strict --site-dir (Join-Path $spectrocubeScratch "site")
```

macOS/Linux:

```bash
spectrocube_scratch="$(mktemp -d)"
~/.venvs/spectrocube/bin/python -m pytest --basetemp "$spectrocube_scratch/pytest"
~/.venvs/spectrocube/bin/python -m ruff check --no-cache src tests
~/.venvs/spectrocube/bin/python -m black --check src/spectrocube/__init__.py src/spectrocube/cli.py src/spectrocube/core.py tests/conftest.py tests/test_cli.py tests/test_optional_recalibration_contract.py tests/test_package_contract.py
~/.venvs/spectrocube/bin/pyright --pythonpath ~/.venvs/spectrocube/bin/python src
~/.venvs/spectrocube/bin/python -m mypy --cache-dir "$spectrocube_scratch/mypy" src
~/.venvs/spectrocube/bin/python -m mkdocs build --strict --site-dir "$spectrocube_scratch/site"
```

The pytest configuration disables its repository cache and chooses a unique
OS-local temporary root when `--basetemp` is not supplied. Release work still
uses a named external scratch root for builds, artifacts, and clean installs.

## Read first

1. `.agents/README.md`
2. `.agents/rules.md`
3. `.agents/commit-culture.md`
4. `.agents/directions.md`
5. The newest relevant entry in `.agents/logs/`
6. `SPEC.md`, then the implementation and tests relevant to the change
7. Fleet's `RULES-BRIEF.md` and the relevant sections of `RULES.md` / `MAP.md`

## Invariants

- Keep the format and package instrument-neutral. Optional instrument metadata
  never becomes a mandatory execution mode or dependency.
- Preserve arbitrary legal xarray coordinates, data variables, and NetCDF-safe
  attributes without silent normalization, reordering, or deletion.
- Validate optional contract fields when present while keeping plain legacy
  cubes valid.
- Keep `pyproject.toml`, runtime `__version__`, `SPEC.md`, installed
  resources, documentation, and the public `CHANGELOG.md` synchronized.
- Keep build artifacts and release scratch outside the repository.
- Do not push or tag unless queezz explicitly asks.

Write an evidence-rich handoff in `.agents/logs/` for each meaningful release
or contract change.
