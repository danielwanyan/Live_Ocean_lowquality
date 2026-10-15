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
        14: frozenset(
            ("segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction")
        ),
        15: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
        ),
        18: frozenset(("segment_frame", "segment_asr", "comment_interaction")),
        19: frozenset(
            ("segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image")
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


def _fact(payload, fact_name):
    return payload["boundary_checks"]["facts"][fact_name]


def _fact_true(payload, fact_name):
    return _fact(payload, fact_name)["value"] is True


def _required_path_passes(payload, definition):
    return all(_fact_true(payload, name) for name in definition.get("required_true", [])) and not any(
        _fact_true(payload, name) for name in definition.get("blocked_true", [])
    )


def _gate_passes(payload, definition):
    if definition.get("disabled") is True:
        return False
    if any(_fact_true(payload, name) for name in definition.get("alternative_true", [])):
        return True
    return _required_path_passes(payload, definition)


def _source_material(source):
    source = _text(source)
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


def _fact_evidence(payload, category_id, fact_name):
    fact = _fact(payload, fact_name)
    if fact["value"] is not True:
        return []

    allowed_materials = CATEGORY_ALLOWED_MATERIALS.get(category_id, frozenset())
    detail = _text(fact["evidence_detail"])
    evidence = []
    for source in fact["evidence_sources"]:
        normalized_source = _text(source)
        material = _source_material(normalized_source)
        if material not in allowed_materials:
            continue
        if (
            category_id == 12
            and fact_name == "concrete_live_effect_claim_found"
            and material not in {"segment_frame", "segment_asr"}
        ):
            continue
        evidence.append(
            {
                "source": normalized_source,
                "quote_or_visual_detail": detail,
                "reason": "经边界事实核验：" + fact_name,
            }
        )
    return evidence


def _path_evidence(payload, category_id, fact_names):
    evidence = []
    seen = set()
    for fact_name in fact_names:
        fact_entries = _fact_evidence(payload, category_id, fact_name)
        if not fact_entries:
            return None
        for entry in fact_entries:
            dedupe_key = (entry["source"], entry["quote_or_visual_detail"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            evidence.append(entry)
    return evidence


def _gate_evidence(payload, category_id, definition, allow_alternative=True):
    if allow_alternative:
        for fact_name in definition.get("alternative_true", []):
            if _fact_true(payload, fact_name):
                alternative_evidence = _path_evidence(payload, category_id, [fact_name])
                if alternative_evidence:
                    return alternative_evidence
    if not _required_path_passes(payload, definition):
        return None
    return _path_evidence(payload, category_id, definition.get("required_true", []))


def _gate_failure_reason(payload, category_id, definition):
    if definition.get("disabled") is True:
        return "类别%d在当前规则版本中已禁用，强制改判为不命中。" % category_id
    blocked = [
        fact_name
        for fact_name in definition.get("blocked_true", [])
        if _fact_true(payload, fact_name)
    ]
    if blocked:
        return "边界阻断事实成立，改判为不命中：" + "、".join(blocked) + "。"
    missing = [
        fact_name
        for fact_name in definition.get("required_true", [])
        if not _fact_true(payload, fact_name)
    ]
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
    if confidence in {"high", "medium", "low"}:
        return confidence
    return "medium"


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
    materials_used = []
    for entry in evidence:
        material = _source_material(entry.get("source"))
        if material and material not in materials_used:
            materials_used.append(material)
    materials_used.sort()

    item["decision"] = decision
    item["judge_reason"] = reason
    item["evidence"] = evidence
    item["evidence_count"] = len(evidence)
    item["materials_used"] = materials_used
    item["product_image_used"] = "pearl_product_image" in materials_used
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


def _apply_general_gates(payload, results_by_id, definitions, audit):
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
                    _gate_failure_reason(payload, category_id, definition),
                    [],
                    rule,
                    audit,
                )
            continue

        gate_passes = _gate_passes(payload, definition)
        if item.get("decision") == "hit" and not gate_passes:
            _set_decision(
                item,
                "no_hit",
                _gate_failure_reason(payload, category_id, definition),
                [],
                rule,
                audit,
            )
            continue

        if item.get("decision") == "hit":
            evidence = _gate_evidence(payload, category_id, definition)
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

        evidence = _gate_evidence(payload, category_id, definition)
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


def _apply_reroutes(payload, results_by_id, definitions, original_hit_ids, audit):
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
            if not _required_path_passes(payload, definition):
                continue
            evidence = _gate_evidence(
                payload,
                target_id,
                definition,
                allow_alternative=False,
            )
        else:
            if not _gate_passes(payload, definition):
                continue
            evidence = _gate_evidence(payload, target_id, definition)
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
    payload["hit_category_ids"] = sorted(
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "hit"
    )
    payload["no_hit_category_ids"] = sorted(
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "no_hit"
    )
    payload["unable_to_judge_category_ids"] = sorted(
        item["category_id"]
        for item in results
        if type(item) is dict and item.get("decision") == "unable_to_judge"
    )

    category_ids = {
        item.get("category_id") for item in results if type(item) is dict
    }
    coverage = payload.get("coverage_check")
    if type(coverage) is dict:
        coverage["expected_category_count"] = 19
        coverage["actual_category_count"] = len(results)
        coverage["missing_category_ids"] = sorted(set(range(1, 20)) - category_ids)
        coverage["extra_category_ids"] = sorted(category_ids - set(range(1, 20)))
        coverage["hit_no_hit_overlap_category_ids"] = []


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


def _finalize_payload(payload):
    definitions = _mutable(EXPECTED_GATE_DEFINITIONS)
    results_by_id = _results_by_id(payload)
    original_hit_ids = {
        category_id
        for category_id, item in results_by_id.items()
        if item.get("decision") == "hit"
    }
    audit = []
    _apply_general_gates(payload, results_by_id, definitions, audit)
    applied_rules = _apply_reroutes(
        payload,
        results_by_id,
        definitions,
        original_hit_ids,
        audit,
    )
    policy_checks = payload.get("policy_checks")
    if type(policy_checks) is dict:
        policy_checks["exclusive_priority_applied"] = applied_rules
    payload["boundary_overrides"] = audit
    _sync_decision_lists(payload)
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
    if errors:
        return _failure(errors)

    audit = _finalize_payload(payload)
    try:
        serialized_payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        return _failure(["final_json_serialize_failed:" + _text(exc)])
    report = _render_report(payload)
    return {
        "finalized_judge_output": report + "\n\nFINAL_JSON:\n" + serialized_payload,
        "finalized_final_json": serialized_payload,
        "finalization_status": "warning" if audit else "pass",
        "boundary_override_log": json.dumps(audit, ensure_ascii=False, allow_nan=False),
        "finalizer_errors": "[]",
    }


async def main(args: Args) -> Output:
    return finalize_judge_output(args.params)
