from collections import Counter

from app.db.models import ClinicalCase
from app.schemas import AIContent, CausalityAssessment, DiagnosisSuggestion, MedicationWarning, RecommendedTest, SourceCitation


LIVER_LABS = {"alt", "ast", "alp", "ggt", "bilirubin", "билирубин"}
STATIN_INGREDIENTS = {"atorvastatin", "atorvastatin calcium", "rosuvastatin", "simvastatin"}
CHEST_RED_FLAGS = {"цээж", "амьсгал", "давчдах", "зүүн гар"}
NSAID_INGREDIENTS = {"ibuprofen", "naproxen", "diclofenac", "ketorolac", "аспирин", "aspirin"}
ANTICOAGULANTS = {"warfarin", "rivaroxaban", "apixaban", "dabigatran", "варфарин"}
ACE_ARB_INGREDIENTS = {"lisinopril", "enalapril", "losartan", "valsartan", "лизиноприл", "эналаприл"}
POTASSIUM_RAISING_INGREDIENTS = {"spironolactone", "eplerenone", "potassium", "калийн", "спиронолактон"}


def build_ai_content(case: ClinicalCase) -> AIContent:
    symptoms = [symptom.name for symptom in case.symptoms]
    labs = list(case.lab_results)
    medications = list(case.medications)
    abnormal_labs = [lab for lab in labs if lab.abnormal_flag]
    medication_names = [med.name for med in medications if med.status == "active"]
    ingredients = [
        ingredient.ingredient_name
        for medication in medications
        for ingredient in medication.ingredients
    ]
    supplement_ingredients = [
        ingredient
        for supplement in getattr(case, "supplements", [])
        for ingredient in supplement.ingredients
    ]
    allergies = list(getattr(getattr(case, "patient", None), "allergies", []))

    red_flags = detect_red_flags(case.chief_complaint, symptoms)
    medication_warnings = detect_medication_warnings(medications, ingredients, abnormal_labs, allergies, supplement_ingredients)
    differential = build_differential(case.chief_complaint, symptoms, abnormal_labs, ingredients, supplement_ingredients)
    missing = build_missing_information(case.chief_complaint, abnormal_labs, medications, allergies)
    tests = build_recommended_tests(abnormal_labs, red_flags)
    causality = build_causality(abnormal_labs, ingredients, supplement_ingredients, medication_warnings)

    confidence = 68 if abnormal_labs or symptoms else 42
    if red_flags:
        confidence = max(confidence, 72)

    return AIContent(
        clinical_summary=build_summary(case.chief_complaint, symptoms, abnormal_labs, medication_names),
        differential_diagnosis=differential,
        missing_information=missing,
        recommended_tests=tests,
        medication_warnings=medication_warnings,
        causality_assessment=causality,
        red_flags=red_flags,
        citations=default_citations(),
        confidence_level=confidence,
        doctor_confirmation_required=True,
    )


def build_summary(chief_complaint: str, symptoms: list[str], abnormal_labs: list, medications: list[str]) -> str:
    parts = [f"Гол зовиур: {chief_complaint}."]
    if symptoms:
        parts.append("Бүртгэгдсэн симптом: " + ", ".join(symptoms) + ".")
    if abnormal_labs:
        lab_text = ", ".join(f"{lab.test_name} {lab.value:g} {lab.unit}" for lab in abnormal_labs)
        parts.append("Хэвийн бус лаборатори: " + lab_text + ".")
    if medications:
        parts.append("Идэвхтэй эм: " + ", ".join(medications) + ".")
    parts.append("AI нь эцсийн онош батлахгүй, эмчийн баталгаажуулалт шаардлагатай.")
    return " ".join(parts)


def detect_red_flags(chief_complaint: str, symptoms: list[str]) -> list[str]:
    text = " ".join([chief_complaint, *symptoms]).lower()
    if any(flag in text for flag in CHEST_RED_FLAGS):
        return [
            "Цээжний өвдөлт, амьсгал давчдах эсвэл зүүн гарт цацрах шинж байвал яаралтай ЭКГ/тропонин үнэлгээ хийнэ.",
            "Гемодинамик тогтворгүй байдал, SpO2 бууралт илэрвэл яаралтай тусламжийн протокол идэвхжүүлнэ.",
        ]
    if "шарлалт" in text:
        return ["Шарлалт, INR өсөлт, ухаан самууралт хавсарвал хурдан явцтай элэгний дутагдлыг яаралтай үнэлнэ."]
    return []


