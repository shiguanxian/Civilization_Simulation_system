# Output Module — Implementation Notes

## stats.py (O1, O2) — 2026-06-15

### Created Files
- src/output/stats.py — StepStats, StatsCollector, format_step_summary
- 	ests/test_output_stats.py — 27 tests

### Key Design Decisions
- rom __future__ import annotations used for TYPE_CHECKING import of Civilization
  - This means ield.type in dataclasses returns strings, not types — tests handle this
- step_events are list[dict] with event_type key, matching simulation event format
- previous_stats fallback: uses delta = total - prev.total to compute new_born/destroyed, both clamped ≥ 0
- collect() returns full StepStats even for empty lists (total_civilizations=0)
- ormat_step_summary() produces 7-line output matching the design spec exactly

### Edge Cases Covered
- Empty civilization list (all zeros)
- Only dead civilizations (filtered to empty → all zeros)
- Single civilization (exact value matching)
- Multiple civilizations (averages, sums, level distribution)
- step_events count all 6 event types correctly
- Unknown event types silently ignored
- step_events=None with previous_stats fallback
- History: append, get_latest, get_history_since (with boundary), clear, collect-after-clear
- Format output: step number, large numbers (comma separator), multiline structure, zero stats

### Verification
- pytest tests/test_output_stats.py -v — 27/27 passed
- uff check src/output/stats.py tests/test_output_stats.py — All checks passed
- mypy src/output/stats.py — Success: no issues found
- Full test suite: 193/194 passed (1 pre-existing failure in test_rules_tech_bomb.py)
