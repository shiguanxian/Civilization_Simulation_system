# Entity Module Implementation Notes

## Files Created
- src/entity.py ！ Civilization dataclass (16 fields) + NameGenerator class
- 	ests/test_entity.py ！ 15 tests covering both classes

## Key Decisions
1. **Civilization defaults**: level=1 (minimum), is_alive=True (alive by default), others at zero/empty. These are sensible placeholders for a new civilization before being configured by the factory.
2. **NameGenerator word bank iteration**: Suffix-first traversal (increment suffix index, wrap to 0 and increment prefix when exhausted). Matches the two-index pattern in the design doc (_prefix_index, _suffix_index).
3. **Word banks as tuples**: Class-level PREFIXES and SUFFIXES are tuples, not lists, ensuring immutability and satisfying the "no mutable class-level defaults" constraint.
4. **No business logic in Civilization**: Verified by test checking that no non-dunder custom methods exist.

## Word Bank Stats
- Prefixes: 10 entries
- Suffixes: 8 entries
- Total combinations: 80
- Fallback format: 猟苧 #000000 (same as number mode)

## Verification Results
- pytest: 15/15 passed ?
- uff: zero violations ?
- mypy: no type errors ?

## Integration Notes
- entity.py has zero dependencies (pure Python stdlib) ！ truly the foundation layer
- Will be consumed by: CivilizationFactory (E3, Wave 2), spatial module, rules modules
- NameGenerator state is per-instance, not shared ！ each factory gets its own

---

## E3 ！ CivilizationFactory (Added)

### Implementation
- File: src/entity.py ！ appended after NameGenerator class
- New dependencies: random (stdlib), from src.config import SimulationConfig
- Signature: CivilizationFactory(config: SimulationConfig, name_generator: NameGenerator)
- Key methods:
  - create_random(civ_id, birth_time, universe_size, cluster_center=None, cluster_radius=None) ！ generates one civ with random position + random params from config ranges
  - create_initial_batch(universe_size) ！ generates config.initial_civ_count civs; dispatches to _create_uniform_batch or _create_cluster_batch based on config.initial_distribution_mode

### Position generation
- Uniform: random.uniform(0, universe_size) for both x and y
- Cluster: Gaussian offset from center: cx + random.gauss(0, radius/3), same for y
- Ring wrap: Both modes apply modulo universe_size to wrap coordinates

### Distribution modes
- uniform: Each civ independently randomly placed
- cluster: Generate config.cluster_count random cluster centers, assign each civ to a random center with Gaussian offset using config.cluster_radius

### Tests (12 new, 27 total)
- test_factory_init ！ constructor stores config and name_generator
- test_factory_create_random_fields_set ！ all fields properly assigned
- test_factory_random_params_in_range ！ 100 rounds verify all params within config ranges
- test_factory_positions_within_bounds ！ 200 positions in [0, universe_size)
- test_factory_positions_wrap_around ！ modulo wrapping works for edge positions
- test_factory_initial_batch_count ！ batch size matches config
- test_factory_initial_batch_default_count ！ batch uses default config count
- test_factory_initial_batch_all_have_birth_time_zero ！ initial civs have birth_time=0
- test_factory_initial_batch_unique_ids ！ all IDs are unique
- test_factory_uniform_distribution_positions ！ uniform mode does not clump in center
- test_factory_cluster_distribution ！ cluster mode works (all in bounds)
- test_factory_cluster_positions_near_center ！ cluster offsets within 2x radius

### Verification
- pytest: 27/27 passed
- ruff: zero violations (import ordering fixed by ruff --fix)
