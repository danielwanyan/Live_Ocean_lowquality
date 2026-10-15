import json
import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from output_validator_node import validate_judge_output


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
                "category_name": f"category {category_id}",
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
        evidence = [{"source": "Segment #1 ASR", "quote_or_visual_detail": "sanitary pads"}]
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
        self.assertIn(
            'finalizer_errors:["invalid_final_result_decision:3"]',
            errors,
        )

    def test_validator_propagates_finalizer_warning(self):
        result = validate_judge_output(
            _validator_params(
                finalization_status="warning",
                finalizer_errors={"audit": ["category_5_rerouted"]},
            )
        )

        errors = json.loads(result["validation_errors"])
        self.assertEqual(result["validation_status"], "warning")
        self.assertIn("boundary_finalization_warning", errors)
        self.assertTrue(any(message.startswith("finalizer_errors:") for message in errors))

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

    def test_validator_rejects_unknown_finalizer_status(self):
        result = validate_judge_output(
            _validator_params(finalization_status="partial", finalizer_errors="[]")
        )

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn(
            "invalid_finalization_status",
            json.loads(result["validation_errors"]),
        )

    def test_validator_rejects_finalizer_errors_with_pass_status(self):
        result = validate_judge_output(
            _validator_params(
                finalization_status="pass",
                finalizer_errors='["unexpected audit"]',
            )
        )

        errors = json.loads(result["validation_errors"])
        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("unexpected_finalizer_errors", errors)
        self.assertIn('finalizer_errors:["unexpected audit"]', errors)

    def test_validator_rejects_shared_evidence_priority_conflicts(self):
        shared_evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "the exact same evidence",
            }
        ]
        cases = [
            ((3, 5), "priority_conflict_category_3_and_5"),
            ((3, 6), "priority_conflict_category_3_and_6"),
            ((5, 6), "priority_conflict_category_5_and_6"),
            ((8, 15), "priority_conflict_category_8_and_15"),
            ((1, 19), "priority_conflict_category_1_and_19"),
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
                if 19 in pair:
                    self.assertIn("disabled_category_19_hit", errors)

    def test_validator_allows_priority_pairs_with_distinct_evidence(self):
        cases = [(3, 5), (3, 6), (5, 6), (8, 15), (1, 19)]

        for pair in cases:
            with self.subTest(pair=pair):
                evidence_by_id = {
                    pair[0]: [
                        {
                            "source": "Segment #1 ASR",
                            "quote_or_visual_detail": "evidence for category %d" % pair[0],
                        }
                    ],
                    pair[1]: [
                        {
                            "source": "Segment #2 ASR",
                            "quote_or_visual_detail": "evidence for category %d" % pair[1],
                        }
                    ],
                }
                payload = _valid_payload(hit_ids=pair, evidence_by_id=evidence_by_id)
                result = validate_judge_output(_validator_params(payload))
                errors = json.loads(result["validation_errors"])
                expected_code = "priority_conflict_category_%d_and_%d" % pair

                self.assertNotIn(expected_code, errors)
                if 19 in pair:
                    self.assertEqual(errors, ["disabled_category_19_hit"])
                else:
                    self.assertEqual(result["validation_status"], "pass")
                    self.assertEqual(errors, [])

    def test_validator_handles_malformed_evidence_without_priority_crash(self):
        payload = _valid_payload(hit_ids=[3, 5])
        by_id = {item["category_id"]: item for item in payload["final_results"]}
        by_id[3]["evidence"] = [None, {"source": [], "quote_or_visual_detail": {}}]
        by_id[3]["evidence_count"] = 2
        by_id[5]["evidence"] = ["not-an-object"]
        by_id[5]["evidence_count"] = 1

        result = validate_judge_output(_validator_params(payload))

        self.assertNotIn(
            "priority_conflict_category_3_and_5",
            json.loads(result["validation_errors"]),
        )

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