def detect_medication_warnings(
    medications: list,
    ingredients: list[str],
    abnormal_labs: list,
    allergies: list,
    supplement_ingredients: list[str],
) -> list[MedicationWarning]:
    warnings: list[MedicationWarning] = []
    ingredient_counts = Counter(normalize_name(ingredient) for ingredient in [*ingredients, *supplement_ingredients])
    duplicates = [name for name, count in ingredient_counts.items() if count > 1]
    if duplicates:
        warnings.append(
            MedicationWarning(
                type="duplicate_ingredient",
                severity="high",
                description="Эм эсвэл нэмэлт бүтээгдэхүүнд ижил active ingredient давхар хэрэглэгдэж болзошгүй: " + ", ".join(duplicates),
                medications=[med.name for med in medications],
            )
        )

    has_liver_abnormality = any(lab.test_name.lower() in LIVER_LABS and lab.abnormal_flag for lab in abnormal_labs)
    normalized_ingredients = {normalize_name(ingredient) for ingredient in ingredients}
    normalized_supplements = {normalize_name(ingredient) for ingredient in supplement_ingredients}
    has_statin = any(ingredient in STATIN_INGREDIENTS for ingredient in normalized_ingredients)
    if has_liver_abnormality and has_statin:
        statins = [
            med.name
            for med in medications
            if any(normalize_name(ingredient.ingredient_name) in STATIN_INGREDIENTS for ingredient in med.ingredients)
        ]
        warnings.append(
            MedicationWarning(
                type="dose_risk",
                severity="high",
                description="Статин хэрэглэж буй үед элэгний фермент өссөн тул drug-induced liver injury боломжийг шалгана.",
                medications=statins,
            )
        )
    allergy_matches = find_allergy_matches(medications, allergies)
    for substance, medication_names in allergy_matches.items():
        warnings.append(
            MedicationWarning(
                type="allergy",
                severity="critical",
                description=f"Өвчтөнд {substance} харшил бүртгэлтэй тул тухайн эм/найрлагыг хэрэглэхийн өмнө эмч дахин баталгаажуулна.",
                medications=medication_names,
            )
        )
    if normalized_ingredients & ANTICOAGULANTS and (normalized_ingredients | normalized_supplements) & NSAID_INGREDIENTS:
        warnings.append(
            MedicationWarning(
                type="interaction",
                severity="high",
                description="Anticoagulant болон NSAID/аспирин давхцахад цус алдалтын эрсдэл нэмэгдэнэ.",
                medications=[med.name for med in medications],
            )
        )
    if normalized_ingredients & ACE_ARB_INGREDIENTS and (normalized_ingredients | normalized_supplements) & POTASSIUM_RAISING_INGREDIENTS:
        warnings.append(
            MedicationWarning(
                type="interaction",
                severity="medium",
                description="ACE/ARB болон potassium-sparing эм эсвэл potassium supplement давхцахад hyperkalemia эрсдэлийг шалгана.",
                medications=[med.name for med in medications],
            )
        )
    return warnings


def build_differential(
    chief_complaint: str,
    symptoms: list[str],
    abnormal_labs: list,
    ingredients: list[str],
    supplement_ingredients: list[str],
) -> list[DiagnosisSuggestion]:
    text = " ".join([chief_complaint, *symptoms]).lower()
    has_liver_abnormality = any(lab.test_name.lower() in LIVER_LABS and lab.abnormal_flag for lab in abnormal_labs)
    has_statin = any(normalize_name(ingredient) in STATIN_INGREDIENTS for ingredient in ingredients)
    has_supplements = bool(supplement_ingredients)

    if has_liver_abnormality:
        suggestions = [
            DiagnosisSuggestion(
                name="Эмийн шалтгаант элэгний гэмтэл (DILI)",
                confidence=72 if has_statin else 54 if has_supplements else 48,
                supporting_evidence=["ALT/AST эсвэл холестазын үзүүлэлт хэвийн бус", "Эм болон supplement timeline-тэй харьцуулж үнэлэх шаардлагатай"],
                missing_evidence=["Вирусын гепатитын серологи", "Архины хэрэглээ, supplement хэрэглээ", "Abdominal ultrasound"],
                icd_code="K71",
            ),
            DiagnosisSuggestion(
                name="Цөсний замын эмгэг",
                confidence=56 if "баруун дээд" in text or "хэвлийн" in text else 38,
                supporting_evidence=["Хэвлийн өвдөлт болон элэг/цөсний лабораторийн өөрчлөлттэй нийцэж болно"],
                missing_evidence=["ALP/GGT pattern", "Abdominal ultrasound", "Шарлалт байгаа эсэх"],
                icd_code="K80",
            ),
        ]
    elif any(word in text for word in CHEST_RED_FLAGS):
        suggestions = [
            DiagnosisSuggestion(
                name="Acute coronary syndrome үгүйсгэх шаардлагатай",
                confidence=78,
                supporting_evidence=["Цээжний өвдөлт/амьсгал давчдах red flag шинжтэй"],
                missing_evidence=["ЭКГ", "Тропонин", "Vital signs", "Өвдөлтийн шинж чанар ба эрсдэлт хүчин зүйл"],
                icd_code="I24",
            )
        ]
    else:
        suggestions = [
            DiagnosisSuggestion(
                name="Мэдээлэл дутуу clinical syndrome",
                confidence=35,
                supporting_evidence=["Одоогийн case-д structured lab/medication/symptom мэдээлэл хязгаарлагдмал"],
                missing_evidence=["Дэлгэрэнгүй анамнез", "Амин үзүүлэлт", "Шаардлагатай лаборатори"],
            )
        ]
    return suggestions


