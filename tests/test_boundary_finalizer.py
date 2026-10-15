import asyncio
import copy
import json
import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from live_boundary_gate_builder import (
    BOUNDARY_CONTRACT_VERSION,
    REQUIRED_FACTS,
    build_boundary_gate_output,
)
from live_boundary_finalizer import finalize_judge_output, main


CATEGORY_NAMES = [
    "色情低俗低质问题",
    "恶心恐怖低质问题",
    "商品无关低质问题",
    "无互动低质问题",
    "无实物商品展示低质问题",
    "商品描述不详细低质问题",
    "静态帧遮挡低质问题",
    "非母语违规低质问题",
    "AIGC真实性低质问题",
    "AIGC商品展示低质问题",
    "录播回放低质问题",
    "功能效果虚假宣传低质问题",
    "危险行为低质问题",
    "站外引流交易低质问题",
    "违法违规商品低质问题",
    "政治敏感低质问题",
    "争议话题低质问题",
    "负面引导低质问题",
    "隐私敏感商品低质问题",
]
EXPECTED_RETURN_KEYS = {
    "finalized_judge_output",
    "finalized_final_json",
    "finalization_status",
    "boundary_override_log",
    "finalizer_errors",
}


def fact(value=False, evidence_sources=None, evidence_detail=None):
    if evidence_sources is None:
        evidence_sources = ["Segment #1 frame"] if value else []
    if evidence_detail is None:
        evidence_detail = "Visible evidence supports the fact." if value else ""
    return {
        "value": value,
        "evidence_sources": evidence_sources,
        "evidence_detail": evidence_detail,
    }


def clean_facts():
    return {name: fact() for name in REQUIRED_FACTS}


def valid_payload():
    final_results = []
    for category_id, category_name in enumerate(CATEGORY_NAMES, start=1):
        final_results.append(
            {
                "category_id": category_id,
                "category_name": category_name,
                "decision": "no_hit",
                "confidence": "medium",
                "evidence_count": 0,
                "evidence": [],
                "judge_reason": "No qualifying evidence was found.",
                "materials_used": [],
                "product_image_used": False,
                "product_image_permission_ok": True,
                "priority_rule_applied": [],
            }
        )
    return {
        "rules_version": BOUNDARY_CONTRACT_VERSION,
        "room_id": "7380123456789012345",
        "material_summary": {
            "segment_count": 1,
            "product_count": 1,
            "comment_interaction_available": True,
            "material_quality_warning": [],
        },
        "boundary_checks": {
            "contract_version": BOUNDARY_CONTRACT_VERSION,
            "facts": clean_facts(),
        },
        "final_results": final_results,
        "hit_category_ids": [],
        "no_hit_category_ids": list(range(1, 20)),
        "unable_to_judge_category_ids": [],
        "coverage_check": {
            "expected_category_count": 19,
            "actual_category_count": 19,
            "missing_category_ids": [],
            "extra_category_ids": [],
            "hit_no_hit_overlap_category_ids": [],
        },
        "policy_checks": {
            "product_image_permission_violations": [],
            "exclusive_priority_applied": [],
            "threshold_recheck_warnings": [],
        },
    }


def build_params(payload=None, judge_output=None):
    payload = valid_payload() if payload is None else payload
    gate_output = build_boundary_gate_output(
        {
            "segments_json": json.dumps(
                [
                    {
                        "segment_index": 1,
                        "asr_summary": "The host explains the promoted product.",
                        "frame_urls": ["https://example.com/live-frame.jpg"],
                    }
                ]
            ),
            "comment_interaction": "A viewer asks about the product size.",
            "product_catalog_json": json.dumps(
                [
                    {
                        "product_index": 1,
                        "title": "Example product",
                        "image_urls": ["https://example.com/product.jpg"],
                    }
                ]
            ),
            "rules_version": BOUNDARY_CONTRACT_VERSION,
        }
    )
    if judge_output is None:
        judge_output = "Judge report\nFINAL_JSON:\n" + json.dumps(payload, ensure_ascii=False)
    return {
        "judge_output": judge_output,
        "boundary_gates_json": gate_output["boundary_gates_json"],
        "boundary_contract_version": gate_output["boundary_contract_version"],
    }


