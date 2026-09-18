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
        final_results = []
        for category_id in range(1, 20):
            if category_id == 19:
                final_results.append(
                    {
                        "category_id": 19,
                        "category_name": "隐私敏感商品低质问题",
                        "decision": "hit",
                        "confidence": "high",
                        "evidence_count": 1,
                        "evidence": [{"source": "Segment #1 ASR", "quote_or_visual_detail": "sanitary pads"}],
                        "judge_reason": "disabled category regression fixture",
                        "materials_used": ["segment_asr"],
                        "product_image_used": False,
                        "product_image_permission_ok": True,
                        "priority_rule_applied": [],
                    }
                )
            else:
                final_results.append(
                    {
                        "category_id": category_id,
                        "category_name": f"category {category_id}",
                        "decision": "no_hit",
                        "confidence": "medium",
                        "evidence_count": 0,
                        "evidence": [],
                        "judge_reason": "fixture",
                        "materials_used": [],
                        "product_image_used": False,
                        "product_image_permission_ok": True,
                        "priority_rule_applied": [],
                    }
                )

        payload = {
            "room_id": "fixture-room",
            "final_results": final_results,
            "hit_category_ids": [19],
            "no_hit_category_ids": list(range(1, 19)),
            "unable_to_judge_category_ids": [],
        }
        result = validate_judge_output({"judge_output": "report\nFINAL_JSON:\n" + json.dumps(payload)})

        self.assertEqual(result["validation_status"], "fail")
        self.assertIn("disabled_category_19_hit", json.loads(result["validation_errors"]))


if __name__ == "__main__":
    unittest.main()
