"""Tests for registry loading and pattern lookup."""


from services.registry import (
    get_active_patterns,
    get_candidate_patterns_for_move,
    get_registry_version,
    load_registry,
)


class TestRegistry:
    def test_load_registry(self):
        """Registry loads successfully with correct version."""
        registry = load_registry()
        assert registry["registry_version"] == "1.0"
        assert len(registry["patterns"]) == 61

    def test_registry_version(self):
        load_registry()
        assert get_registry_version() == "1.0"

    def test_all_patterns_have_required_fields(self):
        registry = load_registry()
        for p in registry["patterns"]:
            assert "id" in p, f"Pattern missing id: {p}"
            assert "phase" in p, f"Pattern {p['id']} missing phase"
            assert "axis" in p, f"Pattern {p['id']} missing axis"
            assert "name" in p, f"Pattern {p['id']} missing name"
            assert "description" in p, f"Pattern {p['id']} missing description"
            assert "detection_method" in p, f"Pattern {p['id']} missing detection_method"
            assert "cp_loss_min" in p, f"Pattern {p['id']} missing cp_loss_min"
            assert "active" in p, f"Pattern {p['id']} missing active"

    def test_pattern_id_prefixes(self):
        """All pattern IDs follow prefix conventions."""
        registry = load_registry()
        valid_prefixes = {"OT", "OS", "OL", "MT", "MS", "ET", "ES", "GC"}
        for p in registry["patterns"]:
            prefix = p["id"].split("-")[0]
            assert prefix in valid_prefixes, f"Invalid prefix on {p['id']}"

    def test_unique_ids(self):
        registry = load_registry()
        ids = [p["id"] for p in registry["patterns"]]
        assert len(ids) == len(set(ids)), "Duplicate pattern IDs found"

    def test_active_patterns_excludes_game_conditions(self):
        load_registry()
        patterns = get_active_patterns(exclude_axes={"game_condition", "opening_line"})
        for p in patterns:
            assert p["axis"] not in ("game_condition", "opening_line")

    def test_candidate_patterns_filters_by_phase_and_cp_loss(self):
        load_registry()
        # Opening with cp_loss=250 should match opening tactical patterns
        candidates = get_candidate_patterns_for_move("opening", 250)
        assert len(candidates) > 0
        for p in candidates:
            assert p["phase"] in ("opening", "all")
            assert 250 >= p["cp_loss_min"]

    def test_candidate_patterns_low_cp_loss_filters(self):
        load_registry()
        # cp_loss=10 should not match any opening tactical (min 100+)
        candidates = get_candidate_patterns_for_move("opening", 10)
        for p in candidates:
            assert p["cp_loss_min"] <= 10

    def test_game_condition_count(self):
        registry = load_registry()
        gc_patterns = [p for p in registry["patterns"] if p["axis"] == "game_condition"]
        assert len(gc_patterns) == 10
