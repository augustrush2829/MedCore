from types import SimpleNamespace

from app.services.ai import build_ai_content


def test_liver_lab_and_statin_produces_medication_warning():
    case = SimpleNamespace(
        chief_complaint="Хэвлийн өвдөлт",
        symptoms=[SimpleNamespace(name="Баруун дээд хэвлийн өвдөлт")],
        lab_results=[
            SimpleNamespace(test_name="ALT", value=120, unit="U/L", abnormal_flag=True),
        ],
        medications=[
            SimpleNamespace(
                name="Atorvastatin",
                status="active",
                ingredients=[SimpleNamespace(ingredient_name="Atorvastatin calcium")],
            )
        ],
        supplements=[],
        patient=SimpleNamespace(allergies=[]),
    )

    result = build_ai_content(case)

    assert result.doctor_confirmation_required is True
    assert result.medication_warnings[0].type == "dose_risk"
    assert result.causality_assessment.type == "medication_related"


def test_chest_pain_produces_red_flag():
    case = SimpleNamespace(
        chief_complaint="Цээжний өвдөлт, амьсгал давчдах",
        symptoms=[],
        lab_results=[],
        medications=[],
        supplements=[],
        patient=SimpleNamespace(allergies=[]),
    )

    result = build_ai_content(case)

    assert result.red_flags
    assert result.recommended_tests[0].priority == "urgent"


def test_allergy_match_produces_critical_medication_warning():
    case = SimpleNamespace(
        chief_complaint="Толгой өвдөх",
        symptoms=[],
        lab_results=[],
        medications=[
            SimpleNamespace(
                name="Aspirin",
                status="active",
                ingredients=[SimpleNamespace(ingredient_name="Aspirin")],
            )
        ],
        supplements=[],
        patient=SimpleNamespace(allergies=[SimpleNamespace(substance="Aspirin")]),
    )

    result = build_ai_content(case)

    assert result.medication_warnings[0].type == "allergy"
    assert result.medication_warnings[0].severity == "critical"


def test_anticoagulant_and_nsaid_interaction_is_flagged():
    case = SimpleNamespace(
        chief_complaint="Өвдөлт",
        symptoms=[],
        lab_results=[],
        medications=[
            SimpleNamespace(
                name="Warfarin",
                status="active",
                ingredients=[SimpleNamespace(ingredient_name="Warfarin")],
            ),
            SimpleNamespace(
                name="Ibuprofen",
                status="active",
                ingredients=[SimpleNamespace(ingredient_name="Ibuprofen")],
            ),
        ],
        supplements=[],
        patient=SimpleNamespace(allergies=[]),
    )

    result = build_ai_content(case)

    assert any(warning.type == "interaction" for warning in result.medication_warnings)
