# test_technique_catalog.py — HAJ-204 acceptance tests.
#
# Exercises src/technique_catalog.py against the hand-authored sample
# catalog (data/techniques.yaml) plus inline malformed fixtures.
#
# Coverage targets from the ticket:
#   - Dataclasses match Section 2 / Section 5 schema
#   - Loader reads YAML and returns dict[technique_id, definition]
#   - Loader handles missing optional fields gracefully
#   - Basic schema validation rejects malformed entries with clear errors
#   - All schema sections (identity, classification, grip signature, kinetic
#     preconditions, difficulty, ne-waza, era) are exercised
#   - Naming overlay loader (including the empty file case)

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technique_catalog import (
    AcquisitionSource,
    CanonicalGripSignature,
    CatalogValidationError,
    FailedThrowConsequence,
    GripDepth,
    GripHand,
    GripSpec,
    GripTargetRegion,
    KodokanStatus,
    NamingType,
    PROFICIENCY_ORDER,
    ProficiencyTier,
    TechniqueDefinition,
    TechniqueFamily,
    TechniqueNamingOverlay,
    TechniqueRecord,
    UkePostureRequirement,
    load_catalog,
    load_naming_overlays,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CATALOG = REPO_ROOT / "data" / "techniques.yaml"
SAMPLE_OVERLAYS = REPO_ROOT / "data" / "technique_naming_overlays.yaml"


# ---------------------------------------------------------------------------
# Dataclass shape — Section 2 + Section 5 schema
# ---------------------------------------------------------------------------
def test_proficiency_order_is_canonical():
    # Order matters — Section 3 names the eight tiers in ascending sequence.
    names = [tier.value for tier in PROFICIENCY_ORDER]
    assert names == [
        "known", "novice", "proficient", "intermediate",
        "competitive", "expert", "master", "legendary",
    ]


def test_technique_record_default_construction():
    record = TechniqueRecord(technique_id="uchi_mata")
    # Section 5 defaults: a fresh record sits at known with empty ledgers.
    assert record.proficiency_tier is ProficiencyTier.KNOWN
    assert record.teaching_tier is ProficiencyTier.KNOWN
    assert record.proficiency_progress == 0
    assert record.executed_attempts == 0
    assert record.executed_successes == 0
    assert record.executed_ippons == 0
    assert record.defended_attempts == 0
    assert record.defended_successes == 0
    assert record.defended_ippon_losses == 0
    assert record.source_of_acquisition is None
    assert record.year_acquired is None
    assert record.acquired_from is None
    assert record.last_used_year is None


def test_naming_overlay_round_trip_shape():
    overlay = TechniqueNamingOverlay(
        dojo_id="cranford_jkc",
        technique_id="uchi_mata",
        custom_name="Cranford's uchi-mata",
        named_by="sensei_yonezuka",
        year_named=1972,
        triggering_event="first_mastery",
        naming_type=NamingType.SENSEI,
    )
    assert overlay.parent_overlay is None
    assert overlay.naming_type is NamingType.SENSEI


# ---------------------------------------------------------------------------
# Loader against the hand-authored sample catalog
# ---------------------------------------------------------------------------
def test_load_sample_catalog_yaml():
    catalog = load_catalog(SAMPLE_CATALOG)
    assert set(catalog.keys()) == {"uchi_mata", "o_soto_gari", "seoi_nage", "tomoe_nage"}

    uchi = catalog["uchi_mata"]
    # Identity
    assert uchi.name_japanese == "Uchi-mata"
    assert uchi.name_english == "Inner Thigh Throw"
    # Classification
    assert uchi.family is TechniqueFamily.KOSHI_WAZA
    assert uchi.subfamily == "forward_throw"
    assert uchi.kodokan_status is KodokanStatus.GOKYO_NO_WAZA
    # Stage 1 — grip signature
    assert len(uchi.canonical_grip_signature.tori_required_grips) == 2
    first_grip = uchi.canonical_grip_signature.tori_required_grips[0]
    assert first_grip.hand is GripHand.TORI_LEFT
    assert first_grip.target_region is GripTargetRegion.UKE_SLEEVE_UPPER
    assert first_grip.minimum_depth is GripDepth.CONTROLLED
    disq = uchi.canonical_grip_signature.uke_disqualifying_grips
    assert len(disq) == 1 and disq[0].minimum_depth is GripDepth.DEEP
    # Stage 2 — kinetic
    assert uchi.kuzushi_vector == ["forward_right_diagonal", "forward_pure"]
    assert uchi.couple_type == "forward_rotation_about_hip_axis"
    assert uchi.posture_requirements is UkePostureRequirement.UPRIGHT_OR_FORWARD_COMPROMISED
    # Difficulty & pedagogy
    assert uchi.base_difficulty == 70
    assert uchi.pedagogical_prerequisites == ["harai_goshi"]
    assert uchi.minimum_belt_for_competition_use == "green"
    # Ne-waza linkage
    assert uchi.failed_throw_consequence is FailedThrowConsequence.UKE_LANDS_STOMACH
    assert uchi.ne_waza_followup_preferences == ["kesa_gatame"]
    # Era
    assert uchi.era_introduced == 1895
    assert uchi.era_restricted is None


def test_load_sample_catalog_covers_each_family():
    catalog = load_catalog(SAMPLE_CATALOG)
    families = {definition.family for definition in catalog.values()}
    # Sample exercises four of the five families (ne_waza is HAJ-212 scope).
    assert TechniqueFamily.TE_WAZA in families
    assert TechniqueFamily.KOSHI_WAZA in families
    assert TechniqueFamily.ASHI_WAZA in families
    assert TechniqueFamily.SUTEMI_WAZA in families


# ---------------------------------------------------------------------------
# Optional-field handling
# ---------------------------------------------------------------------------
MINIMAL_YAML = textwrap.dedent("""
    techniques:
      - technique_id: minimal_throw
        name_japanese: Minimaru
        name_english: Minimal Throw
        family: te_waza
        subfamily: forward_throw
        kodokan_status: shinmeisho_no_waza
        canonical_grip_signature:
          tori_required_grips:
            - hand: tori_right
              target_region: uke_lapel_high
              minimum_depth: shallow
        kuzushi_vector:
          - forward_pure
        couple_type: placeholder_couple
        posture_requirements: any
        base_difficulty: 40
""").strip()


def test_loader_accepts_minimal_entry_with_optional_fields_omitted(tmp_path):
    yaml_path = tmp_path / "minimal.yaml"
    yaml_path.write_text(MINIMAL_YAML, encoding="utf-8")

    catalog = load_catalog(yaml_path)
    definition = catalog["minimal_throw"]
    # Defaults must materialize cleanly when YAML omits optional sections.
    assert definition.pedagogical_prerequisites == []
    assert definition.minimum_belt_for_competition_use is None
    assert definition.failed_throw_consequence is None
    assert definition.ne_waza_followup_preferences == []
    assert definition.era_introduced is None
    assert definition.era_restricted is None
    assert definition.canonical_grip_signature.uke_disqualifying_grips == []


def test_loader_accepts_json_format(tmp_path):
    payload = {
        "techniques": [
            {
                "technique_id": "json_throw",
                "name_japanese": "Jeisonu",
                "name_english": "JSON Throw",
                "family": "te_waza",
                "subfamily": "forward_throw",
                "kodokan_status": "gokyo_no_waza",
                "canonical_grip_signature": {
                    "tori_required_grips": [
                        {
                            "hand": "tori_right",
                            "target_region": "uke_lapel_high",
                            "minimum_depth": "controlled",
                        }
                    ]
                },
                "kuzushi_vector": ["forward_pure"],
                "couple_type": "placeholder",
                "posture_requirements": "any",
                "base_difficulty": 50,
            }
        ]
    }
    json_path = tmp_path / "catalog.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog = load_catalog(json_path)
    assert "json_throw" in catalog
    assert catalog["json_throw"].base_difficulty == 50


# ---------------------------------------------------------------------------
# Validation — malformed entries raise CatalogValidationError with context
# ---------------------------------------------------------------------------
def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "broken.yaml"
    path.write_text(textwrap.dedent(body).strip(), encoding="utf-8")
    return path


def test_missing_required_field_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            # name_japanese intentionally missing
            name_english: Broken
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
    """)
    with pytest.raises(CatalogValidationError, match="name_japanese"):
        load_catalog(path)


def test_invalid_family_enum_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: not_a_real_family
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
    """)
    with pytest.raises(CatalogValidationError, match="not_a_real_family"):
        load_catalog(path)