def build_missing_information(chief_complaint: str, abnormal_labs: list, medications: list, allergies: list) -> list[str]:
    missing = ["Амин үзүүлэлт бүрэн оруулах", "Харшил болон хавсарсан өвчний түүх баталгаажуулах"]
    if abnormal_labs:
        missing.append("Өмнөх лабораторийн trend болон baseline утгыг харьцуулах")
    if medications:
        missing.append("Эм эхэлсэн огноо, тун өөрчлөгдсөн эсэх, supplement хэрэглээг шалгах")
    if not allergies:
        missing.append("Эмийн харшлыг doctor-verified байдлаар бүртгэх")
    if "хэвлийн" in chief_complaint.lower():
        missing.append("Abdominal ultrasound болон шарлалт байгаа эсэхийг үнэлэх")
    return missing


def build_recommended_tests(abnormal_labs: list, red_flags: list[str]) -> list[RecommendedTest]:
    tests: list[RecommendedTest] = []
    if red_flags:
        tests.extend(
            [
                RecommendedTest(name="ЭКГ", reason="Цээжний өвдөлтийн яаралтай шалтгааныг үгүйсгэх", priority="urgent"),
                RecommendedTest(name="Тропонин", reason="Myocardial injury шалгах", priority="urgent"),
            ]
        )
    if any(lab.test_name.lower() in LIVER_LABS for lab in abnormal_labs):
        tests.extend(
            [
                RecommendedTest(name="HBsAg, Anti-HCV", reason="Вирусын гепатит үгүйсгэх", priority="urgent"),
                RecommendedTest(name="ALP, GGT, нийт/шууд билирубин", reason="Hepatocellular vs cholestatic pattern ялгах", priority="routine"),
                RecommendedTest(name="Abdominal ultrasound", reason="Элэг, цөсний бүтэц ба бөглөрөл шалгах", priority="urgent"),
            ]
        )
    if not tests:
        tests.append(RecommendedTest(name="Case-specific baseline labs", reason="Clinical context бүрдүүлэх", priority="routine"))
    return tests


def build_causality(
    abnormal_labs: list,
    ingredients: list[str],
    supplement_ingredients: list[str],
    warnings: list[MedicationWarning],
) -> CausalityAssessment:
    if warnings:
        return CausalityAssessment(
            type="medication_related",
            confidence=65,
            evidence="Эм, active ingredient, supplement эсвэл allergy/interactions-ийн pattern clinical өөрчлөлттэй давхцаж байгаа тул эмийн нөлөө боломжтой. Бусад шалтгааныг шинжилгээгээр үгүйсгэнэ.",
        )
    if abnormal_labs and supplement_ingredients:
        return CausalityAssessment(
            type="unclear",
            confidence=50,
            evidence="Лабораторийн өөрчлөлт болон supplement хэрэглээ зэрэгцэж байгаа боловч start date, dose change, өмнөх trend дутуу тул шалтгаан тодорхойгүй.",
        )
    if abnormal_labs:
        return CausalityAssessment(
            type="unclear",
            confidence=45,
            evidence="Лабораторийн өөрчлөлт байгаа боловч timeline, medication start/change, өмнөх trend дутуу тул шалтгаан тодорхойгүй.",
        )
    return CausalityAssessment(
        type="unclear",
        confidence=30,
        evidence="Structured evidence хангалтгүй тул өвчин эсвэл эмийн шалтгааныг ялгах боломжгүй.",
    )


def default_citations() -> list[SourceCitation]:
    return [
        SourceCitation(title="MedCore MVP clinical safety policy", source="Internal", version="mvp-v1"),
        SourceCitation(title="Drug-induced liver injury clinical assessment framework", source="Guideline placeholder", version="review-required"),
        SourceCitation(title="Chest pain emergency triage framework", source="Guideline placeholder", version="review-required"),
    ]


def normalize_name(value: str) -> str:
    return value.strip().lower()


def find_allergy_matches(medications: list, allergies: list) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for allergy in allergies:
        substance = normalize_name(allergy.substance)
        if not substance:
            continue
        for medication in medications:
            medication_terms = [normalize_name(medication.name)]
            medication_terms.extend(normalize_name(ingredient.ingredient_name) for ingredient in medication.ingredients)
            if any(substance in term or term in substance for term in medication_terms):
                matches.setdefault(allergy.substance, []).append(medication.name)
    return matches
