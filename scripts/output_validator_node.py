import json


ALLOWED_PRODUCT_IMAGE_CATEGORY_IDS = {3, 5, 6, 9, 10, 12, 15, 16, 17}
ALL_CATEGORY_IDS = set(range(1, 20))
ALLOWED_DECISIONS = {"hit", "no_hit", "unable_to_judge"}
PRIORITY_CONFLICT_PAIRS = ((3, 5), (3, 6), (5, 6), (8, 15), (1, 19))


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
    for first_id, second_id in PRIORITY_CONFLICT_PAIRS:
        first = by_id.get(first_id, {})
        second = by_id.get(second_id, {})
        if first.get("decision") != "hit" or second.get("decision") != "hit":
            continue
        if _normalized_evidence_keys(first) & _normalized_evidence_keys(second):
            errors.append(
                "priority_conflict_category_%d_and_%d" % (first_id, second_id)
            )

    category_19 = by_id.get(19, {})
    if category_19.get("decision") == "hit":
        errors.append("disabled_category_19_hit")


def _normalized_evidence_keys(item):
    evidence = item.get("evidence")
    if not isinstance(evidence, list):
        return set()

    keys = set()
    for entry in evidence:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        detail = entry.get("quote_or_visual_detail")
        if not isinstance(source, str) or not isinstance(detail, str):
            continue
        source = source.strip()
        detail = detail.strip()
        if source and detail:
            keys.add((source, detail))
    return keys


def _finalizer_errors_are_nonempty(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in {"", "[]"}
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return bool(value)


def _finalizer_errors_diagnostic(value):
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        try:
            return str(value).strip()
        except Exception:
            return "<unprintable>"


def _check_finalization_status(params, errors, warnings):
    status = _text(params.get("finalization_status"))
    finalizer_errors = params.get("finalizer_errors")
    has_diagnostic = _finalizer_errors_are_nonempty(finalizer_errors)

    if not status:
        return

    if status == "fail":
        errors.append("boundary_finalization_failed")
    elif status == "warning":
        warnings.append("boundary_finalization_warning")
    elif status == "pass":
        if has_diagnostic:
            errors.append("unexpected_finalizer_errors")
    else:
        errors.append("invalid_finalization_status")

    if has_diagnostic:
        diagnostic = "finalizer_errors:" + _finalizer_errors_diagnostic(finalizer_errors)
        if status == "warning":
            warnings.append(diagnostic)
        else:
            errors.append(diagnostic)


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
    finalization_errors = []
    finalization_warnings = []
    _check_finalization_status(params, finalization_errors, finalization_warnings)
    try:
        payload = json.loads(_extract_final_json_text(judge_output))
    except Exception as exc:
        return {
            "validation_status": "fail",
            "validation_errors": json.dumps(
                [f"json_parse_failed:{exc}"]
                + finalization_errors
                + finalization_warnings,
                ensure_ascii=False,
            ),
            "validated_final_json": "",
            "final_report_text": report_text,
            "room_id": _text(params.get("room_id")),
            "hit_category_ids": "[]",
            "no_hit_category_ids": "[]",
            "unable_to_judge_category_ids": "[]",
        }

    errors, warnings = _validate_payload(payload, params)
    errors.extend(finalization_errors)
    warnings.extend(finalization_warnings)
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
