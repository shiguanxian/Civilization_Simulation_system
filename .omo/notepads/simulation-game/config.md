# Config Module Learnings

## C1 + C2 Implementation (2026-06-15)

### Files Created
- src/config.py - SimulationConfig and ComputerCapability dataclasses
- tests/test_config.py - 10 tests covering both classes

### Key Design Decisions
- Used tuple[int, int] and tuple[float, float] for range fields
- All rule module parameters from detailed-design-05-rules.md included
- ComputerCapability has no defaults - all fields required on init

### Type Annotations
- All fields have full type annotations (checked by mypy)
- Python 3.12+ style used throughout
- No Any, no type suppressions needed

### Verification Results
- pytest tests/test_config.py -v: 10/10 passed
- ruff check src/config.py tests/test_config.py: All checks passed
- mypy src/config.py: Success: no issues found

### Important Constraints
- spatial_grid_cell_size=0.0 means auto-detect (handled in Wave 2)
- ComputerCapability is data-only - detect_computer_capability() comes in C3
- No file I/O, no psutil, no platform detection in this wave - data classes only

### C5 Implementation (2026-06-15)

#### Files Modified
- src/config.py — Added load_config(), _read_toml_config(), _apply_cli_overrides(), _auto_detect_cell_size(), _CLI_MAPPING
- tests/test_config.py — Added TestLoadConfig class with 16 test methods

#### Key Design Decisions
- load_config() uses 3-layer priority: CLI args > pyproject.toml > code defaults
- _read_toml_config() uses stdlib tomllib (Python 3.11+) — not tomli
- _auto_detect_cell_size() uses globals().get() to safely detect if C3/C4 functions exist (handles parallel development)
- get_recommended_params() returns SimulationConfig with spatial_grid_cell_size set, so _auto_detect_cell_size reads that field
- _CLI_MAPPING matches argparse.Namespace attribute names to SimulationConfig field names
- None CLI values are skipped (not set)

#### Config Overridable Fields
- pyproject.toml [tool.simulation]: universe_size, initial_civ_count, max_civ_count, birth_rate, total_steps, name_generator_mode
- CLI mapping: size→universe_size, civs→initial_civ_count, steps→total_steps, birth_rate→birth_rate, mode→name_generator_mode, max_civs→max_civ_count

#### Verification Results
- pytest tests/test_config.py -v: 31/31 passed
- ruff check src/config.py tests/test_config.py: All checks passed
- Tests cover: default config, toml override, CLI override, priority chain, missing/invalid toml, auto-detect with and without C3/C4 functions


### C3 + C4 Implementation (2026-06-15)

#### Files Modified
- src/config.py — Added detect_computer_capability(), get_recommended_params(), format_report() method on ComputerCapability
- tests/test_config.py — Added TestDetectComputerCapability (3 tests) and TestGetRecommendedParams (2 tests)

#### Key Design Decisions
- detect_computer_capability() uses lazy import (from src.entity import Civilization) inside function body to avoid circular import (entity.py imports SimulationConfig from config.py)
- psutil calls wrapped in try/except — any failure falls back to reasonable defaults + continues
- Micro-benchmark creates 1000 Civilization objects + computes 1000 pairwise distances, measures elapsed time
- CPU score normalized to 0-10 scale: <50ms → 10, ≥500ms → 1, with multi-core bonus (up to 1.5x)
- Recommended civ count = 50% of available memory ÷ 200 bytes per civ
- Grid cell size = 500 - (cpu_score/10 × 400) ly, clamped to [50, 500]
- Estimated step time = benchmark_ms × (recommended_civ_count / 1000) × 0.3
- get_recommended_params() creates new SimulationConfig with overridden fields: max_civ_count, spatial_grid_cell_size, run_mode
- format_report() reads platform.processor() and psutil at call time for display info

#### Error Handling
- Every psutil call (cpu_count, cpu_freq, virtual_memory) in its own try/except
- Benchmark failure falls back to 200ms estimate
- All functions guaranteed to never raise — graceful degradation throughout

#### Verification Results
- pytest tests/test_config.py -v: 31/31 passed (all existing + 5 new)
- ruff check: All checks passed
- mypy src/config.py tests/test_config.py: Success: no issues found
- LSP diagnostics: clean on both files
