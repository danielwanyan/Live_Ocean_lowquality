import asyncio
import json
import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from live_boundary_gate_builder import (
    BOUNDARY_CONTRACT_VERSION,
    GATE_DEFINITIONS,
    REQUIRED_FACTS,
    REROUTES,
    build_boundary_gate_output,
    main,
)


EXPECTED_CONTRACT_VERSION = "2026-10-15-v3-cross-project-boundary-gates"
EXPECTED_REQUIRED_FACTS = [
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
]
EXPECTED_GATE_DEFINITIONS = {
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
EXPECTED_REROUTES = [
    {
        "from": [5],
        "to": 3,
        "rule": "priority_3_over_5_for_unrelated_content",
    },
    {
        "from": [6],
        "to": 3,
        "rule": "priority_3_over_6",
    },
    {
        "from": [6],
        "to": 5,
        "rule": "priority_5_over_6_for_no_physical_display",
    },
    {
        "from": [8],
        "to": 15,
        "rule": "priority_15_over_8_for_product_mismatch",
    },
    {
        "from": [19],
        "to": 1,
        "rule": "priority_1_over_19",
    },
]
EXPECTED_RETURN_KEYS = {
    "boundary_gates_json",
    "boundary_gate_panel",
    "boundary_output_schema_json",
    "boundary_contract_version",
    "boundary_builder_warnings",
}


class BoundaryGateBuilderTest(unittest.TestCase):
    def test_builds_versioned_gate_contract_with_available_materials(self):
        result = build_boundary_gate_output(
            {
                "segments_json": json.dumps(
                    [
                        {
                            "segment_index": 1,
                            "asr_summary": "The host explains the promoted product.",
                            "frame_urls": ["https://example.com/frame.jpg"],
                        }
                    ]
                ),
                "comment_interaction": "A viewer asks about sizing.",
                "product_catalog_json": json.dumps(
                    [
                        {
                            "title": "Example product",
                            "image_urls": ["https://example.com/product.jpg"],
                        }
                    ]
                ),
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        schema = json.loads(result["boundary_output_schema_json"])

        self.assertEqual(BOUNDARY_CONTRACT_VERSION, EXPECTED_CONTRACT_VERSION)
        self.assertEqual(REQUIRED_FACTS, EXPECTED_REQUIRED_FACTS)
        self.assertEqual(gates["contract_version"], EXPECTED_CONTRACT_VERSION)
        self.assertEqual(gates["rules_version"], EXPECTED_CONTRACT_VERSION)
        self.assertEqual(gates["required_facts"], EXPECTED_REQUIRED_FACTS)
        self.assertEqual(
            gates["material_availability"],
            {
                "segment_frame": True,
                "segment_asr": True,
                "comment_interaction": True,
                "pearl_product_title": True,
                "pearl_product_image": True,
            },
        )
        self.assertEqual(gates["disabled_category_ids"], [19])
        self.assertIn("80%+ occlusion", result["boundary_gate_panel"])
        self.assertNotIn("still_frame", result["boundary_gate_panel"])
        self.assertEqual(schema["contract_version"], EXPECTED_CONTRACT_VERSION)
        self.assertEqual(schema["required_facts"], EXPECTED_REQUIRED_FACTS)
        self.assertEqual(json.loads(result["boundary_builder_warnings"]), [])
        self.assertEqual(
            schema["fact_shape"],
            {
                "value": "Boolean",
                "evidence_sources": "Array<String>",
                "evidence_detail": "String",
            },
        )

    def test_reports_missing_material_availability_and_warnings(self):
        result = build_boundary_gate_output(
            {
                "segments_json": "[]",
                "comment_interaction": "",
                "product_catalog_json": "[]",
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertEqual(
            gates["material_availability"],
            {
                "segment_frame": False,
                "segment_asr": False,
                "comment_interaction": False,
                "pearl_product_title": False,
                "pearl_product_image": False,
            },
        )
        self.assertIn("segment_frame_missing", warnings)
        self.assertIn("segment_asr_missing", warnings)
        self.assertIn("product_catalog_missing", warnings)

    def test_non_string_asr_values_are_unavailable(self):
        for value in (False, True, 0, 1, {"summary": "not valid ASR"}):
            with self.subTest(value=value):
                result = build_boundary_gate_output(
                    {
                        "segments_json": [{"asr_summary": value, "frame_urls": []}],
                        "comment_interaction": "",
                        "product_catalog_json": [],
                        "rules_version": EXPECTED_CONTRACT_VERSION,
                    }
                )
                gates = json.loads(result["boundary_gates_json"])

                self.assertFalse(gates["material_availability"]["segment_asr"])

    def test_non_string_product_titles_are_unavailable(self):
        for value in (False, True, 0, 1, {"title": "not valid title text"}):
            with self.subTest(value=value):
                result = build_boundary_gate_output(
                    {
                        "segments_json": [],
                        "comment_interaction": "",
                        "product_catalog_json": [{"title": value, "image_urls": []}],
                        "rules_version": EXPECTED_CONTRACT_VERSION,
                    }
                )
                gates = json.loads(result["boundary_gates_json"])

                self.assertFalse(gates["material_availability"]["pearl_product_title"])

    def test_non_string_comment_interaction_values_are_unavailable(self):
        invalid_values = (False, True, 0, 1, {"comment": "not valid text"}, ["not valid text"])
        for value in invalid_values:
            with self.subTest(value=value):
                result = build_boundary_gate_output(
                    {
                        "segments_json": [],
                        "comment_interaction": value,
                        "product_catalog_json": [],
                        "rules_version": EXPECTED_CONTRACT_VERSION,
                    }
                )
                gates = json.loads(result["boundary_gates_json"])

                self.assertFalse(gates["material_availability"]["comment_interaction"])

    def test_url_lists_with_no_nonblank_string_are_unavailable(self):
        invalid_lists = (
            [0],
            [1],
            [False],
            [True],
            [{"url": "not a valid list item"}],
            [""],
            ["   "],
            [0, True, {"url": "not a valid list item"}, "   "],
        )
        for value in invalid_lists:
            with self.subTest(field="frame_urls", value=value):
                result = build_boundary_gate_output(
                    {
                        "segments_json": [{"asr_summary": "", "frame_urls": value}],
                        "comment_interaction": "",
                        "product_catalog_json": [],
                        "rules_version": EXPECTED_CONTRACT_VERSION,
                    }
                )
                gates = json.loads(result["boundary_gates_json"])
                self.assertFalse(gates["material_availability"]["segment_frame"])

            with self.subTest(field="image_urls", value=value):
                result = build_boundary_gate_output(
                    {
                        "segments_json": [],
                        "comment_interaction": "",
                        "product_catalog_json": [{"title": "", "image_urls": value}],
                        "rules_version": EXPECTED_CONTRACT_VERSION,
                    }
                )
                gates = json.loads(result["boundary_gates_json"])
                self.assertFalse(gates["material_availability"]["pearl_product_image"])

    def test_url_lists_with_a_nonblank_string_are_available(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [{"asr_summary": "", "frame_urls": [0, " https://example.com/frame.jpg "]}],
                "comment_interaction": "",
                "product_catalog_json": [
                    {"title": "", "image_urls": [False, " https://example.com/product.jpg "]}
                ],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )
        gates = json.loads(result["boundary_gates_json"])

        self.assertTrue(gates["material_availability"]["segment_frame"])
        self.assertTrue(gates["material_availability"]["pearl_product_image"])

    def test_json_url_lists_with_a_nonblank_string_are_available(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [
                    {
                        "asr_summary": "",
                        "frame_urls": json.dumps([0, "https://example.com/frame.jpg"]),
                    }
                ],
                "comment_interaction": "",
                "product_catalog_json": [
                    {
                        "title": "",
                        "image_urls": json.dumps([False, "https://example.com/product.jpg"]),
                    }
                ],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )
        gates = json.loads(result["boundary_gates_json"])

        self.assertTrue(gates["material_availability"]["segment_frame"])
        self.assertTrue(gates["material_availability"]["pearl_product_image"])

    def test_malformed_frame_urls_string_is_unavailable(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [
                    {
                        "asr_summary": "Valid ASR",
                        "frame_urls": "not-json",
                    }
                ],
                "comment_interaction": "Valid comment",
                "product_catalog_json": [],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertFalse(gates["material_availability"]["segment_frame"])
        self.assertIn("segment_frame_missing", warnings)

    def test_malformed_product_image_urls_string_is_unavailable(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [
                    {
                        "title": "",
                        "image_urls": "not-json",
                    }
                ],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertFalse(gates["material_availability"]["pearl_product_image"])
        self.assertIn("product_catalog_missing", warnings)

    def test_rules_version_mismatch_adds_warning(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [],
                "rules_version": "different-version",
            }
        )

        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertIn("rules_version_mismatch", warnings)

    def test_title_only_catalog_is_available_without_product_missing_warning(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [{"title": "Title only", "image_urls": []}],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertTrue(gates["material_availability"]["pearl_product_title"])
        self.assertFalse(gates["material_availability"]["pearl_product_image"])
        self.assertNotIn("product_catalog_missing", warnings)

    def test_image_only_catalog_is_available_without_product_missing_warning(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [
                    {
                        "title": "",
                        "image_urls": ["https://example.com/product.jpg"],
                    }
                ],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )

        gates = json.loads(result["boundary_gates_json"])
        warnings = json.loads(result["boundary_builder_warnings"])

        self.assertFalse(gates["material_availability"]["pearl_product_title"])
        self.assertTrue(gates["material_availability"]["pearl_product_image"])
        self.assertNotIn("product_catalog_missing", warnings)

    def test_reroutes_and_generated_content_gates_are_exact(self):
        result = build_boundary_gate_output(
            {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }
        )
        gates = json.loads(result["boundary_gates_json"])

        self.assertEqual(gates["reroutes"], EXPECTED_REROUTES)
        self.assertEqual(REROUTES, EXPECTED_REROUTES)
        self.assertEqual(
            set(gates["gate_definitions"]),
            {"1", "2", "3", "5", "6", "9", "10", "11", "12", "14", "15", "18", "19"},
        )
        self.assertEqual(gates["gate_definitions"], EXPECTED_GATE_DEFINITIONS)
        self.assertEqual(GATE_DEFINITIONS, EXPECTED_GATE_DEFINITIONS)
        self.assertEqual(
            gates["gate_definitions"]["15"]["alternative_true"],
            ["category_15_non_ipp_illegal_basis_found"],
        )
        self.assertEqual(
            gates["gate_definitions"]["9"]["required_true"],
            [
                "explicit_generated_content_evidence_found",
                "authenticity_misleading_found",
            ],
        )
        self.assertEqual(
            gates["gate_definitions"]["10"]["required_true"],
            [
                "explicit_generated_content_evidence_found",
                "generated_product_material_mismatch_found",
            ],
        )
        self.assertNotEqual(
            gates["gate_definitions"]["9"]["required_true"],
            gates["gate_definitions"]["10"]["required_true"],
        )

    def test_return_key_set_is_exact(self):
        result = build_boundary_gate_output({})

        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)

    def test_async_main_adapter_returns_exact_contract(self):
        class StubArgs:
            params = {
                "segments_json": [],
                "comment_interaction": "",
                "product_catalog_json": [],
                "rules_version": EXPECTED_CONTRACT_VERSION,
            }

        result = asyncio.run(main(StubArgs()))

        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)
        self.assertEqual(result["boundary_contract_version"], EXPECTED_CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
