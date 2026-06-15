
## R3 - Expansion Module (2026-06-15)

### Created Files
- src/rules/expansion.py �� pply_expansion() function
- 	ests/test_rules_expansion.py �� 21 tests

### Key Implementation Details
- **Radius growth**: growth = expansion_rate_base * level * log10(energy_output) / 18.0
- **Radius cap**: min(expansion_radius, universe_size * 0.1)
- **Position drift**: random angle (0-2��), distance = expansion_radius * 0.1 * uniform(0.5, 1.0)
- **Coordinate wrapping**: % config.universe_size for both x and y
- **Exposure formula**: ase_exposure_prob + (radius / threshold) + (0.2 if communicating) - (stealth * 0.3), clamped to [0, 1]
- **NOTE**: The exposure formula implemented differs from doc/detailed-design-05-rules.md (step function + multiplicative stealth) �� the task prompt specified a continuous formula with additive stealth penalty, which was followed

### Test Coverage
1. Radius growth: grows, higher level = faster, higher energy = faster
2. Radius cap: bounded at 10% of universe, exact cap, does not shrink
3. Position drift: position changes, drift distance formula validated, multiple directions
4. Coordinate wrapping: wraps at x-positive, x-negative, y both sides
5. Exposure probability: always-expose edge, never-expose edge, radius increases prob, communication increases prob, clamping
6. Dead civs: skipped entirely, mixed alive/dead
7. Communication_active: set on exposure, persistent once set

### Verification
- uv run pytest tests/test_rules_expansion.py -v 21/21 passed
- uv run ruff check src/rules/expansion.py tests/test_rules_expansion.py All checks passed

## R1/R2 - Tech Bomb Module (2026-06-15)

### Created Files
- src/rules/tech_bomb.py apply_development(), _tech_needed(), _calc_carrying_capacity(), _trigger_tech_explosion()
- tests/test_rules_tech_bomb.py 34 tests

### Key Implementation Details
- **Tech growth**: tech_growth_base * (1 + level * 0.5) per step
- **Tech explosion**: triggers when tech_points >= _tech_needed(level) AND random() < tech_explosion_prob
- **Tech needed**: 100.0 * level**2
- **Carrying capacity**: energy_output * level * 1e6 (logistic K value)
- **Population logistic**: rate = pop_growth_rate * (1 - pop / carrying_capacity); negative when over capacity
- **Energy growth**: rate = energy_growth_rate * (1 + tech_points * 1e-6)
- **Explosion skip**: after explosion, `continue` skips population and energy regular growth
- **Level cap**: min(level + 1, 5) in _trigger_tech_explosion
- **Explosion effects**: tech_points halved, energy x random(2,5), detection x random(1.5,3), expansion x random(2,4), pop x random(1.5,3), prob halved
- **Dead civs**: skipped at top of loop with `if not civ.is_alive: continue`
- **config parameter**: _trigger_tech_explosion accepts config for API consistency (currently unused)

### Test Coverage (34 tests)
1. Tech accumulation: increases, scales with level, dead civ skipped
2. Tech needed formula: exact values (100, 400, 900, 1600, 2500), monotonic increase
3. Explosion trigger: sufficent tech triggers, zero prob prevents, insufficient tech prevents
4. Explosion effects: level+1, tech halved (exact 0.5x), energy multi, detection multi, expansion multi, pop multi, prob halved
5. Explosion skips regular growth: population changed by explosion multiplier not regular growth
6. Level cap: capped at 5, explosion effects still apply at cap
7. Population growth: increases normally, approaches carrying capacity, negative growth when over capacity
8. Carrying capacity: formula, scales with level, scales with energy
9. Energy growth: increases, scales with tech_points, formula verified exactly
10. Integration: alive processed, dead skipped, mixed list, empty list
11. Direct _trigger_tech_explosion: level capped at 5, all fields modified in expected ranges

### Verification
- uv run pytest tests/test_rules_tech_bomb.py -v 34/34 passed
- uv run ruff check src/rules/tech_bomb.py tests/test_rules_tech_bomb.py All checks passed

## R4 - Detection Module (2026-06-15)

### Created Files
- src/rules/detection.py — ContactEvent dataclass, detect_contacts() function
- tests/test_rules_detection.py — 25 tests

