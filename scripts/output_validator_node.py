import json


ALLOWED_PRODUCT_IMAGE_CATEGORY_IDS = {3, 5, 6, 9, 10, 12, 15, 16, 17}
ALL_CATEGORY_IDS = set(range(1, 20))
ALLOWED_DECISIONS = {"hit", "no_hit", "unable_to_judge"}
PRIORITY_CONFLICT_PAIRS = ((3, 5), (3, 6), (5, 6), (8, 15))
FINALIZATION_STATUSES = {"pass", "warning", "fail"}


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


def _reject_json_constant(value):
    raise ValueError("invalid_json_constant:" + value)


def _strict_json_loads(value):
    return json.loads(value, parse_constant=_reject_json_constant)


def _normalize_whitespace(value):
    return " ".join(value.split())


def _parse_id_list(value):
    if isinstance(value, list):
        return [_to_int(item) for item in value]
    return []


def _has_non_empty_evidence(item):
    evidence = item.get("evidence")
    evidence_count = item.get("evidence_count")
    return (
        type(evidence) is list
        and bool(evidence)
        and _evidence_entries_are_valid(evidence)
        and type(evidence_count) is int
        and evidence_count == len(evidence)
    )


def _evidence_entries_are_valid(evidence):
    for entry in evidence:
        if type(entry) is not dict:
            return False
        source = entry.get("source")
        detail = entry.get("quote_or_visual_detail")
        reason = entry.get("reason")
        if type(source) is not str or not source.strip():
            return False
        if type(detail) is not str or not detail.strip():
            return False
        if type(reason) is not str or not reason.strip():
            return False
    return True


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
    if type(evidence) is not list:
        return set()

    keys = set()
    for entry in evidence:
        if type(entry) is not dict:
            continue
        source = entry.get("source")
        detail = entry.get("quote_or_visual_detail")
        if type(source) is not str or type(detail) is not str:
            continue
        source = _normalize_whitespace(source)
        detail = _normalize_whitespace(detail)
        if source and detail:
            keys.add((source, detail))
    return keys


def _parse_finalizer_errors(value):
    if type(value) is not str:
        return None
    try:
        parsed = _strict_json_loads(value)
    except Exception:
        return None
    if type(parsed) is not list or any(
        type(item) is not str or not item.strip() for item in parsed
    ):
        return None
    return parsed


def _check_finalization_status(params, errors, warnings):
    has_status = "finalization_status" in params
    has_errors = "finalizer_errors" in params
    if not has_status and not has_errors:
        return None

    status = params.get("finalization_status")
    status_is_valid = type(status) is str and status in FINALIZATION_STATUSES
    if has_status != has_errors:
        errors.append("incomplete_finalizer_metadata")
        if status_is_valid and status == "fail":
            errors.append("boundary_finalization_failed")
        return status if status_is_valid else None

    if not status_is_valid:
        errors.append("invalid_finalization_status")

    parsed_errors = _parse_finalizer_errors(params.get("finalizer_errors"))
    if parsed_errors is None:
        errors.append("invalid_finalizer_errors")

    if not status_is_valid:
        return None
    if status == "fail":
        errors.append("boundary_finalization_failed")
        if parsed_errors == []:
            errors.append("invalid_finalizer_errors")
        elif parsed_errors is not None:
            errors.extend(parsed_errors)
    elif parsed_errors:
        errors.append("unexpected_finalizer_errors")
    elif parsed_errors is not None and status == "warning":
        warnings.append("boundary_finalization_warning")
    return status


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
        evidence = item.get("evidence")
        if type(evidence) is not list or not _evidence_entries_are_valid(evidence):
            errors.append(f"malformed_evidence_category_{category_id}")
        evidence_count = item.get("evidence_count")
        if type(evidence_count) is not int:
            errors.append(f"invalid_evidence_count_category_{category_id}")
        elif type(evidence) is list and evidence_count != len(evidence):
            errors.append(f"evidence_count_mismatch_category_{category_id}")
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


def _failure_result(params, report_text, errors):
    return {
        "validation_status": "fail",
        "validation_errors": json.dumps(errors, ensure_ascii=False, allow_nan=False),
        "validated_final_json": "",
        "final_report_text": report_text,
        "room_id": _text(params.get("room_id")),
        "hit_category_ids": "[]",
        "no_hit_category_ids": "[]",
        "unable_to_judge_category_ids": "[]",
    }


def validate_judge_output(params):
    judge_output = params.get("judge_output", "")
    report_text = _text(judge_output).split("FINAL_JSON:", 1)[0].strip() if "FINAL_JSON:" in _text(judge_output) else _text(judge_output)
    finalization_errors = []
    finalization_warnings = []
    finalization_status = _check_finalization_status(
        params,
        finalization_errors,
        finalization_warnings,
    )
    if finalization_status == "fail" and not _text(judge_output):
        return _failure_result(
            params,
            report_text,
            finalization_errors + finalization_warnings,
        )
    try:
        payload = _strict_json_loads(_extract_final_json_text(judge_output))
        if type(payload) is not dict:
            raise ValueError("final_json_not_object")
    except Exception as exc:
        return _failure_result(
            params,
            report_text,
            (
                [f"json_parse_failed:{exc}"]
                + finalization_errors
                + finalization_warnings
            ),
        )

    errors, warnings = _validate_payload(payload, params)
    errors.extend(finalization_errors)
    warnings.extend(finalization_warnings)
    try:
        serialized_payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        errors.append("json_serialize_failed:" + _text(exc))
        serialized_payload = ""
    all_messages = errors + warnings
    if errors:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    return {
        "validation_status": status,
        "validation_errors": json.dumps(
            all_messages,
            ensure_ascii=False,
            allow_nan=False,
        ),
        "validated_final_json": serialized_payload,
        "final_report_text": report_text,
        "room_id": _text(payload.get("room_id") or params.get("room_id")),
        "hit_category_ids": json.dumps(_parse_id_list(payload.get("hit_category_ids")), ensure_ascii=False),
        "no_hit_category_ids": json.dumps(_parse_id_list(payload.get("no_hit_category_ids")), ensure_ascii=False),
        "unable_to_judge_category_ids": json.dumps(_parse_id_list(payload.get("unable_to_judge_category_ids")), ensure_ascii=False),
    }


async def main(args: Args) -> Output:
    params = args.params
    return validate_judge_output(params)
