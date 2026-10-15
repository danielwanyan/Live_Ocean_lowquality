import json
import re
from types import MappingProxyType


def _immutable(value):
    if type(value) is dict:
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_immutable(item) for item in value)
    return value


def _mutable(value):
    if isinstance(value, MappingProxyType):
        return {key: _mutable(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_mutable(item) for item in value]
    return value


def _exact_contract_equal(actual, expected):
    if isinstance(expected, MappingProxyType):
        if type(actual) is not dict or set(actual) != set(expected):
            return False
        return all(
            _exact_contract_equal(actual[key], expected[key]) for key in expected
        )
    if type(expected) is tuple:
        if type(actual) is not list or len(actual) != len(expected):
            return False
        return all(
            _exact_contract_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    return type(actual) is type(expected) and actual == expected


EXPECTED_REQUIRED_FACTS = (
    "sexualized_exposure_or_behavior_found",
    "ordinary_tryon_or_public_context_only",
    "disturbing_visual_dominates",
    "cleaning_demo_context",
    "novelty_or_product_art_context",
    "sustained_product_promotion_found",
    "unrelated_content_dominates",
    "real_physical_product_display_found",
    "core_buying_information_found",
    "identifiable_product_and_core_purpose_found",
    "extremely_low_information_across_relevant_segments",
    "explicit_generated_content_evidence_found",
    "authenticity_misleading_found",
    "generated_product_material_mismatch_found",
    "concrete_replay_indicator_found",
    "replay_weak_signal_only",
    "concrete_live_effect_claim_found",
    "materially_misleading_basis_found",
    "effect_claim_prevalence_or_strength_threshold_met",
    "marketing_or_product_image_only",
    "off_platform_destination_found",
    "explicit_transaction_guidance_found",
    "same_scene_transaction_requirement_met",
    "live_promoted_item_evidence_found",
    "bound_product_evidence_found",
    "core_product_contradiction_found",
    "minor_variant_or_background_only",
    "category_15_non_ipp_illegal_basis_found",
    "sustained_negative_emotion_found",
    "hostile_shaming_fear_evidence_found",
    "routine_sales_or_knowledge_marketing_only",
)
EXPECTED_FACT_KEYS = ("value", "evidence_sources", "evidence_detail")
EXPECTED_MATERIAL_AVAILABILITY_KEYS = (
    "segment_frame",
    "segment_asr",
    "comment_interaction",
    "pearl_product_title",
    "pearl_product_image",
)
EXPECTED_CATEGORY_NAMES = MappingProxyType(
    {
        1: "色情低俗低质问题",
        2: "恶心恐怖低质问题",
        3: "商品无关低质问题",
        4: "无互动低质问题",
        5: "无实物商品展示低质问题",
        6: "商品描述不详细低质问题",
        7: "静态帧遮挡低质问题",
        8: "非母语违规低质问题",
        9: "AIGC真实性低质问题",
        10: "AIGC商品展示低质问题",
        11: "录播回放低质问题",
        12: "功能效果虚假宣传低质问题",
        13: "危险行为低质问题",
        14: "站外引流交易低质问题",
        15: "违法违规商品低质问题",
        16: "政治敏感低质问题",
        17: "争议话题低质问题",
        18: "负面引导低质问题",
        19: "隐私敏感商品低质问题",
    }
)
PRODUCT_IMAGE_ALLOWED_CATEGORY_IDS = frozenset((3, 5, 6, 9, 10, 12, 15, 16, 17))
EXPECTED_GATE_DEFINITIONS = _immutable(
    {
        "1": {
            "required_true": ["sexualized_exposure_or_behavior_found"],
            "blocked_true": ["ordinary_tryon_or_public_context_only"],
        },
        "2": {
            "required_true": ["disturbing_visual_dominates"],
            "blocked_true": ["cleaning_demo_context", "novelty_or_product_art_context"],
        },
        "3": {
            "required_true": ["unrelated_content_dominates"],
            "blocked_true": ["sustained_product_promotion_found"],
        },
        "5": {
            "required_true": ["sustained_product_promotion_found"],
            "blocked_true": ["real_physical_product_display_found", "unrelated_content_dominates"],
        },
        "6": {
            "required_true": [
                "sustained_product_promotion_found",
                "real_physical_product_display_found",
                "extremely_low_information_across_relevant_segments",
            ],
            "blocked_true": [
                "core_buying_information_found",
                "identifiable_product_and_core_purpose_found",
                "unrelated_content_dominates",
            ],
        },
        "9": {
            "required_true": [
                "explicit_generated_content_evidence_found",
                "authenticity_misleading_found",
            ],
            "blocked_true": [],
        },
        "10": {
            "required_true": [
                "explicit_generated_content_evidence_found",
                "generated_product_material_mismatch_found",
            ],
            "blocked_true": [],
        },
        "11": {
            "required_true": ["concrete_replay_indicator_found"],
            "blocked_true": ["replay_weak_signal_only"],
        },
        "12": {
            "required_true": [
                "concrete_live_effect_claim_found",
                "materially_misleading_basis_found",
                "effect_claim_prevalence_or_strength_threshold_met",
            ],
            "blocked_true": ["marketing_or_product_image_only"],
        },
        "14": {
            "required_true": [
                "off_platform_destination_found",
                "explicit_transaction_guidance_found",
                "same_scene_transaction_requirement_met",
            ],
            "blocked_true": [],
        },
        "15": {
            "required_true": [
                "live_promoted_item_evidence_found",
                "bound_product_evidence_found",
                "core_product_contradiction_found",
            ],
            "blocked_true": ["minor_variant_or_background_only"],
            "alternative_true": ["category_15_non_ipp_illegal_basis_found"],
        },
        "18": {
            "required_true": [
                "sustained_negative_emotion_found",
                "hostile_shaming_fear_evidence_found",
            ],
            "blocked_true": ["routine_sales_or_knowledge_marketing_only"],
        },
        "19": {
            "required_true": [],
            "blocked_true": [],
            "disabled": True,
        },
    }
)
EXPECTED_REROUTES = _immutable(
    [
        {"from": [5], "to": 3, "rule": "priority_3_over_5_for_unrelated_content"},
        {"from": [6], "to": 3, "rule": "priority_3_over_6"},
        {"from": [6], "to": 5, "rule": "priority_5_over_6_for_no_physical_display"},
        {"from": [8], "to": 15, "rule": "priority_15_over_8_for_product_mismatch"},
        {"from": [19], "to": 1, "rule": "priority_1_over_19"},
    ]
)
CATEGORY_ALLOWED_MATERIALS = MappingProxyType(
    {
        1: frozenset(("segment_frame", "segment_asr")),
        2: frozenset(("segment_frame", "segment_asr")),
        3: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "comment_interaction",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        4: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "comment_interaction",
            )
        ),
        5: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        6: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "comment_interaction",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        7: frozenset(("segment_frame",)),
        8: frozenset(("segment_asr", "segment_frame_visible_text")),
        9: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        10: frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        11: frozenset(("segment_frame", "segment_asr")),
        12: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        13: frozenset(("segment_frame", "segment_asr")),
        14: frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        15: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        16: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        17: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        18: frozenset(("segment_frame", "segment_asr", "comment_interaction")),
        19: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
    }
)
MINIMUM_DISTINCT_EVIDENCE_UNITS = MappingProxyType(
    {
        category_id: 2 if category_id in {13, 15, 16, 17, 18} else 1
        for category_id in range(1, 20)
    }
)
FACT_ALLOWED_MATERIALS = MappingProxyType(
    {
        "sexualized_exposure_or_behavior_found": frozenset(("segment_frame", "segment_asr")),
        "ordinary_tryon_or_public_context_only": frozenset(("segment_frame", "segment_asr")),
        "disturbing_visual_dominates": frozenset(("segment_frame", "segment_asr")),
        "cleaning_demo_context": frozenset(("segment_frame", "segment_asr")),
        "novelty_or_product_art_context": frozenset(("segment_frame", "segment_asr")),
        "sustained_product_promotion_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "unrelated_content_dominates": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "real_physical_product_display_found": frozenset(("segment_frame",)),
        "core_buying_information_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "identifiable_product_and_core_purpose_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "extremely_low_information_across_relevant_segments": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "explicit_generated_content_evidence_found": frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        "authenticity_misleading_found": frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        "generated_product_material_mismatch_found": frozenset(
            (
                "segment_frame",
                "segment_asr",
                "segment_frame_visible_text",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        "concrete_replay_indicator_found": frozenset(("segment_frame", "segment_asr")),
        "replay_weak_signal_only": frozenset(("segment_frame", "segment_asr")),
        "concrete_live_effect_claim_found": frozenset(("segment_frame", "segment_asr")),
        "materially_misleading_basis_found": frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        "effect_claim_prevalence_or_strength_threshold_met": frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        "marketing_or_product_image_only": frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        "off_platform_destination_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "explicit_transaction_guidance_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "same_scene_transaction_requirement_met": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        "live_promoted_item_evidence_found": frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text")
        ),
        "bound_product_evidence_found": frozenset(
            ("pearl_product_title", "pearl_product_image")
        ),
        "core_product_contradiction_found": frozenset(
            (
                "segment_frame",
                "segment_asr",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        "minor_variant_or_background_only": frozenset(
            (
                "segment_frame",
                "segment_asr",
                "pearl_product_title",
                "pearl_product_image",
            )
        ),
        "category_15_non_ipp_illegal_basis_found": frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        "sustained_negative_emotion_found": frozenset(
            ("segment_frame", "segment_asr", "comment_interaction")
        ),
        "hostile_shaming_fear_evidence_found": frozenset(
            ("segment_frame", "segment_asr", "comment_interaction")
        ),
        "routine_sales_or_knowledge_marketing_only": frozenset(
            ("segment_frame", "segment_asr", "comment_interaction")
        ),
    }
)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _reject_json_constant(value):
    raise ValueError("non_finite_json_constant:" + value)


def _strict_json_loads(value):
    return json.loads(value, parse_constant=_reject_json_constant)


def _extract_payload(judge_output):
    text = _text(judge_output)
    marker = "FINAL_JSON:"
    if marker not in text:
        raise ValueError("final_json_marker_missing")

    json_text = text.split(marker, 1)[1].strip()
    fence = chr(96) * 3
    if json_text.startswith(fence):
        json_text = json_text[len(fence):].lstrip()
        if json_text.startswith("json") and (
            len(json_text) == len("json") or json_text[len("json")].isspace()
        ):
            json_text = json_text[len("json"):].lstrip()
        if not json_text.endswith(fence):
            raise ValueError("final_json_fence_unclosed")
        json_text = json_text[:-len(fence)].rstrip()

    payload = _strict_json_loads(json_text)
    if not isinstance(payload, dict):
        raise ValueError("final_json_not_object")
    return payload


def _load_gates(value):
    if isinstance(value, str):
        try:
            value = _strict_json_loads(value)
        except Exception as exc:
            raise ValueError("boundary_gates_parse_failed:" + _text(exc))
    if not isinstance(value, dict):
        raise ValueError("boundary_gates_not_object")
    return value


def _validate_contract(payload, gates, expected_version):
    errors = []
    if expected_version is None or (type(expected_version) is str and not expected_version.strip()):
        errors.append("boundary_contract_version_missing")
    elif type(expected_version) is not str:
        errors.append("boundary_contract_version_invalid")

    gate_contract_version = gates.get("contract_version")
    if type(gate_contract_version) is not str or gate_contract_version != expected_version:
        errors.append("gate_contract_version_mismatch")
    gate_rules_version = gates.get("rules_version")
    if type(gate_rules_version) is not str or gate_rules_version != expected_version:
        errors.append("gate_rules_version_mismatch")

    required_facts = gates.get("required_facts")
    required_facts_valid = (
        type(required_facts) is list
        and all(type(fact_name) is str and bool(fact_name.strip()) for fact_name in required_facts)
        and required_facts == list(EXPECTED_REQUIRED_FACTS)
    )
    if not required_facts_valid:
        errors.append("gate_required_facts_contract_mismatch")

    gate_definitions_valid = _exact_contract_equal(
        gates.get("gate_definitions"), EXPECTED_GATE_DEFINITIONS
    )
    if not gate_definitions_valid:
        errors.append("gate_definitions_contract_mismatch")

    reroutes_valid = _exact_contract_equal(gates.get("reroutes"), EXPECTED_REROUTES)
    if not reroutes_valid:
        errors.append("gate_reroutes_contract_mismatch")

    material_availability = gates.get("material_availability")
    material_availability_valid = (
        type(material_availability) is dict
        and set(material_availability) == set(EXPECTED_MATERIAL_AVAILABILITY_KEYS)
        and all(type(value) is bool for value in material_availability.values())
    )
    if not material_availability_valid:
        errors.append("gate_material_availability_contract_mismatch")

    allowed_source_labels_valid = _allowed_source_labels_are_valid(
        gates.get("allowed_source_labels"),
        material_availability if type(material_availability) is dict else {},
    )
    if not allowed_source_labels_valid:
        errors.append("gate_allowed_source_labels_contract_mismatch")

    boundary_checks = payload.get("boundary_checks")
    if not isinstance(boundary_checks, dict):
        errors.append("boundary_checks_missing_or_not_object")
    else:
        model_contract_version = boundary_checks.get("contract_version")
        if type(model_contract_version) is not str or model_contract_version != expected_version:
            errors.append("boundary_contract_version_mismatch")

        facts = boundary_checks.get("facts")
        if not isinstance(facts, dict):
            errors.append("boundary_facts_missing_or_not_object")
        else:
            for fact_name in EXPECTED_REQUIRED_FACTS:
                fact = facts.get(fact_name)
                if type(fact) is not dict:
                    errors.append("missing_boundary_fact:" + _text(fact_name))
                    continue

                if set(fact) != set(EXPECTED_FACT_KEYS):
                    errors.append("boundary_fact_keys_mismatch:" + fact_name)
                    continue

                value = fact.get("value")
                evidence_sources = fact.get("evidence_sources")
                evidence_detail = fact.get("evidence_detail")
                if type(value) is not bool:
                    errors.append("boundary_fact_value_not_bool:" + fact_name)
                if type(evidence_sources) is not list:
                    errors.append("boundary_fact_evidence_sources_not_list:" + fact_name)
                elif any(type(source) is not str for source in evidence_sources):
                    errors.append("boundary_fact_evidence_source_not_string:" + fact_name)
                if type(evidence_detail) is not str:
                    errors.append("boundary_fact_evidence_detail_not_string:" + fact_name)

                if value is True:
                    has_source = type(evidence_sources) is list and any(
                        type(source) is str and bool(source.strip()) for source in evidence_sources
                    )
                    has_detail = type(evidence_detail) is str and bool(evidence_detail.strip())
                    if not has_source or not has_detail:
                        errors.append("true_fact_without_evidence:" + fact_name)

    payload_rules_version = payload.get("rules_version")
    if type(payload_rules_version) is not str or payload_rules_version != expected_version:
        errors.append("payload_rules_version_mismatch")
    return errors


def _validate_final_results_structure(payload):
    errors = []
    results = payload.get("final_results")
    if type(results) is not list:
        return ["final_results_missing_or_not_list"]
    if len(results) != 19:
        errors.append("final_results_count_mismatch")

    valid_ids = set()
    seen_ids = set()
    for index, item in enumerate(results):
        if type(item) is not dict:
            errors.append("final_result_item_not_object:index_%d" % index)
            continue

        category_id = item.get("category_id")
        if type(category_id) is not int:
            errors.append("final_result_category_id_not_exact_int:index_%d" % index)
            continue
        if category_id < 1 or category_id > 19:
            errors.append("final_result_category_id_out_of_range:%d" % category_id)
        elif category_id in seen_ids:
            errors.append("duplicate_final_result_category_id:%d" % category_id)
        else:
            seen_ids.add(category_id)
            valid_ids.add(category_id)

        if item.get("category_name") != EXPECTED_CATEGORY_NAMES.get(category_id):
            errors.append("final_result_category_name_mismatch:%d" % category_id)

        decision = item.get("decision")
        if type(decision) is not str or decision not in {"hit", "no_hit", "unable_to_judge"}:
            errors.append("invalid_final_result_decision:%d" % category_id)

        evidence = item.get("evidence")
        if type(evidence) is not list:
            errors.append("final_result_evidence_not_list:%d" % category_id)
        else:
            for evidence_index, entry in enumerate(evidence):
                if type(entry) is not dict:
                    errors.append(
                        "final_result_evidence_item_not_object:%d:index_%d"
                        % (category_id, evidence_index)
                    )
                    continue
                for field_name in ("source", "quote_or_visual_detail", "reason"):
                    if type(entry.get(field_name)) is not str:
                        errors.append(
                            "final_result_evidence_%s_not_string:%d:index_%d"
                            % (field_name, category_id, evidence_index)
                        )
                    elif field_name == "reason" and not entry[field_name].strip():
                        errors.append(
                            "invalid_final_result_evidence_reason:%d" % category_id
                        )

        evidence_count = item.get("evidence_count")
        if type(evidence_count) is not int:
            errors.append("final_result_evidence_count_not_exact_int:%d" % category_id)
        elif type(evidence) is list and evidence_count != len(evidence):
            errors.append("final_result_evidence_count_mismatch:%d" % category_id)

        if type(item.get("judge_reason")) is not str:
            errors.append("final_result_judge_reason_not_string:%d" % category_id)

        materials_used = item.get("materials_used")
        if type(materials_used) is not list:
            errors.append("final_result_materials_used_not_list:%d" % category_id)
        else:
            for material_index, material in enumerate(materials_used):
                if type(material) is not str:
                    errors.append(
                        "final_result_material_not_string:%d:index_%d"
                        % (category_id, material_index)
                    )

        if type(item.get("product_image_used")) is not bool:
            errors.append("final_result_product_image_used_not_bool:%d" % category_id)
        if type(item.get("product_image_permission_ok")) is not bool:
            errors.append(
                "final_result_product_image_permission_ok_not_bool:%d" % category_id
            )

        priority_rules = item.get("priority_rule_applied")
        if type(priority_rules) is not list:
            errors.append("final_result_priority_rule_applied_not_list:%d" % category_id)
        else:
            for rule_index, rule in enumerate(priority_rules):
                if type(rule) is not str:
                    errors.append(
                        "final_result_priority_rule_not_string:%d:index_%d"
                        % (category_id, rule_index)
                    )

    if valid_ids != set(range(1, 20)):
        errors.append("final_result_category_ids_mismatch")
    return errors


def _fact(payload, fact_name):
    return payload["boundary_checks"]["facts"][fact_name]


def _source_material(source):
    if type(source) is not str:
        return None
    if source == "Comment Interaction":
        return "comment_interaction"
    if re.fullmatch(r"Pearl product #[1-9][0-9]* image", source):
        return "pearl_product_image"
    if re.fullmatch(r"Pearl product #[1-9][0-9]* title", source):
        return "pearl_product_title"
    if re.fullmatch(r"Segment #[1-9][0-9]* frame", source):
        return "segment_frame"
    if re.fullmatch(r"Segment #[1-9][0-9]* ASR", source):
        return "segment_asr"
    if re.fullmatch(r"Segment #[1-9][0-9]* (?:frame )?visible text", source):
        return "segment_frame_visible_text"
    return None


def _allowed_source_labels_are_valid(labels, material_availability):
    if type(labels) is not list:
        return False
    if any(type(label) is not str or not label.strip() for label in labels):
        return False
    if labels != sorted(set(labels)):
        return False
    for label in labels:
        material = _source_material(label)
        if material is None or not _material_is_available(material, material_availability):
            return False
    return True


def _availability_key(material):
    if material == "segment_frame_visible_text":
        return "segment_frame"
    return material


def _material_is_available(material, material_availability):
    availability_key = _availability_key(material)
    return material_availability.get(availability_key) is True


def _meets_evidence_threshold(category_id, evidence):
    return len(evidence) >= MINIMUM_DISTINCT_EVIDENCE_UNITS[category_id]


def _fact_evidence(
    payload,
    category_id,
    fact_name,
    material_availability,
    allowed_source_labels,
):
    fact = _fact(payload, fact_name)
    if fact["value"] is not True:
        return []

    allowed_materials = CATEGORY_ALLOWED_MATERIALS.get(category_id, frozenset())
    detail = _text(fact["evidence_detail"])
    evidence = []
    for source in fact["evidence_sources"]:
        if source not in allowed_source_labels:
            continue
        material = _source_material(source)
        if material not in allowed_materials:
            continue
        if material not in FACT_ALLOWED_MATERIALS[fact_name]:
            continue
        if not _material_is_available(material, material_availability):
            continue
        if (
            category_id == 12
            and fact_name == "concrete_live_effect_claim_found"
            and material not in {"segment_frame", "segment_asr"}
        ):
            continue
        evidence.append(
            {
                "source": source,
                "quote_or_visual_detail": detail,
                "reason": "经边界事实核验：" + fact_name,
            }
        )
    return evidence


def _fact_true(
    payload,
    category_id,
    fact_name,
    material_availability,
    allowed_source_labels,
):
    return bool(
        _fact_evidence(
            payload,
            category_id,
            fact_name,
            material_availability,
            allowed_source_labels,
        )
    )


def _required_path_passes(
    payload,
    category_id,
    definition,
    material_availability,
    allowed_source_labels,
):
    return all(
        _fact_true(
            payload,
            category_id,
            name,
            material_availability,
            allowed_source_labels,
        )
        for name in definition.get("required_true", [])
    ) and not any(
        _fact_true(
            payload,
            category_id,
            name,
            material_availability,
            allowed_source_labels,
        )
        for name in definition.get("blocked_true", [])
    )


def _gate_passes(
    payload,
    category_id,
    definition,
    material_availability,
    allowed_source_labels,
):
    if definition.get("disabled") is True:
        return False
    if any(
        _fact_true(
            payload,
            category_id,
            name,
            material_availability,
            allowed_source_labels,
        )
        for name in definition.get("alternative_true", [])
    ):
        return True
    return _required_path_passes(
        payload,
        category_id,
        definition,
        material_availability,
        allowed_source_labels,
    )


def _path_evidence(
    payload,
    category_id,
    fact_names,
    material_availability,
    allowed_source_labels,
):
    evidence = []
    seen = set()
    for fact_name in fact_names:
        fact_entries = _fact_evidence(
            payload,
            category_id,
            fact_name,
            material_availability,
            allowed_source_labels,
        )
        if not fact_entries:
            return None
        for entry in fact_entries:
            dedupe_key = entry["source"]
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            evidence.append(entry)
    return evidence


def _gate_evidence(
    payload,
    category_id,
    definition,
    material_availability,
    allowed_source_labels,
    allow_alternative=True,
):
    if allow_alternative:
        for fact_name in definition.get("alternative_true", []):
            if _fact_true(
                payload,
                category_id,
                fact_name,
                material_availability,
                allowed_source_labels,
            ):
                alternative_evidence = _path_evidence(
                    payload,
                    category_id,
                    [fact_name],
                    material_availability,
                    allowed_source_labels,
                )
                if _meets_evidence_threshold(category_id, alternative_evidence):
                    return alternative_evidence
    if not _required_path_passes(
        payload,
        category_id,
        definition,
        material_availability,
        allowed_source_labels,
    ):
        return None
    required_evidence = _path_evidence(
        payload,
        category_id,
        definition.get("required_true", []),
        material_availability,
        allowed_source_labels,
    )
    if required_evidence and _meets_evidence_threshold(category_id, required_evidence):
        return required_evidence
    return None


def _gate_failure_reason(
    payload,
    category_id,
    definition,
    material_availability,
    allowed_source_labels,
):
    if definition.get("disabled") is True:
        return "类别%d在当前规则版本中已禁用，强制改判为不命中。" % category_id
    blocked = [
        fact_name
        for fact_name in definition.get("blocked_true", [])
        if _fact_true(
            payload,
            category_id,
            fact_name,
            material_availability,
            allowed_source_labels,
        )
    ]
    if blocked:
        return "边界阻断事实成立，改判为不命中：" + "、".join(blocked) + "。"
    missing = [
        fact_name
        for fact_name in definition.get("required_true", [])
        if not _fact_true(
            payload,
            category_id,
            fact_name,
            material_availability,
            allowed_source_labels,
        )
    ]
    unsupported = [
        fact_name
        for fact_name in missing
        if _fact(payload, fact_name)["value"] is True
    ]
    if unsupported:
        return "边界必要事实缺少可用的允许材料证据，改判为不命中：" + "、".join(unsupported) + "。"
    return "边界必要事实不完整，改判为不命中：" + "、".join(missing) + "。"


def _append_priority_rule(item, rule):
    existing = item.get("priority_rule_applied")
    if type(existing) is not list:
        existing = []
    updated = [value for value in existing if type(value) is str and value]
    if rule and rule not in updated:
        updated.append(rule)
    item["priority_rule_applied"] = updated


def _decision_confidence(item):
    confidence = item.get("confidence")
    if type(confidence) is str and confidence in {"high", "medium", "low"}:
        return confidence
    return "medium"


def _canonical_priority_rules(item):
    canonical = []
    for rule in item.get("priority_rule_applied", []):
        if rule.strip() and rule not in canonical:
            canonical.append(rule)
    return canonical


def _set_evidence_fields(item, evidence):
    evidence = list(evidence)
    materials_used = sorted(
        {
            material
            for material in (_source_material(entry.get("source")) for entry in evidence)
            if material
        }
    )
    item["evidence"] = evidence
    item["evidence_count"] = len(evidence)
    item["materials_used"] = materials_used
    item["product_image_used"] = "pearl_product_image" in materials_used


def _authorized_model_evidence(
    item,
    category_id,
    material_availability,
    allowed_source_labels,
):
    allowed_materials = CATEGORY_ALLOWED_MATERIALS[category_id]
    authorized = []
    seen = set()
    for entry in item["evidence"]:
        source = entry["source"]
        detail = entry["quote_or_visual_detail"]
        if source not in allowed_source_labels:
            continue
        material = _source_material(source)
        if material not in allowed_materials:
            continue
        if not _material_is_available(material, material_availability):
            continue
        if not source or not detail.strip():
            continue
        dedupe_key = source
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        authorized.append(entry)
    return authorized


def _append_audit(item, from_decision, to_decision, reason, priority_rule, audit):
    audit.append(
        {
            "category_id": item.get("category_id"),
            "from_decision": from_decision,
            "to_decision": to_decision,
            "reason": reason,
            "priority_rule_applied": priority_rule,
        }
    )


def _record_priority_association(item, reason, priority_rule, audit):
    decision = item.get("decision")
    _append_priority_rule(item, priority_rule)
    _append_audit(
        item,
        decision,
        decision,
        reason,
        priority_rule,
        audit,
    )


def _set_decision(
    item,
    decision,
    reason,
    evidence,
    priority_rule,
    audit,
):
    previous_decision = item.get("decision")
    confidence = _decision_confidence(item)
    evidence = list(evidence or []) if decision == "hit" else []

    item["decision"] = decision
    item["judge_reason"] = reason
    _set_evidence_fields(item, evidence)
    item["confidence"] = confidence
    _append_priority_rule(item, priority_rule)

    if previous_decision != decision:
        _append_audit(
            item,
            previous_decision,
            decision,
            reason,
            priority_rule,
            audit,
        )


def _results_by_id(payload):
    results = payload.get("final_results")
    if type(results) is not list:
        return {}
    return {
        item.get("category_id"): item
        for item in results
        if type(item) is dict and type(item.get("category_id")) is int
    }


def _canonicalize_results(
    payload,
    results_by_id,
    definitions,
    material_availability,
    allowed_source_labels,
    audit,
):
    for category_id in sorted(results_by_id):
        item = results_by_id[category_id]
        original_confidence = item.get("confidence")
        canonical_confidence = _decision_confidence(item)
        item["confidence"] = canonical_confidence
        item["priority_rule_applied"] = _canonical_priority_rules(item)
        if canonical_confidence != original_confidence:
            rule = "boundary_confidence_normalization_category_%d" % category_id
            _record_priority_association(
                item,
                "已将类别%d的无效置信度规范为medium。" % category_id,
                rule,
                audit,
            )

        definition = definitions.get(str(category_id))
        if (
            item.get("decision") == "hit"
            and definition
            and definition.get("disabled") is True
        ):
            continue

        if item.get("decision") != "hit":
            had_stale_hit_fields = bool(
                item.get("evidence")
                or item.get("evidence_count")
                or item.get("materials_used")
                or item.get("product_image_used") is True
            )
            _set_evidence_fields(item, [])
            if had_stale_hit_fields:
                rule = "boundary_non_hit_cleanup_category_%d" % category_id
                _record_priority_association(
                    item,
                    "已清理类别%d非命中判定中的陈旧命中证据字段。" % category_id,
                    rule,
                    audit,
                )
            continue

        original_evidence = list(item["evidence"])
        original_evidence_count = item.get("evidence_count")
        original_materials = list(item.get("materials_used", []))
        original_product_image_used = item.get("product_image_used")
        authorized_evidence = _authorized_model_evidence(
            item,
            category_id,
            material_availability,
            allowed_source_labels,
        )
        if _meets_evidence_threshold(category_id, authorized_evidence):
            _set_evidence_fields(item, authorized_evidence)
            if authorized_evidence != original_evidence:
                rule = "boundary_evidence_filter_category_%d" % category_id
                _record_priority_association(
                    item,
                    "已移除类别%d中未授权或重复的模型证据。" % category_id,
                    rule,
                    audit,
                )
            elif (
                item["evidence_count"] != original_evidence_count
                or item["materials_used"] != original_materials
                or item["product_image_used"] != original_product_image_used
            ):
                rule = "boundary_evidence_metadata_repair_category_%d" % category_id
                _record_priority_association(
                    item,
                    "已根据类别%d的最终有效证据重算材料与商品图标志。" % category_id,
                    rule,
                    audit,
                )
            continue

        gate_evidence = None
        if definition and _gate_passes(
            payload,
            category_id,
            definition,
            material_availability,
            allowed_source_labels,
        ):
            gate_evidence = _gate_evidence(
                payload,
                category_id,
                definition,
                material_availability,
                allowed_source_labels,
            )
        if gate_evidence:
            _set_evidence_fields(item, gate_evidence)
            rule = "boundary_evidence_repair_category_%d" % category_id
            _record_priority_association(
                item,
                "已用可信边界事实证据修复类别%d的模型命中证据。" % category_id,
                rule,
                audit,
            )
            continue

        _set_decision(
            item,
            "no_hit",
            "模型命中缺少该类别允许且当前可用的有效证据，改判为不命中。",
            [],
            "boundary_evidence_category_%d" % category_id,
            audit,
        )


def _apply_general_gates(
    payload,
    results_by_id,
    definitions,
    material_availability,
    allowed_source_labels,
    audit,
):
    for category_text in sorted(definitions, key=int):
        category_id = int(category_text)
        item = results_by_id.get(category_id)
        if item is None:
            continue
        definition = definitions[category_text]
        rule = "boundary_gate_category_%d" % category_id

        if definition.get("disabled") is True:
            if item.get("decision") != "no_hit":
                _set_decision(
                    item,
                    "no_hit",
                    _gate_failure_reason(
                        payload,
                        category_id,
                        definition,
                        material_availability,
                        allowed_source_labels,
                    ),
                    [],
                    rule,
                    audit,
                )
            continue

        gate_passes = _gate_passes(
            payload,
            category_id,
            definition,
            material_availability,
            allowed_source_labels,
        )
        if item.get("decision") == "hit" and not gate_passes:
            _set_decision(
                item,
                "no_hit",
                _gate_failure_reason(
                    payload,
                    category_id,
                    definition,
                    material_availability,
                    allowed_source_labels,
                ),
                [],
                rule,
                audit,
            )
            continue

        if item.get("decision") == "hit":
            evidence = _gate_evidence(
                payload,
                category_id,
                definition,
                material_availability,
                allowed_source_labels,
            )
            if not evidence:
                _set_decision(
                    item,
                    "no_hit",
                    "边界必要事实缺少可用的允许材料证据，改判为不命中。",
                    [],
                    rule,
                    audit,
                )
            continue

        if not gate_passes:
            continue

        evidence = _gate_evidence(
            payload,
            category_id,
            definition,
            material_availability,
            allowed_source_labels,
        )
        if not evidence:
            continue
        _set_decision(
            item,
            "hit",
            "边界必要事实与有效材料证据完整，判定为命中。",
            evidence,
            rule,
            audit,
        )


def _apply_reroutes(
    payload,
    results_by_id,
    definitions,
    material_availability,
    allowed_source_labels,
    original_hit_ids,
    audit,
):
    applied_rules = []
    for reroute in _mutable(EXPECTED_REROUTES):
        source_ids = [
            category_id
            for category_id in reroute["from"]
            if category_id in original_hit_ids
        ]
        if not source_ids:
            continue

        target_id = reroute["to"]
        definition = definitions[str(target_id)]
        if target_id == 15 and source_ids == [8]:
            if not _required_path_passes(
                payload,
                target_id,
                definition,
                material_availability,
                allowed_source_labels,
            ):
                continue
            evidence = _gate_evidence(
                payload,
                target_id,
                definition,
                material_availability,
                allowed_source_labels,
                allow_alternative=False,
            )
        else:
            if not _gate_passes(
                payload,
                target_id,
                definition,
                material_availability,
                allowed_source_labels,
            ):
                continue
            evidence = _gate_evidence(
                payload,
                target_id,
                definition,
                material_availability,
                allowed_source_labels,
            )
        if not evidence:
            continue

        rule = reroute["rule"]
        target = results_by_id.get(target_id)
        if target is None:
            continue

        for source_id in source_ids:
            source = results_by_id.get(source_id)
            if source is None:
                continue
            source_reason = "优先级规则%s关联类别%d至类别%d。" % (
                rule,
                source_id,
                target_id,
            )
            if source.get("decision") == "no_hit":
                _record_priority_association(
                    source,
                    source_reason,
                    rule,
                    audit,
                )
            else:
                _set_decision(
                    source,
                    "no_hit",
                    source_reason,
                    [],
                    rule,
                    audit,
                )

        target_reason = "优先级规则%s关联类别%s至类别%d。" % (
            rule,
            "、".join(str(category_id) for category_id in source_ids),
            target_id,
        )
        if target.get("decision") == "hit":
            _record_priority_association(
                target,
                target_reason,
                rule,
                audit,
            )
        else:
            _set_decision(
                target,
                "hit",
                target_reason,
                evidence,
                rule,
                audit,
            )
        if rule not in applied_rules:
            applied_rules.append(rule)
    return sorted(applied_rules)


def _sync_decision_lists(payload):
    results = payload.get("final_results")
    if type(results) is not list:
        return
    results.sort(
        key=lambda item: item.get("category_id", 0) if type(item) is dict else 0
    )
    hit_ids = {
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "hit"
    }
    no_hit_ids = {
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "no_hit"
    }
    unable_ids = {
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "unable_to_judge"
    }
    payload["hit_category_ids"] = sorted(hit_ids)
    payload["no_hit_category_ids"] = sorted(no_hit_ids)
    payload["unable_to_judge_category_ids"] = sorted(unable_ids)

    category_ids = {
        item.get("category_id") for item in results if type(item) is dict
    }
    payload["coverage_check"] = {
        "expected_category_count": 19,
        "actual_category_count": len(results),
        "missing_category_ids": sorted(set(range(1, 20)) - category_ids),
        "extra_category_ids": sorted(category_ids - set(range(1, 20))),
        "hit_no_hit_overlap_category_ids": sorted(
            (hit_ids & no_hit_ids) | (hit_ids & unable_ids) | (no_hit_ids & unable_ids)
        ),
    }


def _threshold_recheck_warnings(payload):
    policy_checks = payload.get("policy_checks")
    if type(policy_checks) is not dict:
        return []
    warnings = policy_checks.get("threshold_recheck_warnings")
    if type(warnings) is not list or any(type(item) is not str for item in warnings):
        return []
    return list(warnings)


def _sync_permission_and_policy(payload, applied_rules, threshold_warnings, audit):
    violations = []
    for item in payload["final_results"]:
        category_id = item["category_id"]
        permission_ok = not (
            item["decision"] == "hit"
            and item["product_image_used"] is True
            and category_id not in PRODUCT_IMAGE_ALLOWED_CATEGORY_IDS
        )
        if item.get("product_image_permission_ok") is not permission_ok:
            item["product_image_permission_ok"] = permission_ok
            rule = "boundary_product_permission_repair_category_%d" % category_id
            _record_priority_association(
                item,
                "已根据类别%d的最终证据重算商品图权限标志。" % category_id,
                rule,
                audit,
            )
        if not permission_ok:
            violations.append(category_id)

    payload["policy_checks"] = {
        "product_image_permission_violations": sorted(violations),
        "exclusive_priority_applied": list(applied_rules),
        "threshold_recheck_warnings": threshold_warnings,
    }


def _render_report(payload):
    results = payload.get("final_results")
    if type(results) is not list:
        results = []
    hits = [item for item in results if type(item) is dict and item.get("decision") == "hit"]
    no_hits = [
        item for item in results if type(item) is dict and item.get("decision") == "no_hit"
    ]
    unable = [
        item
        for item in results
        if type(item) is dict and item.get("decision") == "unable_to_judge"
    ]

    lines = ["识别到的低质问题："]
    if not hits:
        lines.append("未识别到低质问题。")
    for index, item in enumerate(hits, start=1):
        lines.append("%d. 识别到【%s】" % (index, _text(item.get("category_name"))))
        lines.append("相关佐证：")
        for evidence_index, evidence in enumerate(item.get("evidence", []), start=1):
            if type(evidence) is not dict:
                continue
            lines.append(
                "证据%d：%s｜%s｜%s"
                % (
                    evidence_index,
                    _text(evidence.get("source")),
                    _text(evidence.get("quote_or_visual_detail")),
                    _text(evidence.get("reason")),
                )
            )
        lines.append("裁判理由：" + _text(item.get("judge_reason")))

    lines.append("")
    lines.append("无低质问题：")
    if not no_hits:
        lines.append("无。")
    for item in no_hits:
        lines.append(
            "无【%s】：%s"
            % (_text(item.get("category_name")), _text(item.get("judge_reason")))
        )

    lines.append("")
    lines.append("无法判断：")
    if not unable:
        lines.append("无。")
    for item in unable:
        lines.append(
            "无法判断【%s】：%s"
            % (_text(item.get("category_name")), _text(item.get("judge_reason")))
        )
    return "\n".join(lines)


def _finalize_payload(payload, gates):
    definitions = _mutable(EXPECTED_GATE_DEFINITIONS)
    material_availability = gates["material_availability"]
    allowed_source_labels = frozenset(gates["allowed_source_labels"])
    threshold_warnings = _threshold_recheck_warnings(payload)
    results_by_id = _results_by_id(payload)
    original_hit_ids = {
        category_id
        for category_id, item in results_by_id.items()
        if item.get("decision") == "hit"
    }
    audit = []
    _canonicalize_results(
        payload,
        results_by_id,
        definitions,
        material_availability,
        allowed_source_labels,
        audit,
    )
    _apply_general_gates(
        payload,
        results_by_id,
        definitions,
        material_availability,
        allowed_source_labels,
        audit,
    )
    applied_rules = _apply_reroutes(
        payload,
        results_by_id,
        definitions,
        material_availability,
        allowed_source_labels,
        original_hit_ids,
        audit,
    )
    _sync_decision_lists(payload)
    _sync_permission_and_policy(
        payload,
        applied_rules,
        threshold_warnings,
        audit,
    )
    payload["boundary_overrides"] = audit
    return audit


def _failure(errors):
    return {
        "finalized_judge_output": "",
        "finalized_final_json": "",
        "finalization_status": "fail",
        "boundary_override_log": "[]",
        "finalizer_errors": json.dumps(errors, ensure_ascii=False),
    }


def finalize_judge_output(params):
    if not isinstance(params, dict):
        params = {}

    try:
        payload = _extract_payload(params.get("judge_output"))
    except Exception as exc:
        error = _text(exc)
        if error in {
            "final_json_marker_missing",
            "final_json_not_object",
            "final_json_fence_unclosed",
        }:
            return _failure([error])
        return _failure(["final_json_parse_failed:" + error])

    try:
        gates = _load_gates(params.get("boundary_gates_json"))
    except Exception as exc:
        return _failure([_text(exc) or "boundary_gates_load_failed"])

    expected_version = params.get("boundary_contract_version")
    errors = _validate_contract(payload, gates, expected_version)
    input_rules_version = params.get("rules_version")
    if type(input_rules_version) is not str or input_rules_version != expected_version:
        errors.append("rules_version_mismatch")
    input_room_id = params.get("room_id")
    if type(input_room_id) is not str or not input_room_id.strip():
        errors.append("room_id_missing_or_invalid")
    elif type(payload.get("room_id")) is not str or payload.get("room_id") != input_room_id:
        errors.append("room_id_mismatch")
    if errors:
        return _failure(errors)

    try:
        structure_errors = _validate_final_results_structure(payload)
        if structure_errors:
            return _failure(structure_errors)
        audit = _finalize_payload(payload, gates)
        serialized_payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        report = _render_report(payload)
        serialized_audit = json.dumps(audit, ensure_ascii=False, allow_nan=False)
        return {
            "finalized_judge_output": report + "\n\nFINAL_JSON:\n" + serialized_payload,
            "finalized_final_json": serialized_payload,
            "finalization_status": "warning" if audit else "pass",
            "boundary_override_log": serialized_audit,
            "finalizer_errors": "[]",
        }
    except Exception as exc:
        return _failure(["finalization_failed:" + _text(exc)])


async def main(args: Args) -> Output:
    return finalize_judge_output(args.params)