class LiveBoundaryFinalizerTest(unittest.TestCase):
    def assert_failure(self, result, expected_error):
        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)
        self.assertEqual(result["finalized_judge_output"], "")
        self.assertEqual(result["finalized_final_json"], "")
        self.assertEqual(result["finalization_status"], "fail")
        self.assertEqual(result["boundary_override_log"], "[]")
        self.assertIn(expected_error, json.loads(result["finalizer_errors"]))

    def test_missing_final_json_marker_fails_closed(self):
        result = finalize_judge_output(build_params(judge_output="No structured output"))

        self.assert_failure(result, "final_json_marker_missing")

    def test_malformed_json_after_marker_fails_with_parse_error(self):
        result = finalize_judge_output(build_params(judge_output="FINAL_JSON:\n{broken"))

        self.assertEqual(result["finalization_status"], "fail")
        errors = json.loads(result["finalizer_errors"])
        self.assertTrue(any(error.startswith("final_json_parse_failed:") for error in errors))

    def test_missing_boundary_checks_fails_closed(self):
        payload = valid_payload()
        del payload["boundary_checks"]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_checks_missing_or_not_object")

    def test_missing_required_fact_fails_closed(self):
        payload = valid_payload()
        missing_name = REQUIRED_FACTS[0]
        del payload["boundary_checks"]["facts"][missing_name]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "missing_boundary_fact:" + missing_name)

    def test_boundary_fact_value_must_be_exact_bool(self):
        payload = valid_payload()
        fact_name = REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["value"] = 1

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_value_not_bool:" + fact_name)

    def test_boundary_fact_evidence_sources_must_be_exact_list(self):
        payload = valid_payload()
        fact_name = REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["evidence_sources"] = "Segment #1 frame"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_evidence_sources_not_list:" + fact_name)

    def test_true_fact_requires_nonblank_source_and_detail(self):
        fact_name = REQUIRED_FACTS[0]
        invalid_facts = (
            fact(True, evidence_sources=[], evidence_detail="Evidence detail"),
            fact(True, evidence_sources=["   "], evidence_detail="Evidence detail"),
            fact(True, evidence_sources=["Segment #1 frame"], evidence_detail="   "),
        )

        for invalid_fact in invalid_facts:
            with self.subTest(invalid_fact=invalid_fact):
                payload = valid_payload()
                payload["boundary_checks"]["facts"][fact_name] = invalid_fact

                result = finalize_judge_output(build_params(payload))

                self.assert_failure(result, "true_fact_without_evidence:" + fact_name)

    def test_gate_contract_version_mismatch_fails_closed(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["contract_version"] = "stale-gate-version"
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_contract_version_mismatch")

    def test_model_boundary_contract_version_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["boundary_checks"]["contract_version"] = "stale-model-version"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_contract_version_mismatch")

    def test_payload_rules_version_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["rules_version"] = "stale-rules-version"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "rules_version_mismatch")

    def test_empty_expected_boundary_contract_version_fails_closed(self):
        params = build_params()
        params["boundary_contract_version"] = "   "

        result = finalize_judge_output(params)

        self.assert_failure(result, "boundary_contract_version_missing")

    def test_boundary_facts_must_be_an_object(self):
        payload = valid_payload()
        payload["boundary_checks"]["facts"] = []

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_facts_missing_or_not_object")

    def test_boundary_gate_input_must_parse_to_an_object(self):
        params = build_params()
        params["boundary_gates_json"] = "[]"

        result = finalize_judge_output(params)

        self.assert_failure(result, "boundary_gates_not_object")

    def test_fenced_valid_payload_passes(self):
        payload = valid_payload()
        fence = chr(96) * 3
        for opening in (fence, fence + "json"):
            with self.subTest(opening=opening):
                judge_output = "FINAL_JSON:\n" + opening + "\n" + json.dumps(payload) + "\n" + fence

                result = finalize_judge_output(build_params(judge_output=judge_output))

                self.assertEqual(result["finalization_status"], "pass")

    def test_fully_valid_payload_passes_without_business_overrides(self):
        payload = valid_payload()
        true_fact_name = REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][true_fact_name] = fact(True)

        result = finalize_judge_output(build_params(payload))

        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)
        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(json.loads(result["finalizer_errors"]), [])
        self.assertEqual(json.loads(result["boundary_override_log"]), [])
        self.assertEqual(json.loads(result["finalized_final_json"]), payload)
        self.assertTrue(result["finalized_judge_output"].startswith("FINAL_JSON:\n"))
        self.assertEqual(
            json.loads(result["finalized_judge_output"].split("FINAL_JSON:\n", 1)[1]),
            payload,
        )

    def test_dictionary_gates_and_payload_are_not_mutated_across_calls(self):
        payload = valid_payload()
        params = build_params(payload)
        params["boundary_gates_json"] = json.loads(params["boundary_gates_json"])
        original_payload = copy.deepcopy(payload)
        original_gates = copy.deepcopy(params["boundary_gates_json"])

        first = finalize_judge_output(params)
        second = finalize_judge_output(params)

        self.assertEqual(first["finalization_status"], "pass")
        self.assertEqual(second["finalization_status"], "pass")
        self.assertEqual(payload, original_payload)
        self.assertEqual(params["boundary_gates_json"], original_gates)

    def test_async_main_adapter_forwards_args_params(self):
        payload = valid_payload()

        class StubArgs:
            params = build_params(payload)

        result = asyncio.run(main(StubArgs()))

        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(json.loads(result["finalized_final_json"]), payload)


if __name__ == "__main__":
    unittest.main()
