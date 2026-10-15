import json
import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from live_boundary_finalizer import EXPECTED_CATEGORY_NAMES, finalize_judge_output
from live_boundary_gate_builder import (
    BOUNDARY_CONTRACT_VERSION,
    REQUIRED_FACTS,
    REROUTES,
    build_boundary_gate_output,
)
from output_validator_node import PRIORITY_CONFLICT_PAIRS, validate_judge_output


RULES_PATH = os.path.join(PROJECT_DIR, "rules", "live_ocean_lowquality_rules_structured_v1.json")
COMPACT_RULES_PATH = os.path.join(PROJECT_DIR, "rules", "live_ocean_lowquality_judge_rules_compact_v1.txt")
SYSTEM_PROMPT_PATH = os.path.join(PROJECT_DIR, "prompts", "lowquality_judge_system_prompt_v1.txt")


def _valid_payload(hit_ids=(), evidence_by_id=None):
    hit_ids = set(hit_ids)
    evidence_by_id = evidence_by_id or {}
    final_results = []
    for category_id in range(1, 20):
        evidence = evidence_by_id.get(category_id, []) if category_id in hit_ids else []
        final_results.append(
            {
                "category_id": category_id,
                "category_name": EXPECTED_CATEGORY_NAMES[category_id],
                "decision": "hit" if category_id in hit_ids else "no_hit",
                "confidence": "high" if category_id in hit_ids else "medium",
                "evidence_count": len(evidence),
                "evidence": evidence,
                "judge_reason": "fixture",
                "materials_used": [],
                "product_image_used": False,
                "product_image_permission_ok": True,
                "priority_rule_applied": [],
            }
        )

    return {
        "room_id": "fixture-room",
        "material_summary": {"segment_count": 1, "product_count": 0},
        "final_results": final_results,
        "hit_category_ids": sorted(hit_ids),
        "no_hit_category_ids": [
            category_id for category_id in range(1, 20) if category_id not in hit_ids
        ],
        "unable_to_judge_category_ids": [],
    }


def _valid_finalizer_payload():
    payload = _valid_payload()
    payload["room_id"] = "7380123456789012345"
    payload["rules_version"] = BOUNDARY_CONTRACT_VERSION
    payload["material_summary"] = {
        "segment_count": 1,
        "product_count": 1,
        "comment_interaction_available": True,
        "material_quality_warning": [],
    }
    payload["boundary_checks"] = {
        "contract_version": BOUNDARY_CONTRACT_VERSION,
        "facts": {
            name: {"value": False, "evidence_sources": [], "evidence_detail": ""}
            for name in REQUIRED_FACTS
        },
    }
    payload["coverage_check"] = {
        "expected_category_count": 19,
        "actual_category_count": 19,
        "missing_category_ids": [],
        "extra_category_ids": [],
        "hit_no_hit_overlap_category_ids": [],
    }
    payload["policy_checks"] = {
        "product_image_permission_violations": [],
        "exclusive_priority_applied": [],
        "threshold_recheck_warnings": [],
    }
    return payload


def _finalizer_params(payload):
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
    return {
        "judge_output": "Judge report\nFINAL_JSON:\n"
        + json.dumps(payload, ensure_ascii=False),
        "boundary_gates_json": gate_output["boundary_gates_json"],
        "boundary_contract_version": gate_output["boundary_contract_version"],
        "rules_version": BOUNDARY_CONTRACT_VERSION,
        "room_id": payload["room_id"],
    }


def _validator_params_from_finalizer(result):
    return {
        "judge_output": result["finalized_judge_output"],
        "finalization_status": result["finalization_status"],
        "finalizer_errors": result["finalizer_errors"],
    }


def _validator_params(payload=None, **extra):
    params = {
        "judge_output": "report\nFINAL_JSON:\n" + json.dumps(payload or _valid_payload())
    }
    params.update(extra)
    return params