### Key Implementation Details
- **ContactEvent**: dataclass with civ_a, civ_b, distance, detected_by_a, detected_by_b
- **detect_contacts()**: iterates alive civs, queries SpatialIndex.query_neighbors() with raw detection_range, then applies stealth/communication modifiers
- **Stealth reduction**: effective_range = detection_range * (1 - target.stealth * 0.5)
- **Communication bonus**: if target.communication_active, effective_range *= 1.5
- **Ring distance**: uses src.spatial.ring_distance() for accurate toroidal distance
- **Deduplication**: (min_id, max_id) tuple set, processed after query but before event creation
- **Self-exclusion**: both SpatialIndex (position check) and detect_contacts (id check)
- **No contact if neither detects**: only generates ContactEvent when detected_by_a or detected_by_b is True
- **IMPORTANT**: query_neighbors uses raw detection_range as first-pass filter; stealth/communication modifiers only apply within detect_contacts after query

### Test Coverage (25 tests)
1. ContactEvent: attributes, dataclass identity
2. Basic detection: both detect within range, out of range (no contact), exact boundary (detects), just beyond (no contact)
3. Stealth effect: no stealth (full detection), high stealth reduces range (asymmetric), both high stealth (no contact), partial stealth
4. Communication bonus: increases detection (raw range must be large enough for query_neighbors), stacks with stealth, only affects detector side (not detector's own ability)
5. Deduplication: pair only once, 3 civs produce 3 unique pairs, reverse input order still deduplicates
6. Asymmetric detection: one way detection (both directions tested)
7. Dead civ skip: dead not in contacts, mixed alive/dead
8. Self detection: single civ no self contact
9. Edge cases: empty list, all dead, single civ, ring distance wrap-around

### Verification
- uv run pytest tests/test_rules_detection.py -v 25/25 passed
- uv run ruff check src/rules/detection.py tests/test_rules_detection.py All checks passed

## R5 - Dark Forest Module (2026-06-15)

### Created Files
- src/rules/dark_forest.py -- _calculate_threat, _decide_action, _attempt_attack, _expose_civilization, apply_dark_forest, apply_cosmic_strike
- tests/test_rules_dark_forest.py -- 29 tests

### Key Implementation Details
- **_calculate_threat**: 0.3 base + 0.2*level_diff/5 + 0.3*aggressiveness + 0.2*(1-stealth) + 0.2*communication + random.uniform(-0.1, 0.1), clamped [0,1]
- **_decide_action**: >= attack_threshold(0.65) → "attack", <= flee_threshold(0.35) → "flee", else → "observe"
- **_attempt_attack**: prob = 0.5 + 0.1*level_diff - 0.2*stealth + 0.1*energy_advantage, clamped [0.1, 0.95]
- **Attack success**: defender.is_alive=False, attacker gets 10% of defender's energy_output
- **Attack failure**: attacker.communication_active=True (defender exposes attacker's coordinates)
- **_expose_civilization**: communication_active=True, stealth *= 0.8
- **apply_dark_forest interface**: takes (civilizations, contacts, config) and returns (attacks_count, destroyed_count)
- **apply_cosmic_strike interface**: takes (civilizations, config) and returns destroyed_count (no SpatialIndex needed -- uses direct ring_distance check)
- **Cosmic strike radius**: universe_size * random.uniform(0.02, 0.1)
- **Cosmic strike probability**: config.cosmic_strike_prob (default 0.001)
- **Same-contact edge cases**: order matters -- attack happens before exposure in the same contact loop iteration
- **MonkeyPatch strategy**: for _calculate_threat tests, patch random.uniform to control perturbation; for _attempt_attack tests, patch random.random to force success/failure; for cosmic strike tests, patch both random.random (trigger) and random.uniform (strike params)

### Test Coverage (29 tests)
1. _calculate_threat: baseline mid values, level diff increases, aggressiveness increases, stealth reduces, communication increases, random perturbation range, low clamp, high clamp
2. _decide_action: high→attack, low→flee, mid→observe, custom thresholds
3. _attempt_attack: success kills/energy gain, failure exposes attacker, defender dead returns false, success probability lower bound (0.1 clamp), energy advantage bonus
4. _expose_civilization: sets communication_active, reduces stealth 20%
5. apply_dark_forest (integration): empty contacts, no threat no attack, high threat causes attack, detected civ gets exposed, dead civ skipped
6. apply_cosmic_strike: no strike when prob fails, kills in radius (including boundary), uses ring distance (toroidal wrap), only alive civs counted, strike radius range verified

### Verification
- uv run pytest tests/test_rules_dark_forest.py -v 29/29 passed
- uv run ruff check src/rules/dark_forest.py tests/test_rules_dark_forest.py All checks passed
