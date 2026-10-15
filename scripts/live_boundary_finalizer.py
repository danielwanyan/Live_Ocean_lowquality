import json


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _extract_payload(judge_output):
    text = _text(judge_output)
    marker = "FINAL_JSON:"
    if marker not in text:
        raise ValueError("final_json_marker_missing")

    json_text = text.split(marker, 1)[1].strip()
    fence = chr(96) * 3
    if json_text.startswith(fence):
        json_text = json_text[len(fence):].lstrip()
        if json_text.startswith("json"):
            json_text = json_text[len("json"):].lstrip()
        if json_text.endswith(fence):
            json_text = json_text[:-len(fence)].rstrip()

    payload = json.loads(json_text)
    if not isinstance(payload, dict):
        raise ValueError("final_json_not_object")
    return payload


def _load_gates(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception as exc:
            raise ValueError("boundary_gates_parse_failed:" + _text(exc))
    if not isinstance(value, dict):
        raise ValueError("boundary_gates_not_object")
    return value


def _validate_contract(payload, gates, expected_version):
    errors = []
    if not expected_version:
        errors.append("boundary_contract_version_missing")

    if gates.get("contract_version") != expected_version:
        errors.append("gate_contract_version_mismatch")

    boundary_checks = payload.get("boundary_checks")
    if not isinstance(boundary_checks, dict):
        errors.append("boundary_checks_missing_or_not_object")
    else:
        if boundary_checks.get("contract_version") != expected_version:
            errors.append("boundary_contract_version_mismatch")

        facts = boundary_checks.get("facts")
        if not isinstance(facts, dict):
            errors.append("boundary_facts_missing_or_not_object")
        else:
            required_facts = gates.get("required_facts")
            if not isinstance(required_facts, list):
                errors.append("gate_required_facts_missing_or_not_list")
                required_facts = []

            for fact_name in required_facts:
                fact = facts.get(fact_name)
                if not isinstance(fact, dict):
                    errors.append("missing_boundary_fact:" + _text(fact_name))
                    continue

                value = fact.get("value")
                evidence_sources = fact.get("evidence_sources")
                if type(value) is not bool:
                    errors.append("boundary_fact_value_not_bool:" + _text(fact_name))
                if type(evidence_sources) is not list:
                    errors.append("boundary_fact_evidence_sources_not_list:" + _text(fact_name))

                if value is True:
                    has_source = isinstance(evidence_sources, list) and any(
                        _text(source) for source in evidence_sources
                    )
                    if not has_source or not _text(fact.get("evidence_detail")):
                        errors.append("true_fact_without_evidence:" + _text(fact_name))

    if payload.get("rules_version") != expected_version:
        errors.append("rules_version_mismatch")
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
        if error in {"final_json_marker_missing", "final_json_not_object"}:
            return _failure([error])
        return _failure(["final_json_parse_failed:" + error])

    try:
        gates = _load_gates(params.get("boundary_gates_json"))
    except Exception as exc:
        return _failure([_text(exc) or "boundary_gates_load_failed"])

    expected_version = _text(params.get("boundary_contract_version"))
    errors = _validate_contract(payload, gates, expected_version)
    if errors:
        return _failure(errors)

    serialized_payload = json.dumps(payload, ensure_ascii=False)
    return {
        "finalized_judge_output": "FINAL_JSON:\n" + serialized_payload,
        "finalized_final_json": serialized_payload,
        "finalization_status": "pass",
        "boundary_override_log": "[]",
        "finalizer_errors": "[]",
    }


async def main(args: Args) -> Output:
    return finalize_judge_output(args.params)
