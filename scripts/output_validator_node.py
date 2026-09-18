import json


ALLOWED_PRODUCT_IMAGE_CATEGORY_IDS = {3, 5, 6, 9, 10, 12, 15, 16, 17}
ALL_CATEGORY_IDS = set(range(1, 20))
ALLOWED_DECISIONS = {"hit", "no_hit", "unable_to_judge"}


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _extract_final_json_text(judge_output):
    text = _text(judge_output)
    marker = "FINAL_JSON:"
    if marker not in text:
        raise ValueError("final_json_marker_missing")
    json_text = text.split(marker, 1)[1].strip()
    if json_text.startswith("```json"):
        json_text = json_text[len("```json"):].strip()
    if json_text.startswith("```"):
        json_text = json_text[len("```"):].strip()
    if json_text.endswith("```"):
        json_text = json_text[:-3].strip()
    return json_text


def _parse_id_list(value):
    if isinstance(value, list):
        return [_to_int(item) for item in value]
    return []


def _has_non_empty_evidence(item):
    evidence = item.get("evidence")
    evidence_count = _to_int(item.get("evidence_count"), 0)
    return evidence_count > 0 and isinstance(evidence, list) and len(evidence) > 0


def _check_decision_lists(payload, errors):
    hit_ids = set(_parse_id_list(payload.get("hit_category_ids")))
    no_hit_ids = set(_parse_id_list(payload.get("no_hit_category_ids")))
    unable_ids = set(_parse_id_list(payload.get("unable_to_judge_category_ids")))
    combined = hit_ids | no_hit_ids | unable_ids
    if combined != ALL_CATEGORY_IDS:
        errors.append("decision_id_lists_do_not_cover_1_to_19")
    if hit_ids & no_hit_ids or hit_ids & unable_ids or no_hit_ids & unable_ids:
        errors.append("decision_id_lists_overlap")
    return hit_ids, no_hit_ids, unable_ids


def _check_priority_conflicts(results, errors):
    by_id = {item.get("category_id"): item for item in results if isinstance(item, dict)}
    category_3 = by_id.get(3, {})
    category_6 = by_id.get(6, {})
    if category_3.get("decision") == "hit" and category_6.get("decision") == "hit":
        reason_3 = json.dumps(category_3.get("evidence", []), ensure_ascii=False).lower()
        reason_6 = json.dumps(category_6.get("evidence", []), ensure_ascii=False).lower()
        if "unrelated" in reason_3 and "unrelated" in reason_6:
            errors.append("priority_conflict_category_3_and_6")
    category_1 = by_id.get(1, {})
    category_19 = by_id.get(19, {})
    if category_1.get("decision") == "hit" and category_19.get("decision") == "hit":
        text_1 = json.dumps(category_1.get("evidence", []), ensure_ascii=False).lower()
        text_19 = json.dumps(category_19.get("evidence", []), ensure_ascii=False).lower()
        if "sexual" in text_1 and "sexual" in text_19:
            errors.append("priority_conflict_category_1_and_19")
    if category_19.get("decision") == "hit":
        errors.append("disabled_category_19_hit")


def _validate_payload(payload, params):
    errors = []
    warnings = []
    results = payload.get("final_results")
    if not isinstance(results, list):
        errors.append("final_results_missing_or_not_list")
        results = []

    category_ids = [item.get("category_id") for item in results if isinstance(item, dict)]
    if len(results) != 19 or set(category_ids) != ALL_CATEGORY_IDS:
        errors.append("category_ids_not_exact_1_to_19")

    for item in results:
        if not isinstance(item, dict):
            errors.append("final_result_item_not_object")
            continue
        category_id = item.get("category_id")
        decision = item.get("decision")
        if decision not in ALLOWED_DECISIONS:
            errors.append(f"invalid_decision_category_{category_id}")
        if decision == "hit" and not _has_non_empty_evidence(item):
            errors.append(f"hit_without_evidence_category_{category_id}")
        if item.get("product_image_used") is True and category_id not in ALLOWED_PRODUCT_IMAGE_CATEGORY_IDS:
            errors.append(f"product_image_permission_violation_category_{category_id}")

    _check_decision_lists(payload, errors)
    _check_priority_conflicts(results, errors)

    material_summary = payload.get("material_summary", {})
    if not isinstance(material_summary, dict):
        material_summary = {}
    segment_count = _to_int(params.get("segment_count", material_summary.get("segment_count", 0)))
    product_count = _to_int(params.get("product_count", material_summary.get("product_count", 0)))
    if segment_count == 0 and product_count == 0:
        warnings.append("empty_materials")

    return errors, warnings


def validate_judge_output(params):
    judge_output = params.get("judge_output", "")
    report_text = _text(judge_output).split("FINAL_JSON:", 1)[0].strip() if "FINAL_JSON:" in _text(judge_output) else _text(judge_output)
    try:
        payload = json.loads(_extract_final_json_text(judge_output))
    except Exception as exc:
        return {
            "validation_status": "fail",
            "validation_errors": json.dumps([f"json_parse_failed:{exc}"], ensure_ascii=False),
            "validated_final_json": "",
            "final_report_text": report_text,
            "room_id": _text(params.get("room_id")),
            "hit_category_ids": "[]",
            "no_hit_category_ids": "[]",
            "unable_to_judge_category_ids": "[]",
        }

    errors, warnings = _validate_payload(payload, params)
    all_messages = errors + warnings
    if errors:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    return {
        "validation_status": status,
        "validation_errors": json.dumps(all_messages, ensure_ascii=False),
        "validated_final_json": json.dumps(payload, ensure_ascii=False),
        "final_report_text": report_text,
        "room_id": _text(payload.get("room_id") or params.get("room_id")),
        "hit_category_ids": json.dumps(_parse_id_list(payload.get("hit_category_ids")), ensure_ascii=False),
        "no_hit_category_ids": json.dumps(_parse_id_list(payload.get("no_hit_category_ids")), ensure_ascii=False),
        "unable_to_judge_category_ids": json.dumps(_parse_id_list(payload.get("unable_to_judge_category_ids")), ensure_ascii=False),
    }


async def main(args: Args) -> Output:
    params = args.params
    return validate_judge_output(params)
