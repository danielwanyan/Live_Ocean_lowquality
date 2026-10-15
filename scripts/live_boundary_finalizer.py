import json


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

    try:
        serialized_payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        return _failure(["final_json_serialize_failed:" + _text(exc)])
    return {
        "finalized_judge_output": "FINAL_JSON:\n" + serialized_payload,
        "finalized_final_json": serialized_payload,
        "finalization_status": "pass",
        "boundary_override_log": "[]",
        "finalizer_errors": "[]",
    }


async def main(args: Args) -> Output:
    return finalize_judge_output(args.params)