class RuleCalibrationTest(unittest.TestCase):
    def test_structured_rules_keep_category_and_product_image_permissions_consistent(self):
        with open(RULES_PATH, encoding="utf-8") as f:
            rules = json.load(f)

        expected_allowed = {3, 5, 6, 9, 10, 12, 15, 16, 17}
        categories = rules["categories"]

        self.assertEqual([item["category_id"] for item in categories], list(range(1, 20)))
        self.assertEqual(set(rules["product_image_allowed_category_ids"]), expected_allowed)
        self.assertEqual(
            {item["category_id"] for item in categories if item["product_image_allowed"]},
            expected_allowed,
        )

        category_19 = next(item for item in categories if item["category_id"] == 19)
        self.assertFalse(category_19["product_image_allowed"])
        self.assertIn("Disabled", category_19["trigger_threshold"])

    def test_rules_include_human_review_boundary_guards(self):
        with open(RULES_PATH, encoding="utf-8") as f:
            rules = json.load(f)

        priorities = {item["id"] for item in rules["exclusive_priority_rules"]}
        self.assertIn("priority_15_over_8_for_product_mismatch", priorities)
        self.assertIn("priority_5_over_6_for_no_physical_display", priorities)

        by_id = {item["category_id"]: item for item in rules["categories"]}
        self.assertIn("auction", by_id[6]["judge_focus_en"].lower())
        self.assertIn("sensitive-skin-safe", by_id[12]["exemptions"][0])
        self.assertIn("Routine commercial urgency alone does not hit", by_id[18]["trigger_threshold"])

    def test_prompts_do_not_reintroduce_category_19_product_image_permission(self):
        with open(COMPACT_RULES_PATH, encoding="utf-8") as f:
            compact_rules = f.read()
        with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
            system_prompt = f.read()

        stale_permission_texts = [
            "3, 5, 6, 9, 10, 12, 15, 16, 17, 19",
            "3,5,6,9,10,12,15,16,17,19",
        ]
        for stale_text in stale_permission_texts:
            self.assertNotIn(stale_text, compact_rules)
            self.assertNotIn(stale_text, system_prompt)

        self.assertIn("Category 19 is disabled", compact_rules)
        self.assertIn("Category 19 is disabled", system_prompt)

    def test_validator_rejects_disabled_category_19_hit(self):
        evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "sanitary pads",
                "reason": "The evidence is included for the category 19 regression.",
            }
        ]
        payload = _valid_payload(hit_ids=[19], evidence_by_id={19: evidence})
        result = validate_judge_output(_validator_params(payload))

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("disabled_category_19_hit", json.loads(result["validation_errors"]))

    def test_validator_rejects_failed_finalizer_and_preserves_diagnostic(self):
        result = validate_judge_output(
            _validator_params(
                finalization_status="fail",
                finalizer_errors='["invalid_final_result_decision:3"]',
            )
        )

        errors = json.loads(result["validation_errors"])
        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("boundary_finalization_failed", errors)
        self.assertIn("invalid_final_result_decision:3", errors)

    def test_validator_propagates_finalizer_warning(self):
        result = validate_judge_output(
            _validator_params(
                finalization_status="warning",
                finalizer_errors="[]",
            )
        )

        errors = json.loads(result["validation_errors"])
        self.assertEqual(result["validation_status"], "warning")
        self.assertEqual(errors, ["boundary_finalization_warning"])

    def test_validator_keeps_finalizer_pass(self):
        result = validate_judge_output(
            _validator_params(finalization_status="pass", finalizer_errors="[]")
        )

        self.assertEqual(result["validation_status"], "pass")
        self.assertEqual(json.loads(result["validation_errors"]), [])

    def test_validator_retains_legacy_pass_when_finalizer_status_missing(self):
        result = validate_judge_output(_validator_params())

        self.assertEqual(result["validation_status"], "pass")
        self.assertEqual(json.loads(result["validation_errors"]), [])

    def test_validator_rejects_incomplete_finalizer_metadata(self):
        cases = [
            {"finalization_status": "pass"},
            {"finalizer_errors": "[]"},
        ]

        for metadata in cases:
            with self.subTest(metadata=metadata):
                result = validate_judge_output(_validator_params(**metadata))

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(
                    "incomplete_finalizer_metadata",
                    json.loads(result["validation_errors"]),
                )

    def test_validator_rejects_non_exact_finalizer_status(self):
        invalid_statuses = [None, False, 0, {}, [], "", "PASS", " warning "]

        for status in invalid_statuses:
            with self.subTest(status=status):
                result = validate_judge_output(
                    _validator_params(
                        finalization_status=status,
                        finalizer_errors="[]",
                    )
                )

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(
                    "invalid_finalization_status",
                    json.loads(result["validation_errors"]),
                )

    def test_validator_rejects_invalid_finalizer_errors_wire_values(self):
        invalid_values = [
            None,
            False,
            0,
            {},
            [],
            "not json",
            "{}",
            '["valid", 1]',
            '[""]',
            '["   "]',
            "[NaN]",
        ]

        for finalizer_errors in invalid_values:
            with self.subTest(finalizer_errors=finalizer_errors):
                result = validate_judge_output(
                    _validator_params(
                        finalization_status="pass",
                        finalizer_errors=finalizer_errors,
                    )
                )

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(
                    "invalid_finalizer_errors",
                    json.loads(result["validation_errors"]),
                )

    def test_validator_rejects_empty_or_invalid_errors_for_fail_status(self):
        invalid_values = [None, "[]", '[""]', '["   "]']

        for finalizer_errors in invalid_values:
            with self.subTest(finalizer_errors=finalizer_errors):
                result = validate_judge_output(
                    _validator_params(
                        finalization_status="fail",
                        finalizer_errors=finalizer_errors,
                    )
                )

                errors = json.loads(result["validation_errors"])
                self.assertEqual(result["validation_status"], "fail")
                self.assertIn("boundary_finalization_failed", errors)
                self.assertIn("invalid_finalizer_errors", errors)

    def test_validator_rejects_unknown_finalizer_status(self):
        result = validate_judge_output(
            _validator_params(finalization_status="partial", finalizer_errors="[]")
        )

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn(
            "invalid_finalization_status",
            json.loads(result["validation_errors"]),
        )

    def test_validator_rejects_finalizer_errors_with_pass_or_warning_status(self):
        for status in ("pass", "warning"):
            with self.subTest(status=status):
                result = validate_judge_output(
                    _validator_params(
                        finalization_status=status,
                        finalizer_errors='["unexpected audit"]',
                    )
                )

                errors = json.loads(result["validation_errors"])
                self.assertEqual(result["validation_status"], "fail")
                self.assertIn("unexpected_finalizer_errors", errors)

    def test_finalizer_pass_output_is_accepted_end_to_end(self):
        finalized = finalize_judge_output(_finalizer_params(_valid_finalizer_payload()))
        result = validate_judge_output(_validator_params_from_finalizer(finalized))
        finalized_payload = json.loads(finalized["finalized_final_json"])

        self.assertEqual(finalized["finalization_status"], "pass")
        self.assertEqual(result["validation_status"], "pass")
        self.assertEqual(json.loads(result["validation_errors"]), [])
        self.assertEqual(json.loads(result["validated_final_json"]), finalized_payload)
        for output_key in (
            "hit_category_ids",
            "no_hit_category_ids",
            "unable_to_judge_category_ids",
        ):
            self.assertEqual(json.loads(result[output_key]), finalized_payload[output_key])

    def test_finalizer_warning_output_is_propagated_end_to_end(self):
        payload = _valid_finalizer_payload()
        payload["boundary_checks"]["facts"]["sexualized_exposure_or_behavior_found"] = {
            "value": True,
            "evidence_sources": ["Segment #1 frame"],
            "evidence_detail": "The host performs explicit sexualized behavior.",
        }

        finalized = finalize_judge_output(_finalizer_params(payload))
        result = validate_judge_output(_validator_params_from_finalizer(finalized))
        finalized_payload = json.loads(finalized["finalized_final_json"])

        self.assertEqual(finalized["finalization_status"], "warning")
        self.assertEqual(json.loads(finalized["finalizer_errors"]), [])
        self.assertEqual(result["validation_status"], "warning")
        self.assertEqual(
            json.loads(result["validation_errors"]),
            ["boundary_finalization_warning"],
        )
        self.assertEqual(json.loads(result["validated_final_json"]), finalized_payload)
        for output_key in (
            "hit_category_ids",
            "no_hit_category_ids",
            "unable_to_judge_category_ids",
        ):
            self.assertEqual(json.loads(result[output_key]), finalized_payload[output_key])

    def test_finalizer_failure_output_is_rejected_without_parse_noise(self):
        payload = _valid_finalizer_payload()
        payload["rules_version"] = "stale-rules-version"

        finalized = finalize_judge_output(_finalizer_params(payload))
        result = validate_judge_output(_validator_params_from_finalizer(finalized))

        errors = json.loads(result["validation_errors"])
        self.assertEqual(finalized["finalization_status"], "fail")
        self.assertEqual(finalized["finalized_judge_output"], "")
        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("boundary_finalization_failed", errors)
        self.assertIn("payload_rules_version_mismatch", errors)
        self.assertFalse(any(error.startswith("json_parse_failed:") for error in errors))

    def test_blank_existing_hit_reason_fails_across_finalizer_and_validator(self):
        payload = _valid_finalizer_payload()
        category_1 = payload["final_results"][0]
        category_1.update(
            {
                "decision": "hit",
                "confidence": "high",
                "evidence_count": 1,
                "evidence": [
                    {
                        "source": "Segment #1 frame",
                        "quote_or_visual_detail": "Visible gated category 1 evidence.",
                        "reason": "   ",
                    }
                ],
                "judge_reason": "Adversarial existing hit with a blank evidence reason.",
                "materials_used": ["segment_frame"],
            }
        )
        payload["hit_category_ids"] = [1]
        payload["no_hit_category_ids"] = list(range(2, 20))
        payload["boundary_checks"]["facts"]["sexualized_exposure_or_behavior_found"] = {
            "value": True,
            "evidence_sources": ["Segment #1 frame"],
            "evidence_detail": "Visible gated category 1 evidence.",
        }

        finalized = finalize_judge_output(_finalizer_params(payload))
        result = validate_judge_output(_validator_params_from_finalizer(finalized))

        finalizer_errors = json.loads(finalized["finalizer_errors"])
        validation_errors = json.loads(result["validation_errors"])
        self.assertEqual(finalized["finalization_status"], "fail")
        self.assertNotIn(finalized["finalization_status"], {"pass", "warning"})
        self.assertIn("invalid_final_result_evidence_reason:1", finalizer_errors)
        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("boundary_finalization_failed", validation_errors)
        self.assertIn("invalid_final_result_evidence_reason:1", validation_errors)
        self.assertFalse(
            any(error.startswith("json_parse_failed:") for error in validation_errors)
        )

    def test_validator_rejects_shared_evidence_priority_conflicts(self):
        shared_evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "the exact same evidence",
                "reason": "Shared evidence belongs to only one priority category.",
            }
        ]
        cases = [
            ((3, 5), "priority_conflict_category_3_and_5"),
            ((3, 6), "priority_conflict_category_3_and_6"),
            ((5, 6), "priority_conflict_category_5_and_6"),
            ((8, 15), "priority_conflict_category_8_and_15"),
        ]

        for pair, expected_code in cases:
            with self.subTest(pair=pair):
                payload = _valid_payload(
                    hit_ids=pair,
                    evidence_by_id={pair[0]: shared_evidence, pair[1]: shared_evidence},
                )
                result = validate_judge_output(_validator_params(payload))
                errors = json.loads(result["validation_errors"])

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(expected_code, errors)

    def test_validator_allows_priority_pairs_with_distinct_evidence(self):
        cases = [(3, 5), (3, 6), (5, 6), (8, 15)]

        for pair in cases:
            with self.subTest(pair=pair):
                evidence_by_id = {
                    pair[0]: [
                        {
                            "source": "Segment #1 ASR",
                            "quote_or_visual_detail": "evidence for category %d" % pair[0],
                            "reason": "Evidence supports category %d." % pair[0],
                        }
                    ],
                    pair[1]: [
                        {
                            "source": "Segment #2 ASR",
                            "quote_or_visual_detail": "evidence for category %d" % pair[1],
                            "reason": "Evidence supports category %d." % pair[1],
                        }
                    ],
                }
                payload = _valid_payload(hit_ids=pair, evidence_by_id=evidence_by_id)
                result = validate_judge_output(_validator_params(payload))
                errors = json.loads(result["validation_errors"])
                expected_code = "priority_conflict_category_%d_and_%d" % pair

                self.assertNotIn(expected_code, errors)
                self.assertEqual(result["validation_status"], "pass")
                self.assertEqual(errors, [])

    def test_category_19_hit_does_not_add_duplicate_priority_conflict(self):
        shared_evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "shared sexual content evidence",
                "reason": "Shared evidence exercises the disabled category rule.",
            }
        ]
        payload = _valid_payload(
            hit_ids=[1, 19],
            evidence_by_id={1: shared_evidence, 19: shared_evidence},
        )

        result = validate_judge_output(_validator_params(payload))

        self.assertEqual(
            json.loads(result["validation_errors"]),
            ["disabled_category_19_hit"],
        )

    def test_validator_handles_malformed_evidence_without_priority_crash(self):
        malformed_evidence = ["identical malformed evidence"]
        payload = _valid_payload(
            hit_ids=[3, 5],
            evidence_by_id={3: malformed_evidence, 5: malformed_evidence},
        )

        result = validate_judge_output(_validator_params(payload))
        errors = json.loads(result["validation_errors"])

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("malformed_evidence_category_3", errors)
        self.assertIn("malformed_evidence_category_5", errors)
        self.assertNotIn("priority_conflict_category_3_and_5", errors)

    def test_validator_rejects_inexact_or_mismatched_evidence_count(self):
        valid_evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "valid evidence",
                "reason": "The evidence supports the decision.",
            }
        ]
        cases = [
            (True, "invalid_evidence_count_category_3"),
            (2, "evidence_count_mismatch_category_3"),
        ]

        for evidence_count, expected_error in cases:
            with self.subTest(evidence_count=evidence_count):
                payload = _valid_payload(hit_ids=[3], evidence_by_id={3: valid_evidence})
                category_3 = next(
                    item for item in payload["final_results"] if item["category_id"] == 3
                )
                category_3["evidence_count"] = evidence_count

                result = validate_judge_output(_validator_params(payload))

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(
                    expected_error,
                    json.loads(result["validation_errors"]),
                )

    def test_validator_requires_nonblank_string_reason_in_evidence(self):
        cases = [
            (False, None),
            (True, None),
            (True, 7),
            (True, ""),
            (True, "   \t\n"),
        ]

        for include_reason, reason in cases:
            with self.subTest(include_reason=include_reason, reason=reason):
                evidence = {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "valid evidence detail",
                }
                if include_reason:
                    evidence["reason"] = reason
                payload = _valid_payload(hit_ids=[3], evidence_by_id={3: [evidence]})

                result = validate_judge_output(_validator_params(payload))

                self.assertEqual(result["validation_status"], "fail")
                self.assertIn(
                    "malformed_evidence_category_3",
                    json.loads(result["validation_errors"]),
                )

    def test_validator_accepts_nonblank_string_reason_in_evidence(self):
        evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "valid evidence detail",
                "reason": "This is a usable reason.",
            }
        ]
        payload = _valid_payload(hit_ids=[3], evidence_by_id={3: evidence})

        result = validate_judge_output(_validator_params(payload))

        self.assertEqual(result["validation_status"], "pass")
        self.assertEqual(json.loads(result["validation_errors"]), [])

    def test_validator_collapses_internal_whitespace_in_priority_evidence_keys(self):
        evidence_by_id = {
            3: [
                {
                    "source": " Segment   #1\tASR ",
                    "quote_or_visual_detail": "same\n\t evidence   detail",
                    "reason": "Category 3 interpretation.",
                }
            ],
            5: [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": " same evidence detail ",
                    "reason": "Category 5 interpretation.",
                }
            ],
        }
        payload = _valid_payload(hit_ids=[3, 5], evidence_by_id=evidence_by_id)

        result = validate_judge_output(_validator_params(payload))

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn(
            "priority_conflict_category_3_and_5",
            json.loads(result["validation_errors"]),
        )

    def test_validator_rejects_non_finite_json_constants(self):
        constants = [float("nan"), float("inf"), float("-inf")]

        for constant in constants:
            with self.subTest(constant=constant):
                payload = _valid_payload()
                payload["non_finite_fixture"] = constant
                judge_output = "report\nFINAL_JSON:\n" + json.dumps(payload)

                result = validate_judge_output({"judge_output": judge_output})
                errors = json.loads(result["validation_errors"])

                self.assertEqual(result["validation_status"], "fail")
                self.assertTrue(
                    any("invalid_json_constant" in error for error in errors),
                    errors,
                )

    def test_validator_priority_pairs_match_non_disabled_gate_reroutes(self):
        reroute_pairs = {
            tuple(sorted((source_id, reroute["to"])))
            for reroute in REROUTES
            for source_id in reroute["from"]
            if source_id != 19 and reroute["to"] != 19
        }

        self.assertEqual(set(PRIORITY_CONFLICT_PAIRS), reroute_pairs)

    def test_validator_output_keys_remain_unchanged(self):
        result = validate_judge_output(
            _validator_params(finalization_status="pass", finalizer_errors="[]")
        )

        self.assertEqual(
            set(result),
            {
                "validation_status",
                "validation_errors",
                "validated_final_json",
                "final_report_text",
                "room_id",
                "hit_category_ids",
                "no_hit_category_ids",
                "unable_to_judge_category_ids",
            },
        )


if __name__ == "__main__":
    unittest.main()