def test_invalid_grip_depth_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            canonical_grip_signature:
              tori_required_grips:
                - hand: tori_right
                  target_region: uke_lapel_high
                  minimum_depth: featherlight
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
    """)
    with pytest.raises(CatalogValidationError, match="featherlight"):
        load_catalog(path)


def test_unknown_kuzushi_direction_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [sideways_corkscrew]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
    """)
    with pytest.raises(CatalogValidationError, match="sideways_corkscrew"):
        load_catalog(path)


def test_base_difficulty_out_of_range_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 250
    """)
    with pytest.raises(CatalogValidationError, match="base_difficulty"):
        load_catalog(path)


def test_implausible_era_year_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
            era_introduced: 1492
    """)
    with pytest.raises(CatalogValidationError, match="era_introduced"):
        load_catalog(path)


def test_era_restricted_before_introduced_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: broken
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
            era_introduced: 1950
            era_restricted: 1940
    """)
    with pytest.raises(CatalogValidationError, match="era_restricted"):
        load_catalog(path)


def test_duplicate_technique_id_is_rejected(tmp_path):
    path = _write(tmp_path, """
        techniques:
          - technique_id: dup
            name_japanese: A
            name_english: A
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
          - technique_id: dup
            name_japanese: B
            name_english: B
            family: te_waza
            subfamily: forward_throw
            kodokan_status: gokyo_no_waza
            kuzushi_vector: [forward_pure]
            couple_type: placeholder
            posture_requirements: any
            base_difficulty: 40
    """)
    with pytest.raises(CatalogValidationError, match="duplicate"):
        load_catalog(path)


def test_unsupported_extension_is_rejected(tmp_path):
    path = tmp_path / "catalog.txt"
    path.write_text("anything", encoding="utf-8")
    with pytest.raises(CatalogValidationError, match="extension"):
        load_catalog(path)


# ---------------------------------------------------------------------------
# Naming overlay loader
# ---------------------------------------------------------------------------
def test_load_empty_overlay_file_returns_empty_dict():
    overlays = load_naming_overlays(SAMPLE_OVERLAYS)
    assert overlays == {}


def test_load_missing_overlay_path_returns_empty_dict(tmp_path):
    # Per Section 2 — a freshly seeded world ships with no overlays; the
    # file may not yet exist.
    overlays = load_naming_overlays(tmp_path / "does_not_exist.yaml")
    assert overlays == {}


def test_load_overlay_with_entries(tmp_path):
    path = tmp_path / "overlays.yaml"
    path.write_text(textwrap.dedent("""
        overlays:
          - dojo_id: cranford_jkc
            technique_id: uchi_mata
            custom_name: Cranford's uchi-mata
            named_by: sensei_yonezuka
            year_named: 1972
            triggering_event: first_mastery
            naming_type: sensei
          - dojo_id: newark_judo
            technique_id: uchi_mata
            custom_name: The Dynamite Blast
            named_by: judoka_okada
            year_named: 1981
            triggering_event: legendary_use_in_competition
            naming_type: free_text
            parent_overlay:
              dojo_id: cranford_jkc
              technique_id: uchi_mata
    """).strip(), encoding="utf-8")

    overlays = load_naming_overlays(path)
    assert set(overlays.keys()) == {
        ("cranford_jkc", "uchi_mata"),
        ("newark_judo", "uchi_mata"),
    }
    inherited = overlays[("newark_judo", "uchi_mata")]
    assert inherited.parent_overlay == ("cranford_jkc", "uchi_mata")
    assert inherited.naming_type is NamingType.FREE_TEXT


def test_duplicate_overlay_key_is_rejected(tmp_path):
    path = tmp_path / "overlays.yaml"
    path.write_text(textwrap.dedent("""
        overlays:
          - dojo_id: d
            technique_id: t
            custom_name: A
            named_by: x
            year_named: 1970
            triggering_event: first_mastery
          - dojo_id: d
            technique_id: t
            custom_name: B
            named_by: x
            year_named: 1971
            triggering_event: first_mastery
    """).strip(), encoding="utf-8")
    with pytest.raises(CatalogValidationError, match="duplicate"):
        load_naming_overlays(path)
