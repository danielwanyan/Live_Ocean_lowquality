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
    build_boundary_gate_output,
)
from live_boundary_finalizer import finalize_judge_output, main


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
    return {name: fact() for name in EXPECTED_REQUIRED_FACTS}


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
    segments_json = json.dumps(
        [
            {
                "segment_index": 1,
                "asr_summary": "The host explains the promoted product.",
                "frame_urls": ["https://example.com/live-frame.jpg"],
            }
        ]
    )
    comment_interaction = "A viewer asks about the product size."
    product_catalog_json = json.dumps(
        [
            {
                "product_index": 1,
                "title": "Example product",
                "image_urls": ["https://example.com/product.jpg"],
            }
        ]
    )
    material_summary = payload.get("material_summary")
    if type(material_summary) is not dict:
        material_summary = {}
    material_quality_warning = json.dumps(
        material_summary.get("material_quality_warning", [])
    )
    gate_output = build_boundary_gate_output(
        {
            "segments_json": segments_json,
            "segment_count": 1,
            "comment_interaction": comment_interaction,
            "product_catalog_json": product_catalog_json,
            "product_count": 1,
            "material_quality_warning": material_quality_warning,
            "rules_version": BOUNDARY_CONTRACT_VERSION,
        }
    )
    if judge_output is None:
        judge_output = "Judge report\nFINAL_JSON:\n" + json.dumps(payload, ensure_ascii=False)
    return {
        "judge_output": judge_output,
        "boundary_gates_json": gate_output["boundary_gates_json"],
        "boundary_contract_version": gate_output["boundary_contract_version"],
        "rules_version": BOUNDARY_CONTRACT_VERSION,
        "room_id": payload.get("room_id"),
        "segments_json": segments_json,
        "segment_count": 1,
        "comment_interaction": comment_interaction,
        "product_catalog_json": product_catalog_json,
        "product_count": 1,
        "material_quality_warning": material_quality_warning,
    }


def build_params_with_availability(payload, **availability_overrides):
    params = build_params(payload)
    segments = json.loads(params["segments_json"])
    products = json.loads(params["product_catalog_json"])
    if availability_overrides.get("segment_frame") is False:
        for segment in segments:
            segment["frame_urls"] = []
    if availability_overrides.get("segment_asr") is False:
        for segment in segments:
            segment["asr_summary"] = ""
    if availability_overrides.get("pearl_product_title") is False:
        for product in products:
            product["title"] = ""
    if availability_overrides.get("pearl_product_image") is False:
        for product in products:
            product["image_urls"] = []
    if availability_overrides.get("comment_interaction") is False:
        params["comment_interaction"] = ""
    params["segments_json"] = json.dumps(segments)
    params["product_catalog_json"] = json.dumps(products)
    gate_output = build_boundary_gate_output(
        {
            "segments_json": params["segments_json"],
            "segment_count": params["segment_count"],
            "comment_interaction": params["comment_interaction"],
            "product_catalog_json": params["product_catalog_json"],
            "product_count": params["product_count"],
            "material_quality_warning": params["material_quality_warning"],
            "rules_version": params["rules_version"],
        }
    )
    params["boundary_gates_json"] = gate_output["boundary_gates_json"]
    return params


def rebuild_gate_from_trusted_params(params):
    gate_output = build_boundary_gate_output(
        {
            "segments_json": params["segments_json"],
            "segment_count": params["segment_count"],
            "comment_interaction": params["comment_interaction"],
            "product_catalog_json": params["product_catalog_json"],
            "product_count": params["product_count"],
            "material_quality_warning": params["material_quality_warning"],
            "rules_version": params["rules_version"],
        }
    )
    params["boundary_gates_json"] = gate_output["boundary_gates_json"]
    params["boundary_contract_version"] = gate_output["boundary_contract_version"]
    return params


def build_params_with_trusted_materials(
    payload,
    segments,
    segment_count,
    comment_interaction,
    products,
    product_count,
    warnings=None,
):
    params = build_params(payload)
    params["segments_json"] = json.dumps(segments)
    params["segment_count"] = segment_count
    params["comment_interaction"] = comment_interaction
    params["product_catalog_json"] = json.dumps(products)
    params["product_count"] = product_count
    params["material_quality_warning"] = json.dumps(warnings or [])
    return rebuild_gate_from_trusted_params(params)


def category_result(payload, category_id):
    return next(
        item for item in payload["final_results"] if item["category_id"] == category_id
    )


def set_fact(payload, fact_name, source="Segment #1 frame", detail=None):
    if detail is None:
        detail = "Concrete evidence for " + fact_name
    payload["boundary_checks"]["facts"][fact_name] = fact(
        True,
        evidence_sources=[source],
        evidence_detail=detail,
    )


def set_fact_sources(payload, fact_name, sources, detail=None):
    if detail is None:
        detail = "Concrete evidence for " + fact_name
    payload["boundary_checks"]["facts"][fact_name] = fact(
        True,
        evidence_sources=list(sources),
        evidence_detail=detail,
    )


def set_decision(payload, category_id, decision):
    item = category_result(payload, category_id)
    item["decision"] = decision
    if decision == "hit":
        item["evidence"] = [
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "Original model evidence.",
                "reason": "Original model reason.",
            }
        ]
        item["evidence_count"] = 1
        item["materials_used"] = ["segment_frame"]
        item["judge_reason"] = "Original model hit."
    else:
        item["evidence"] = []
        item["evidence_count"] = 0
        item["materials_used"] = []
        item["judge_reason"] = "Original model " + decision + "."
    item["product_image_used"] = False

    payload["hit_category_ids"] = sorted(
        result["category_id"]
        for result in payload["final_results"]
        if result["decision"] == "hit"
    )
    payload["no_hit_category_ids"] = sorted(
        result["category_id"]
        for result in payload["final_results"]
        if result["decision"] == "no_hit"
    )
    payload["unable_to_judge_category_ids"] = sorted(
        result["category_id"]
        for result in payload["final_results"]
        if result["decision"] == "unable_to_judge"
    )


def finalized_payload(result):
    return json.loads(result["finalized_final_json"])


def customize_hit(payload, category_id, evidence, reason, confidence):
    item = category_result(payload, category_id)
    item["evidence"] = copy.deepcopy(evidence)
    item["evidence_count"] = len(evidence)
    item["judge_reason"] = reason
    item["confidence"] = confidence
    materials = set()
    for entry in evidence:
        source = entry["source"]
        if source == "Comment Interaction":
            materials.add("comment_interaction")
        elif source.startswith("Pearl product #") and source.endswith(" title"):
            materials.add("pearl_product_title")
        elif source.startswith("Pearl product #") and source.endswith(" image"):
            materials.add("pearl_product_image")
        elif source.startswith("Segment #") and source.endswith(" ASR"):
            materials.add("segment_asr")
        elif source.startswith("Segment #") and source.endswith(" visible text"):
            materials.add("segment_frame_visible_text")
        elif source.startswith("Segment #") and source.endswith(" frame"):
            materials.add("segment_frame")
    item["materials_used"] = sorted(materials)
    item["product_image_used"] = "pearl_product_image" in materials


def set_complete_category_12_facts(payload):
    set_fact(payload, "concrete_live_effect_claim_found", source="Segment #1 ASR")
    set_fact(payload, "materially_misleading_basis_found", source="Pearl product #1 image")
    set_fact(
        payload,
        "effect_claim_prevalence_or_strength_threshold_met",
        source="Pearl product #1 title",
    )


class LiveBoundaryFinalizerTest(unittest.TestCase):
    def assert_failure(self, result, expected_error):
        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)
        self.assertEqual(result["finalized_judge_output"], "")
        self.assertEqual(result["finalized_final_json"], "")
        self.assertEqual(result["finalization_status"], "fail")
        self.assertEqual(result["boundary_override_log"], "[]")
        self.assertIn(expected_error, json.loads(result["finalizer_errors"]))

    def assert_decision(self, payload, category_id, expected_decision):
        self.assertEqual(
            category_result(payload, category_id)["decision"],
            expected_decision,
        )

    def assert_payload_failure_no_raise(self, payload, expected_error):
        try:
            result = finalize_judge_output(build_params(payload))
        except Exception as exc:
            self.fail("finalizer raised instead of failing closed: " + str(exc))
        self.assert_failure(result, expected_error)

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
        missing_name = EXPECTED_REQUIRED_FACTS[0]
        del payload["boundary_checks"]["facts"][missing_name]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "missing_boundary_fact:" + missing_name)

    def test_boundary_fact_value_must_be_exact_bool(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["value"] = 1

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_value_not_bool:" + fact_name)

    def test_boundary_fact_evidence_sources_must_be_exact_list(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["evidence_sources"] = "Segment #1 frame"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_evidence_sources_not_list:" + fact_name)

    def test_true_fact_requires_nonblank_source_and_detail(self):
        fact_name = EXPECTED_REQUIRED_FACTS[0]
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

    def test_supported_contradictory_boundary_facts_fail_closed(self):
        cases = (
            (
                "sexualized_exposure_or_behavior_found",
                "Segment #1 frame",
                "ordinary_tryon_or_public_context_only",
                "Segment #1 ASR",
            ),
            (
                "unrelated_content_dominates",
                "Segment #1 frame",
                "sustained_product_promotion_found",
                "Segment #1 ASR",
            ),
            (
                "extremely_low_information_across_relevant_segments",
                "Segment #1 ASR",
                "core_buying_information_found",
                "Segment #1 ASR",
            ),
            (
                "extremely_low_information_across_relevant_segments",
                "Segment #1 ASR",
                "identifiable_product_and_core_purpose_found",
                "Segment #1 frame",
            ),
            (
                "concrete_replay_indicator_found",
                "Segment #1 frame",
                "replay_weak_signal_only",
                "Segment #1 ASR",
            ),
            (
                "concrete_live_effect_claim_found",
                "Segment #1 ASR",
                "marketing_or_product_image_only",
                "Pearl product #1 image",
            ),
            (
                "materially_misleading_basis_found",
                "Pearl product #1 image",
                "marketing_or_product_image_only",
                "Pearl product #1 image",
            ),
            (
                "core_product_contradiction_found",
                "Segment #1 ASR",
                "minor_variant_or_background_only",
                "Segment #1 frame",
            ),
            (
                "sustained_negative_emotion_found",
                "Segment #1 ASR",
                "routine_sales_or_knowledge_marketing_only",
                "Comment Interaction",
            ),
            (
                "hostile_shaming_fear_evidence_found",
                "Segment #1 frame",
                "routine_sales_or_knowledge_marketing_only",
                "Comment Interaction",
            ),
        )

        for first_fact, first_source, second_fact, second_source in cases:
            with self.subTest(first_fact=first_fact, second_fact=second_fact):
                payload = valid_payload()
                set_fact(payload, first_fact, source=first_source)
                set_fact(payload, second_fact, source=second_source)

                result = finalize_judge_output(build_params(payload))

                self.assert_failure(
                    result,
                    "contradictory_boundary_facts:%s:%s"
                    % (first_fact, second_fact),
                )

    def test_raw_contradictory_facts_fail_even_with_unpublished_sources(self):
        pairs = (
            ("sexualized_exposure_or_behavior_found", "ordinary_tryon_or_public_context_only"),
            ("unrelated_content_dominates", "sustained_product_promotion_found"),
            ("extremely_low_information_across_relevant_segments", "core_buying_information_found"),
            ("extremely_low_information_across_relevant_segments", "identifiable_product_and_core_purpose_found"),
            ("concrete_replay_indicator_found", "replay_weak_signal_only"),
            ("concrete_live_effect_claim_found", "marketing_or_product_image_only"),
            ("materially_misleading_basis_found", "marketing_or_product_image_only"),
            ("core_product_contradiction_found", "minor_variant_or_background_only"),
            ("sustained_negative_emotion_found", "routine_sales_or_knowledge_marketing_only"),
            ("hostile_shaming_fear_evidence_found", "routine_sales_or_knowledge_marketing_only"),
        )

        for first_fact, second_fact in pairs:
            with self.subTest(first_fact=first_fact, second_fact=second_fact):
                payload = valid_payload()
                set_fact(payload, first_fact, source="Segment #999 frame")
                set_fact(payload, second_fact, source="Segment #999 frame")

                result = finalize_judge_output(build_params(payload))

                self.assert_failure(
                    result,
                    "contradictory_boundary_facts:%s:%s"
                    % (first_fact, second_fact),
                )

    def test_gate_contract_version_mismatch_fails_closed(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["contract_version"] = "stale-gate-version"
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_contract_version_mismatch")

    def test_gate_rules_version_mismatch_fails_closed(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["rules_version"] = "stale-gate-rules-version"
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_rules_version_mismatch")

    def test_model_boundary_contract_version_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["boundary_checks"]["contract_version"] = "stale-model-version"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_contract_version_mismatch")

    def test_missing_input_rules_version_fails_closed(self):
        params = build_params()
        del params["rules_version"]

        result = finalize_judge_output(params)

        self.assert_failure(result, "rules_version_mismatch")

    def test_stale_input_rules_version_fails_closed(self):
        params = build_params()
        params["rules_version"] = "stale-input-rules-version"

        result = finalize_judge_output(params)

        self.assert_failure(result, "rules_version_mismatch")

    def test_payload_rules_version_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["rules_version"] = "stale-rules-version"

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "payload_rules_version_mismatch")

    def test_stale_but_internally_consistent_versions_fail_local_contract(self):
        stale_version = "stale-but-consistent"
        payload = valid_payload()
        payload["rules_version"] = stale_version
        payload["boundary_checks"]["contract_version"] = stale_version
        params = build_params(payload)
        gates = json.loads(params["boundary_gates_json"])
        gates["contract_version"] = stale_version
        gates["rules_version"] = stale_version
        params["boundary_gates_json"] = gates
        params["boundary_contract_version"] = stale_version
        params["rules_version"] = stale_version

        result = finalize_judge_output(params)

        self.assertEqual(result["finalization_status"], "fail")
        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)

    def test_trusted_normalize_inputs_fail_closed_on_invalid_types_or_json(self):
        cases = (
            ("segments_json", "{}", "segments_json_invalid"),
            ("segments_json", "[1]", "segments_json_invalid"),
            ("segments_json", [], "segments_json_invalid"),
            ("segment_count", True, "segment_count_invalid"),
            ("segment_count", -1, "segment_count_invalid"),
            ("comment_interaction", 1, "comment_interaction_invalid"),
            ("product_catalog_json", "{}", "product_catalog_json_invalid"),
            ("product_catalog_json", "[1]", "product_catalog_json_invalid"),
            ("product_catalog_json", [], "product_catalog_json_invalid"),
            ("product_count", False, "product_count_invalid"),
            ("product_count", -1, "product_count_invalid"),
            ("material_quality_warning", "{}", "material_quality_warning_invalid"),
            (
                "material_quality_warning",
                json.dumps(["valid", 1]),
                "material_quality_warning_invalid",
            ),
        )

        for field_name, invalid_value, expected_error in cases:
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                params = build_params()
                params[field_name] = invalid_value

                result = finalize_judge_output(params)

                self.assert_failure(result, expected_error)

    def test_each_trusted_normalize_input_is_required(self):
        expected_errors = {
            "segments_json": "segments_json_invalid",
            "segment_count": "segment_count_invalid",
            "comment_interaction": "comment_interaction_invalid",
            "product_catalog_json": "product_catalog_json_invalid",
            "product_count": "product_count_invalid",
            "material_quality_warning": "material_quality_warning_invalid",
        }

        for field_name, expected_error in expected_errors.items():
            with self.subTest(field_name=field_name):
                params = build_params()
                del params[field_name]

                self.assert_failure(finalize_judge_output(params), expected_error)

    def test_all_trusted_inputs_absent_cannot_use_legacy_gate_manifest(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sexualized_exposure_or_behavior_found",
            source="Segment #1 frame",
        )
        params = build_params(payload)
        for field_name in (
            "segments_json",
            "segment_count",
            "comment_interaction",
            "product_catalog_json",
            "product_count",
            "material_quality_warning",
        ):
            del params[field_name]
        gates = json.loads(params["boundary_gates_json"])
        gates["declared_counts"] = {
            "segment_count": None,
            "product_count": None,
        }
        gates["material_reliability"] = {
            "segments": False,
            "products": False,
            "comment": True,
        }
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assertEqual(result["finalization_status"], "fail")
        errors = json.loads(result["finalizer_errors"])
        self.assertIn("segments_json_invalid", errors)
        self.assertIn("product_catalog_json_invalid", errors)

    def test_gate_manifest_and_dynamic_metadata_must_match_trusted_reconstruction(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["allowed_source_labels"].append("Segment #999 frame")
        gates["allowed_source_labels"].sort()
        params["boundary_gates_json"] = gates

        self.assert_failure(
            finalize_judge_output(params),
            "gate_source_manifest_mismatch",
        )

        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["observed_counts"]["segment_count"] = 999
        params["boundary_gates_json"] = gates

        self.assert_failure(
            finalize_judge_output(params),
            "gate_dynamic_metadata_mismatch",
        )

        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["declared_counts"]["segment_count"] = True
        params["boundary_gates_json"] = gates

        self.assert_failure(
            finalize_judge_output(params),
            "gate_dynamic_metadata_mismatch",
        )

    def test_empty_expected_boundary_contract_version_fails_closed(self):
        params = build_params()
        params["boundary_contract_version"] = "   "

        result = finalize_judge_output(params)

        self.assert_failure(result, "boundary_contract_version_missing")

    def test_numeric_expected_contract_version_is_not_coerced_to_text(self):
        payload = valid_payload()
        payload["rules_version"] = "123"
        payload["boundary_checks"]["contract_version"] = "123"
        params = build_params(payload)
        gates = json.loads(params["boundary_gates_json"])
        gates["contract_version"] = "123"
        gates["rules_version"] = "123"
        params["boundary_gates_json"] = gates
        params["boundary_contract_version"] = 123
        params["rules_version"] = 123

        result = finalize_judge_output(params)

        self.assert_failure(result, "boundary_contract_version_invalid")

    def test_numeric_version_fields_fail_their_exact_string_checks(self):
        cases = (
            ("gate_contract_version", "gate_contract_version_mismatch"),
            ("gate_rules_version", "gate_rules_version_mismatch"),
            ("input_rules_version", "rules_version_mismatch"),
            ("payload_rules_version", "payload_rules_version_mismatch"),
            ("model_contract_version", "boundary_contract_version_mismatch"),
        )

        for target, expected_error in cases:
            with self.subTest(target=target):
                payload = valid_payload()
                if target == "payload_rules_version":
                    payload["rules_version"] = 123
                elif target == "model_contract_version":
                    payload["boundary_checks"]["contract_version"] = 123
                params = build_params(payload)
                if target.startswith("gate_"):
                    gates = json.loads(params["boundary_gates_json"])
                    gate_key = "contract_version" if target == "gate_contract_version" else "rules_version"
                    gates[gate_key] = 123
                    params["boundary_gates_json"] = gates
                elif target == "input_rules_version":
                    params["rules_version"] = 123

                result = finalize_judge_output(params)

                self.assert_failure(result, expected_error)

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

    def test_final_results_container_and_count_fail_closed(self):
        cases = (
            (None, "final_results_missing_or_not_list"),
            ({}, "final_results_missing_or_not_list"),
            (valid_payload()["final_results"][:-1], "final_results_count_mismatch"),
            (valid_payload()["final_results"] + [copy.deepcopy(valid_payload()["final_results"][0])], "final_results_count_mismatch"),
        )

        for final_results, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                payload = valid_payload()
                payload["final_results"] = final_results

                self.assert_payload_failure_no_raise(payload, expected_error)

    def test_final_result_items_and_category_ids_fail_closed(self):
        cases = []

        payload = valid_payload()
        payload["final_results"][0] = []
        cases.append((payload, "final_result_item_not_object:index_0"))

        for invalid_id in (True, "1", 1.0):
            payload = valid_payload()
            payload["final_results"][0]["category_id"] = invalid_id
            cases.append((payload, "final_result_category_id_not_exact_int:index_0"))

        payload = valid_payload()
        payload["final_results"][0]["category_id"] = 20
        cases.append((payload, "final_result_category_id_out_of_range:20"))

        payload = valid_payload()
        payload["final_results"][1]["category_id"] = 1
        cases.append((payload, "duplicate_final_result_category_id:1"))

        payload = valid_payload()
        payload["final_results"][0]["category_id"] = 2
        payload["final_results"][1]["category_id"] = 20
        cases.append((payload, "final_result_category_ids_mismatch"))

        payload = valid_payload()
        payload["final_results"][0]["category_id"] = "mixed-sort-id"
        payload["final_results"][1]["category_id"] = None
        cases.append((payload, "final_result_category_id_not_exact_int:index_0"))

        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                self.assert_payload_failure_no_raise(payload, expected_error)

    def test_final_result_field_shapes_fail_closed(self):
        cases = []

        def add_case(field, value, expected_error):
            payload = valid_payload()
            payload["final_results"][0][field] = value
            cases.append((payload, expected_error))

        add_case("decision", "maybe", "invalid_final_result_decision:1")
        add_case("decision", [], "invalid_final_result_decision:1")
        add_case("evidence", None, "final_result_evidence_not_list:1")

        payload = valid_payload()
        payload["final_results"][0]["evidence"] = ["bad-entry"]
        payload["final_results"][0]["evidence_count"] = 1
        cases.append((payload, "final_result_evidence_item_not_object:1:index_0"))

        for evidence_field, invalid_value in (
            ("source", 1),
            ("quote_or_visual_detail", []),
            ("reason", None),
        ):
            payload = valid_payload()
            payload["final_results"][0]["evidence"] = [
                {
                    "source": "Segment #1 frame",
                    "quote_or_visual_detail": "detail",
                    "reason": "reason",
                }
            ]
            payload["final_results"][0]["evidence"][0][evidence_field] = invalid_value
            payload["final_results"][0]["evidence_count"] = 1
            cases.append(
                (
                    payload,
                    "final_result_evidence_%s_not_string:1:index_0" % evidence_field,
                )
            )

        add_case("evidence_count", True, "final_result_evidence_count_not_exact_int:1")
        add_case("evidence_count", 1, "final_result_evidence_count_mismatch:1")
        add_case("judge_reason", None, "final_result_judge_reason_not_string:1")
        add_case("materials_used", None, "final_result_materials_used_not_list:1")
        add_case("materials_used", [1], "final_result_material_not_string:1:index_0")
        add_case("product_image_used", 0, "final_result_product_image_used_not_bool:1")
        add_case(
            "product_image_permission_ok",
            1,
            "final_result_product_image_permission_ok_not_bool:1",
        )
        add_case("priority_rule_applied", None, "final_result_priority_rule_applied_not_list:1")
        add_case(
            "priority_rule_applied",
            [1],
            "final_result_priority_rule_not_string:1:index_0",
        )

        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                self.assert_payload_failure_no_raise(payload, expected_error)

    def test_existing_hit_evidence_reason_must_be_nonblank_string(self):
        cases = [
            ("missing", "final_result_evidence_reason_not_string:1:index_0"),
            (None, "final_result_evidence_reason_not_string:1:index_0"),
            (7, "final_result_evidence_reason_not_string:1:index_0"),
            ("", "invalid_final_result_evidence_reason:1"),
            ("   \t\n", "invalid_final_result_evidence_reason:1"),
        ]

        for reason, expected_error in cases:
            with self.subTest(reason=reason):
                payload = valid_payload()
                set_decision(payload, 1, "hit")
                set_fact(payload, "sexualized_exposure_or_behavior_found")
                evidence = payload["final_results"][0]["evidence"][0]
                if reason == "missing":
                    del evidence["reason"]
                else:
                    evidence["reason"] = reason

                self.assert_payload_failure_no_raise(payload, expected_error)

    def test_existing_hit_evidence_nonblank_reason_passes(self):
        payload = valid_payload()
        set_decision(payload, 1, "hit")
        set_fact(payload, "sexualized_exposure_or_behavior_found")
        payload["final_results"][0]["evidence"][0]["reason"] = "Usable reason."

        result = finalize_judge_output(build_params(payload))

        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(json.loads(result["finalizer_errors"]), [])

    def test_final_result_category_name_must_match_canonical_contract(self):
        for invalid_name in (None, 1, "Wrong category name"):
            with self.subTest(invalid_name=invalid_name):
                payload = valid_payload()
                payload["final_results"][0]["category_name"] = invalid_name

                self.assert_payload_failure_no_raise(
                    payload,
                    "final_result_category_name_mismatch:1",
                )

    def test_final_result_judge_reason_must_be_nonblank(self):
        payload = valid_payload()
        payload["final_results"][0]["judge_reason"] = "   "

        self.assert_payload_failure_no_raise(
            payload,
            "final_result_judge_reason_blank:1",
        )

    def test_gate_required_facts_must_match_independent_contract_exactly(self):
        adversarial_lists = (
            [],
            list(EXPECTED_REQUIRED_FACTS[:-1]),
            list(EXPECTED_REQUIRED_FACTS) + [EXPECTED_REQUIRED_FACTS[-1]],
            list(reversed(EXPECTED_REQUIRED_FACTS)),
            [0],
            [[]],
        )

        for required_facts in adversarial_lists:
            with self.subTest(required_facts=required_facts):
                params = build_params()
                gates = json.loads(params["boundary_gates_json"])
                gates["required_facts"] = required_facts
                params["boundary_gates_json"] = gates

                try:
                    result = finalize_judge_output(params)
                except Exception as exc:
                    self.fail("finalizer raised instead of failing closed: " + str(exc))

                self.assert_failure(result, "gate_required_facts_contract_mismatch")

    def test_changed_gate_definition_fails_closed_before_business_logic(self):
        payload = valid_payload()
        set_decision(payload, 1, "hit")
        set_fact(payload, "ordinary_tryon_or_public_context_only")
        params = build_params(payload)
        gates = json.loads(params["boundary_gates_json"])
        gates["gate_definitions"]["1"]["blocked_true"] = []
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_definitions_contract_mismatch")

    def test_gate_definition_scalar_types_must_match_exactly(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["gate_definitions"]["19"]["disabled"] = 1
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_definitions_contract_mismatch")

    def test_changed_reroute_fails_closed_before_business_logic(self):
        payload = valid_payload()
        set_decision(payload, 6, "hit")
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")
        params = build_params(payload)
        gates = json.loads(params["boundary_gates_json"])
        gates["reroutes"][2]["to"] = 3
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_reroutes_contract_mismatch")

    def test_reroute_scalar_types_must_match_exactly(self):
        params = build_params()
        gates = json.loads(params["boundary_gates_json"])
        gates["reroutes"][0]["to"] = 3.0
        params["boundary_gates_json"] = gates

        result = finalize_judge_output(params)

        self.assert_failure(result, "gate_reroutes_contract_mismatch")

    def test_gate_material_availability_contract_is_exact(self):
        def missing_key(gates):
            del gates["material_availability"]["segment_frame"]

        def extra_key(gates):
            gates["material_availability"]["segment_frame_visible_text"] = True

        def wrong_type(gates):
            gates["material_availability"]["segment_asr"] = 1

        for mutation in (missing_key, extra_key, wrong_type):
            with self.subTest(mutation=mutation.__name__):
                params = build_params()
                gates = json.loads(params["boundary_gates_json"])
                mutation(gates)
                params["boundary_gates_json"] = gates

                result = finalize_judge_output(params)

                self.assert_failure(result, "gate_material_availability_contract_mismatch")

    def test_gate_allowed_source_labels_contract_is_validated(self):
        def missing(gates):
            del gates["allowed_source_labels"]

        def duplicate(gates):
            gates["allowed_source_labels"].append(gates["allowed_source_labels"][0])

        def non_string(gates):
            gates["allowed_source_labels"][0] = 1

        def blank(gates):
            gates["allowed_source_labels"][0] = "   "

        def malformed(gates):
            gates["allowed_source_labels"][0] = "Segment unknown frame"

        def unavailable_channel(gates):
            gates["material_availability"]["segment_frame"] = False

        for mutation in (
            missing,
            duplicate,
            non_string,
            blank,
            malformed,
            unavailable_channel,
        ):
            with self.subTest(mutation=mutation.__name__):
                params = build_params()
                gates = json.loads(params["boundary_gates_json"])
                mutation(gates)
                params["boundary_gates_json"] = gates

                result = finalize_judge_output(params)

                self.assert_failure(result, "gate_allowed_source_labels_contract_mismatch")

    def test_room_id_is_required_and_must_match_payload(self):
        payload = valid_payload()

        missing_params = build_params(payload)
        del missing_params["room_id"]
        self.assert_failure(
            finalize_judge_output(missing_params),
            "room_id_missing_or_invalid",
        )

        for invalid_room_id in (1, True, None, "   "):
            with self.subTest(invalid_room_id=invalid_room_id):
                params = build_params(payload)
                params["room_id"] = invalid_room_id
                self.assert_failure(
                    finalize_judge_output(params),
                    "room_id_missing_or_invalid",
                )

        mismatch_params = build_params(payload)
        mismatch_params["room_id"] = "different-room"
        self.assert_failure(
            finalize_judge_output(mismatch_params),
            "room_id_mismatch",
        )

        matching_result = finalize_judge_output(build_params(payload))
        self.assertEqual(matching_result["finalization_status"], "pass")

    def test_fact_object_requires_exact_keys_when_true_detail_is_missing(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name] = fact(
            True,
            evidence_sources=["Segment #1 frame"],
            evidence_detail="Evidence detail",
        )
        del payload["boundary_checks"]["facts"][fact_name]["evidence_detail"]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_keys_mismatch:" + fact_name)

    def test_fact_object_rejects_extra_key(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["unexpected"] = False

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_keys_mismatch:" + fact_name)

    def test_fact_sources_reject_non_string_element(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["evidence_sources"] = [0]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_evidence_source_not_string:" + fact_name)

    def test_fact_detail_must_be_exact_string(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        payload["boundary_checks"]["facts"][fact_name]["evidence_detail"] = 1

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_evidence_detail_not_string:" + fact_name)

    def test_false_fact_still_requires_detail_key(self):
        payload = valid_payload()
        fact_name = EXPECTED_REQUIRED_FACTS[0]
        del payload["boundary_checks"]["facts"][fact_name]["evidence_detail"]

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(result, "boundary_fact_keys_mismatch:" + fact_name)

    def test_non_finite_json_constants_fail_closed(self):
        payload_json = json.dumps(valid_payload())
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                altered_json = payload_json.replace('"segment_count": 1', '"segment_count": ' + constant)

                result = finalize_judge_output(
                    build_params(judge_output="FINAL_JSON:\n" + altered_json)
                )

                errors = json.loads(result["finalizer_errors"])
                self.assertEqual(result["finalization_status"], "fail")
                self.assertTrue(any(error.startswith("final_json_parse_failed:") for error in errors))

    def test_non_finite_gate_json_fails_closed(self):
        params = build_params()
        gates_json = params["boundary_gates_json"]
        params["boundary_gates_json"] = gates_json[:-1] + ', "sentinel": NaN}'

        result = finalize_judge_output(params)

        errors = json.loads(result["finalizer_errors"])
        self.assertEqual(result["finalization_status"], "fail")
        self.assertTrue(any(error.startswith("boundary_gates_parse_failed:") for error in errors))

    def test_unterminated_json_fence_fails_closed(self):
        fence = chr(96) * 3
        judge_output = "FINAL_JSON:\n" + fence + "json\n" + json.dumps(valid_payload())

        result = finalize_judge_output(build_params(judge_output=judge_output))

        self.assert_failure(result, "final_json_fence_unclosed")

    def test_duplicate_final_json_markers_fail_closed(self):
        payload_json = json.dumps(valid_payload())
        judge_output = "FINAL_JSON:\n" + payload_json + "\nFINAL_JSON:\n" + payload_json

        result = finalize_judge_output(build_params(judge_output=judge_output))

        errors = json.loads(result["finalizer_errors"])
        self.assertEqual(result["finalization_status"], "fail")
        self.assertTrue(any(error.startswith("final_json_parse_failed:") for error in errors))

    def test_trailing_text_after_final_json_fails_closed(self):
        judge_output = "FINAL_JSON:\n" + json.dumps(valid_payload()) + "\ntrailing text"

        result = finalize_judge_output(build_params(judge_output=judge_output))

        errors = json.loads(result["finalizer_errors"])
        self.assertEqual(result["finalization_status"], "fail")
        self.assertTrue(any(error.startswith("final_json_parse_failed:") for error in errors))

    def test_fenced_valid_payload_passes(self):
        payload = valid_payload()
        fence = chr(96) * 3
        for opening in (fence, fence + "json"):
            with self.subTest(opening=opening):
                judge_output = "FINAL_JSON:\n" + opening + "\n" + json.dumps(payload) + "\n" + fence

                result = finalize_judge_output(build_params(judge_output=judge_output))

                self.assertEqual(result["finalization_status"], "pass")

    def test_marketing_and_routine_context_block_categories_12_and_18(self):
        payload = valid_payload()
        set_decision(payload, 12, "hit")
        set_decision(payload, 18, "hit")
        set_fact(payload, "marketing_or_product_image_only", source="Pearl product #1 image")
        set_fact(payload, "routine_sales_or_knowledge_marketing_only", source="Segment #1 ASR")

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)

        self.assertEqual(result["finalization_status"], "warning")
        self.assert_decision(finalized, 12, "no_hit")
        self.assert_decision(finalized, 18, "no_hit")
        self.assertEqual(
            sorted(item["category_id"] for item in finalized["boundary_overrides"]),
            [12, 18],
        )

    def test_cleaning_context_blocks_category_2(self):
        payload = valid_payload()
        set_decision(payload, 2, "hit")
        set_fact(payload, "disturbing_visual_dominates")
        set_fact(payload, "cleaning_demo_context")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 2, "no_hit")

    def test_unknown_cleaning_blocker_does_not_demote_category_2(self):
        payload = valid_payload()
        set_decision(payload, 2, "hit")
        set_fact(payload, "disturbing_visual_dominates", source="Segment #1 frame")
        set_fact(payload, "cleaning_demo_context", source="unknown cleaning keyword")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 2, "hit")

    def test_existing_category_2_hit_with_unknown_fact_source_is_demoted(self):
        payload = valid_payload()
        set_decision(payload, 2, "hit")
        set_fact(
            payload,
            "disturbing_visual_dominates",
            source="keyword-only detector",
            detail="Unsupported keyword observation.",
        )

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_2 = category_result(finalized, 2)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(category_2["decision"], "no_hit")
        self.assertEqual(category_2["evidence"], [])
        self.assertIn("允许材料证据", category_2["judge_reason"])
        self.assertTrue(
            any(item["category_id"] == 2 for item in finalized["boundary_overrides"])
        )

    def test_novelty_or_product_art_context_blocks_category_2(self):
        payload = valid_payload()
        set_decision(payload, 2, "hit")
        set_fact(payload, "disturbing_visual_dominates")
        set_fact(payload, "novelty_or_product_art_context")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 2, "no_hit")

    def test_ordinary_tryon_context_blocks_category_1(self):
        payload = valid_payload()
        set_decision(payload, 1, "hit")
        set_fact(payload, "sexualized_exposure_or_behavior_found")
        set_fact(payload, "ordinary_tryon_or_public_context_only")

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(
            result,
            "contradictory_boundary_facts:sexualized_exposure_or_behavior_found:ordinary_tryon_or_public_context_only",
        )

    def test_unsupported_ordinary_tryon_still_conflicts_with_sexual_fact(self):
        payload = valid_payload()
        set_decision(payload, 1, "hit")
        set_fact(payload, "sexualized_exposure_or_behavior_found", source="Segment #1 frame")
        set_fact(
            payload,
            "ordinary_tryon_or_public_context_only",
            source="Pearl product #1 image",
        )

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(
            result,
            "contradictory_boundary_facts:sexualized_exposure_or_behavior_found:ordinary_tryon_or_public_context_only",
        )

    def test_unavailable_frame_channel_cannot_promote_category_1(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sexualized_exposure_or_behavior_found",
            source="Segment #999 frame",
        )

        result = finalize_judge_output(
            build_params_with_availability(payload, segment_frame=False)
        )
        finalized = finalized_payload(result)

        self.assert_decision(finalized, 1, "no_hit")

    def test_unpublished_segment_identity_cannot_promote_category_1(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sexualized_exposure_or_behavior_found",
            source="Segment #999 frame",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 1, "no_hit")

    def test_category_3_cannot_promote_from_pearl_only_dominance(self):
        payload = valid_payload()
        set_fact(
            payload,
            "unrelated_content_dominates",
            source="Pearl product #1 image",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 3, "no_hit")

    def test_category_6_live_facts_cannot_be_supported_by_pearl_only_sources(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sustained_product_promotion_found",
            source="Pearl product #1 title",
        )
        set_fact(
            payload,
            "real_physical_product_display_found",
            source="Pearl product #1 image",
        )
        set_fact(
            payload,
            "extremely_low_information_across_relevant_segments",
            source="Pearl product #1 title",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 6, "no_hit")

    def test_real_physical_display_blocks_category_5(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")
        set_fact(payload, "real_physical_product_display_found")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 5, "no_hit")

    def test_core_buying_information_blocks_category_6(self):
        payload = valid_payload()
        set_decision(payload, 6, "hit")
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")
        set_fact(payload, "real_physical_product_display_found")
        set_fact(payload, "extremely_low_information_across_relevant_segments", source="Segment #1 ASR")
        set_fact(payload, "core_buying_information_found", source="Segment #1 ASR")

        result = finalize_judge_output(build_params(payload))

        self.assert_failure(
            result,
            "contradictory_boundary_facts:extremely_low_information_across_relevant_segments:core_buying_information_found",
        )

    def test_replay_weak_signal_only_blocks_category_11(self):
        payload = valid_payload()
        set_decision(payload, 11, "hit")
        set_fact(payload, "replay_weak_signal_only")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 11, "no_hit")

    def test_off_platform_destination_without_transaction_facts_blocks_category_14(self):
        payload = valid_payload()
        set_decision(payload, 14, "hit")
        set_fact(payload, "off_platform_destination_found", source="Segment #1 visible text")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 14, "no_hit")

    def test_minor_variant_and_core_contradiction_fail_even_with_alternative(self):
        for independent_non_ipp in (False, True):
            with self.subTest(independent_non_ipp=independent_non_ipp):
                payload = valid_payload()
                set_decision(payload, 15, "hit")
                set_fact(payload, "live_promoted_item_evidence_found")
                set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
                set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")
                set_fact(payload, "minor_variant_or_background_only")
                if independent_non_ipp:
                    set_fact_sources(
                        payload,
                        "category_15_non_ipp_illegal_basis_found",
                        ("Pearl product #1 title", "Segment #1 ASR"),
                    )

                result = finalize_judge_output(build_params(payload))

                self.assert_failure(
                    result,
                    "contradictory_boundary_facts:core_product_contradiction_found:minor_variant_or_background_only",
                )

    def test_category_19_is_always_forced_to_no_hit(self):
        for original_decision in ("hit", "unable_to_judge"):
            with self.subTest(original_decision=original_decision):
                payload = valid_payload()
                set_decision(payload, 19, original_decision)

                finalized = finalized_payload(finalize_judge_output(build_params(payload)))

                self.assert_decision(finalized, 19, "no_hit")

    def test_category_19_disabled_reason_precedes_generic_evidence_demotion(self):
        payload = valid_payload()
        set_decision(payload, 19, "hit")
        customize_hit(
            payload,
            19,
            [
                {
                    "source": "Comment Interaction",
                    "quote_or_visual_detail": "Unauthorized category 19 evidence.",
                    "reason": "Disabled rule must remain authoritative.",
                }
            ],
            "Original category 19 hit.",
            "medium",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_19 = category_result(finalized, 19)
        category_19_audits = [
            item
            for item in finalized["boundary_overrides"]
            if item["category_id"] == 19
        ]

        self.assertEqual(category_19["decision"], "no_hit")
        self.assertIn("禁用", category_19["judge_reason"])
        self.assertTrue(
            any(
                item["priority_rule_applied"] == "boundary_gate_category_19"
                for item in category_19_audits
            )
        )
        self.assertFalse(
            any(
                item["priority_rule_applied"] == "boundary_evidence_category_19"
                for item in category_19_audits
            )
        )

    def test_unrelated_content_reroutes_original_categories_5_and_6_to_3(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        set_decision(payload, 6, "hit")
        set_fact(payload, "unrelated_content_dominates", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [3])
        self.assert_decision(finalized, 5, "no_hit")
        self.assert_decision(finalized, 6, "no_hit")
        self.assertEqual(
            finalized["policy_checks"]["exclusive_priority_applied"],
            ["priority_3_over_5_for_unrelated_content", "priority_3_over_6"],
        )
        self.assertIn(
            "priority_3_over_5_for_unrelated_content",
            category_result(finalized, 5)["priority_rule_applied"],
        )
        self.assertIn(
            "priority_3_over_6",
            category_result(finalized, 6)["priority_rule_applied"],
        )

    def test_existing_category_3_target_preserves_fields_across_two_reroutes(self):
        payload = valid_payload()
        set_decision(payload, 3, "hit")
        set_decision(payload, 5, "hit")
        set_decision(payload, 6, "hit")
        original_evidence = [
            {
                "source": "Comment Interaction",
                "quote_or_visual_detail": "Original category 3 evidence.",
                "reason": "Original category 3 rationale.",
            }
        ]
        customize_hit(
            payload,
            3,
            original_evidence,
            "Keep the original category 3 reason.",
            "low",
        )
        set_fact(payload, "unrelated_content_dominates", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_3 = category_result(finalized, 3)
        target_audits = [
            item
            for item in finalized["boundary_overrides"]
            if item["category_id"] == 3
            and item["priority_rule_applied"]
            in {
                "priority_3_over_5_for_unrelated_content",
                "priority_3_over_6",
            }
        ]

        self.assertEqual(category_3["evidence"], original_evidence)
        self.assertEqual(category_3["judge_reason"], "Keep the original category 3 reason.")
        self.assertEqual(category_3["confidence"], "low")
        self.assertEqual(
            category_3["priority_rule_applied"],
            ["priority_3_over_5_for_unrelated_content", "priority_3_over_6"],
        )
        self.assertEqual(
            {item["priority_rule_applied"] for item in target_audits},
            {"priority_3_over_5_for_unrelated_content", "priority_3_over_6"},
        )
        self.assertTrue(
            all(item["from_decision"] == item["to_decision"] == "hit" for item in target_audits)
        )

    def test_no_physical_display_reroutes_original_category_6_to_5(self):
        payload = valid_payload()
        set_decision(payload, 6, "hit")
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [5])
        self.assert_decision(finalized, 6, "no_hit")
        self.assertIn(
            "priority_5_over_6_for_no_physical_display",
            category_result(finalized, 6)["priority_rule_applied"],
        )

    def test_existing_category_5_target_preserves_fields_and_audits_priority_associations(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        set_decision(payload, 6, "hit")
        original_evidence = [
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "Only a static product card is visible.",
                "reason": "Original category 5 evidence.",
            }
        ]
        customize_hit(
            payload,
            5,
            original_evidence,
            "Keep the original category 5 reason.",
            "medium",
        )
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_5 = category_result(finalized, 5)
        category_6 = category_result(finalized, 6)
        rule = "priority_5_over_6_for_no_physical_display"
        priority_audits = [
            item
            for item in finalized["boundary_overrides"]
            if item["priority_rule_applied"] == rule
        ]

        self.assertEqual(category_5["evidence"], original_evidence)
        self.assertEqual(category_5["judge_reason"], "Keep the original category 5 reason.")
        self.assertEqual(category_5["confidence"], "medium")
        self.assertIn(rule, category_5["priority_rule_applied"])
        self.assertIn(rule, category_6["priority_rule_applied"])
        self.assertEqual({item["category_id"] for item in priority_audits}, {5, 6})
        target_audit = next(item for item in priority_audits if item["category_id"] == 5)
        source_audit = next(item for item in priority_audits if item["category_id"] == 6)
        self.assertEqual(
            (target_audit["from_decision"], target_audit["to_decision"]),
            ("hit", "hit"),
        )
        self.assertEqual(
            (source_audit["from_decision"], source_audit["to_decision"]),
            ("hit", "no_hit"),
        )

    def test_existing_reroute_target_repairs_unauthorized_evidence_before_priority(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        set_decision(payload, 6, "hit")
        customize_hit(
            payload,
            5,
            [
                {
                    "source": "Comment Interaction",
                    "quote_or_visual_detail": "Forbidden category 5 source.",
                    "reason": "Must not survive canonicalization.",
                }
            ],
            "Original category 5 reason.",
            "medium",
        )
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_5 = category_result(finalized, 5)

        self.assertEqual(category_5["decision"], "hit")
        self.assertEqual(
            [item["source"] for item in category_5["evidence"]],
            ["Segment #1 ASR"],
        )
        self.assertEqual(category_5["materials_used"], ["segment_asr"])
        self.assertFalse(category_5["product_image_used"])
        self.assertTrue(
            any(
                item["category_id"] == 5
                and item["from_decision"] == item["to_decision"] == "hit"
                and item["priority_rule_applied"] == "boundary_evidence_repair_category_5"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_demoted_reroute_source_keeps_gate_fields_and_gets_priority_audit(self):
        payload = valid_payload()
        set_decision(payload, 6, "hit")
        customize_hit(
            payload,
            6,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Original category 6 evidence.",
                    "reason": "Original category 6 rationale.",
                }
            ],
            "Original category 6 reason.",
            "low",
        )
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_6 = category_result(finalized, 6)
        rule = "priority_5_over_6_for_no_physical_display"
        category_6_audits = [
            item
            for item in finalized["boundary_overrides"]
            if item["category_id"] == 6
        ]

        self.assertEqual(category_6["decision"], "no_hit")
        self.assertEqual(category_6["evidence"], [])
        self.assertIn("优先级规则", category_6["judge_reason"])
        self.assertEqual(category_6["confidence"], "low")
        self.assertIn(rule, category_6["priority_rule_applied"])
        self.assertTrue(
            any(
                item["from_decision"] == "hit"
                and item["to_decision"] == "no_hit"
                and item["priority_rule_applied"] == rule
                for item in category_6_audits
            )
        )

    def test_full_ipp_facts_reroute_original_category_8_to_15(self):
        payload = valid_payload()
        set_decision(payload, 8, "hit")
        customize_hit(
            payload,
            8,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Language evidence sharing the IPP source.",
                    "reason": "Shared source triggers reroute.",
                }
            ],
            "Original category 8 hit.",
            "medium",
        )
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 ASR")
        set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [15])
        self.assert_decision(finalized, 8, "no_hit")
        self.assertIn(
            "priority_15_over_8_for_product_mismatch",
            category_result(finalized, 8)["priority_rule_applied"],
        )

    def test_independent_category_8_and_15_evidence_can_coexist(self):
        payload = valid_payload()
        set_decision(payload, 8, "hit")
        customize_hit(
            payload,
            8,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Independent language violation.",
                    "reason": "Category 8 language evidence.",
                }
            ],
            "Independent category 8 hit.",
            "medium",
        )
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 frame")
        set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [8, 15])
        self.assertNotIn(
            "priority_15_over_8_for_product_mismatch",
            category_result(finalized, 8)["priority_rule_applied"],
        )

    def test_disjoint_category_5_does_not_escape_its_own_gate_for_category_3(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        customize_hit(
            payload,
            5,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Independent category 5 model evidence.",
                    "reason": "Does not overlap category 3 frame evidence.",
                }
            ],
            "Original category 5 hit without the required promotion fact.",
            "medium",
        )
        set_fact(payload, "unrelated_content_dominates", source="Segment #1 frame")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [3])
        self.assert_decision(finalized, 5, "no_hit")

    def test_same_source_category_8_and_15_evidence_reroutes_to_15(self):
        payload = valid_payload()
        set_decision(payload, 8, "hit")
        customize_hit(
            payload,
            8,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Language evidence overlaps IPP evidence.",
                    "reason": "Shared evidence source.",
                }
            ],
            "Original category 8 hit.",
            "medium",
        )
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 ASR")
        set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [15])
        self.assert_decision(finalized, 8, "no_hit")

    def test_sexual_fact_reroutes_original_category_19_to_1(self):
        payload = valid_payload()
        set_decision(payload, 19, "hit")
        set_fact(payload, "sexualized_exposure_or_behavior_found")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [1])
        self.assert_decision(finalized, 19, "no_hit")
        self.assertIn(
            "priority_1_over_19",
            category_result(finalized, 19)["priority_rule_applied"],
        )

    def test_complete_category_12_facts_promote_original_no_hit_with_evidence(self):
        payload = valid_payload()
        set_fact(payload, "concrete_live_effect_claim_found", source="Segment #1 ASR")
        set_fact(payload, "materially_misleading_basis_found", source="Pearl product #1 image")
        set_fact(
            payload,
            "effect_claim_prevalence_or_strength_threshold_met",
            source="Pearl product #1 title",
        )

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_12 = category_result(finalized, 12)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(category_12["decision"], "hit")
        self.assertEqual(category_12["evidence_count"], 3)
        self.assertEqual(
            category_12["materials_used"],
            ["pearl_product_image", "pearl_product_title", "segment_asr"],
        )
        self.assertTrue(category_12["product_image_used"])
        self.assertEqual(category_12["confidence"], "medium")
        self.assertTrue(
            all(
                set(item) == {"source", "quote_or_visual_detail", "reason"}
                for item in category_12["evidence"]
            )
        )

    def test_mutation_normalizes_malformed_confidence_values_to_medium(self):
        malformed_values = ([], {}, 1, True, None, "", "unexpected")

        for malformed_confidence in malformed_values:
            with self.subTest(malformed_confidence=malformed_confidence):
                payload = valid_payload()
                category_result(payload, 12)["confidence"] = malformed_confidence
                set_complete_category_12_facts(payload)

                try:
                    result = finalize_judge_output(build_params(payload))
                except Exception as exc:
                    self.fail("finalizer raised for malformed confidence: " + str(exc))
                finalized = finalized_payload(result)

                self.assert_decision(finalized, 12, "hit")
                self.assertEqual(category_result(finalized, 12)["confidence"], "medium")

    def test_mutation_preserves_valid_confidence_values(self):
        for confidence in ("high", "medium", "low"):
            with self.subTest(confidence=confidence):
                payload = valid_payload()
                category_result(payload, 12)["confidence"] = confidence
                set_complete_category_12_facts(payload)

                finalized = finalized_payload(finalize_judge_output(build_params(payload)))

                self.assert_decision(finalized, 12, "hit")
                self.assertEqual(category_result(finalized, 12)["confidence"], confidence)

    def test_category_15_non_ipp_fact_preserves_original_hit(self):
        payload = valid_payload()
        set_decision(payload, 15, "hit")
        customize_hit(
            payload,
            15,
            [
                {
                    "source": "Segment #1 frame",
                    "quote_or_visual_detail": "First illegal-product evidence unit.",
                    "reason": "Independent non-IPP basis.",
                },
                {
                    "source": "Pearl product #1 title",
                    "quote_or_visual_detail": "Second illegal-product evidence unit.",
                    "reason": "Independent non-IPP basis.",
                },
            ],
            "Original category 15 hit.",
            "medium",
        )
        set_fact_sources(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            ("Pearl product #1 title", "Segment #1 ASR"),
        )

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)

        self.assertEqual(result["finalization_status"], "pass")
        self.assert_decision(finalized, 15, "hit")
        self.assertEqual(finalized["boundary_overrides"], [])

    def test_category_15_alternative_one_unit_cannot_promote(self):
        payload = valid_payload()
        set_fact(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            source="Pearl product #1 title",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 15, "no_hit")

    def test_category_15_alternative_one_unit_cannot_preserve_existing_hit(self):
        payload = valid_payload()
        set_decision(payload, 15, "hit")
        customize_hit(
            payload,
            15,
            [
                {
                    "source": "Segment #1 frame",
                    "quote_or_visual_detail": "First model evidence unit.",
                    "reason": "Original model evidence.",
                },
                {
                    "source": "Pearl product #1 image",
                    "quote_or_visual_detail": "Second model evidence unit.",
                    "reason": "Original model evidence.",
                },
            ],
            "Original category 15 hit.",
            "medium",
        )
        set_fact(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            source="Pearl product #1 title",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 15, "no_hit")

    def test_category_15_alternative_two_distinct_units_promote(self):
        payload = valid_payload()
        set_fact_sources(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            ("Pearl product #1 title", "Segment #1 ASR"),
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_15 = category_result(finalized, 15)

        self.assertEqual(category_15["decision"], "hit")
        self.assertEqual(category_15["evidence_count"], 2)

    def test_category_15_full_ipp_path_wins_when_alternative_has_one_unit(self):
        payload = valid_payload()
        set_fact(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            source="Pearl product #1 title",
        )
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 frame")
        set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_15 = category_result(finalized, 15)

        self.assertEqual(category_15["decision"], "hit")
        self.assertEqual(category_15["evidence_count"], 3)
        self.assertNotIn(
            "Pearl product #1 title",
            [item["source"] for item in category_15["evidence"]],
        )

    def test_category_15_rejects_asr_as_bound_product_evidence(self):
        payload = valid_payload()
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 frame")
        set_fact(payload, "bound_product_evidence_found", source="Segment #1 ASR")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 15, "no_hit")

    def test_unpublished_pearl_identities_cannot_promote_category_15(self):
        payload = valid_payload()
        set_fact_sources(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            ("Pearl product #999 title", "Pearl product #999 image"),
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 15, "no_hit")

    def test_category_15_same_source_with_different_details_counts_as_one_unit(self):
        payload = valid_payload()
        set_decision(payload, 15, "hit")
        original_evidence = [
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "First model detail.",
                "reason": "Original model evidence.",
            },
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "Second model detail.",
                "reason": "Original model evidence.",
            },
        ]
        customize_hit(
            payload,
            15,
            original_evidence,
            "Original category 15 hit.",
            "medium",
        )
        set_fact(payload, "live_promoted_item_evidence_found", source="Segment #1 frame")
        set_fact(payload, "bound_product_evidence_found", source="Pearl product #1 image")
        set_fact(payload, "core_product_contradiction_found", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_15 = category_result(finalized, 15)

        self.assertEqual(category_15["decision"], "hit")
        self.assertNotEqual(category_15["evidence"], original_evidence)
        self.assertEqual(category_15["evidence_count"], 3)
        self.assertTrue(
            any(
                item["category_id"] == 15
                and item["priority_rule_applied"] == "boundary_evidence_repair_category_15"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_non_ipp_category_15_fact_does_not_reroute_category_8(self):
        payload = valid_payload()
        set_decision(payload, 8, "hit")
        customize_hit(
            payload,
            8,
            [
                {
                    "source": "Segment #1 ASR",
                    "quote_or_visual_detail": "Valid category 8 language evidence.",
                    "reason": "Keep category 8 independent from non-IPP category 15.",
                }
            ],
            "Original category 8 hit.",
            "medium",
        )
        set_fact_sources(
            payload,
            "category_15_non_ipp_illegal_basis_found",
            ("Pearl product #1 title", "Segment #1 ASR"),
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [8, 15])
        self.assert_decision(finalized, 8, "hit")
        self.assertNotIn(
            "priority_15_over_8_for_product_mismatch",
            category_result(finalized, 8)["priority_rule_applied"],
        )

    def test_category_18_same_evidence_unit_cannot_promote(self):
        payload = valid_payload()
        shared_detail = "The same hostile statement."
        set_fact(
            payload,
            "sustained_negative_emotion_found",
            source="Segment #1 ASR",
            detail=shared_detail,
        )
        set_fact(
            payload,
            "hostile_shaming_fear_evidence_found",
            source="Segment #1 ASR",
            detail=shared_detail,
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 18, "no_hit")

    def test_category_18_same_source_with_different_details_is_one_unit(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sustained_negative_emotion_found",
            source="Segment #1 ASR",
            detail="First model-authored detail.",
        )
        set_fact(
            payload,
            "hostile_shaming_fear_evidence_found",
            source="Segment #1 ASR",
            detail="Second model-authored detail.",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 18, "no_hit")

    def test_category_18_two_distinct_evidence_units_promote(self):
        payload = valid_payload()
        set_fact(
            payload,
            "sustained_negative_emotion_found",
            source="Segment #1 ASR",
            detail="Sustained negative emotion across the room.",
        )
        set_fact(
            payload,
            "hostile_shaming_fear_evidence_found",
            source="Comment Interaction",
            detail="A distinct hostile viewer interaction.",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_18 = category_result(finalized, 18)

        self.assertEqual(category_18["decision"], "hit")
        self.assertEqual(category_18["evidence_count"], 2)

    def test_two_unit_categories_demote_existing_one_unit_hits(self):
        for category_id in (13, 16, 17):
            with self.subTest(category_id=category_id):
                payload = valid_payload()
                set_decision(payload, category_id, "hit")

                finalized = finalized_payload(finalize_judge_output(build_params(payload)))

                self.assert_decision(finalized, category_id, "no_hit")

    def test_two_unit_categories_preserve_existing_two_unit_hits(self):
        for category_id in (13, 16, 17):
            with self.subTest(category_id=category_id):
                payload = valid_payload()
                set_decision(payload, category_id, "hit")
                customize_hit(
                    payload,
                    category_id,
                    [
                        {
                            "source": "Segment #1 frame",
                            "quote_or_visual_detail": "First evidence unit.",
                            "reason": "Threshold evidence.",
                        },
                        {
                            "source": "Segment #1 ASR",
                            "quote_or_visual_detail": "Second evidence unit.",
                            "reason": "Threshold evidence.",
                        },
                    ],
                    "Original threshold-qualified hit.",
                    "medium",
                )

                finalized = finalized_payload(finalize_judge_output(build_params(payload)))

                self.assert_decision(finalized, category_id, "hit")

    def test_category_9_positive_facts_only_promote_category_9(self):
        payload = valid_payload()
        set_fact(
            payload,
            "explicit_generated_content_evidence_found",
            source="Segment #1 frame",
        )
        set_fact(
            payload,
            "authenticity_misleading_found",
            source="Segment #1 ASR",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [9])

    def test_category_10_positive_facts_only_promote_category_10(self):
        payload = valid_payload()
        set_fact(
            payload,
            "explicit_generated_content_evidence_found",
            source="Segment #1 frame",
        )
        set_fact(
            payload,
            "generated_product_material_mismatch_found",
            source="Segment #1 ASR",
        )
        set_fact(
            payload,
            "bound_product_evidence_found",
            source="Pearl product #1 image",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["hit_category_ids"], [10])

    def test_category_10_pearl_only_generated_evidence_cannot_hit(self):
        payload = valid_payload()
        set_fact(
            payload,
            "explicit_generated_content_evidence_found",
            source="Pearl product #1 image",
        )
        set_fact(
            payload,
            "generated_product_material_mismatch_found",
            source="Pearl product #1 title",
        )
        set_fact(
            payload,
            "bound_product_evidence_found",
            source="Pearl product #1 image",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 10, "no_hit")

    def test_category_10_requires_two_distinct_trusted_sources(self):
        payload = valid_payload()
        set_fact(
            payload,
            "explicit_generated_content_evidence_found",
            source="Segment #1 frame",
        )
        set_fact(
            payload,
            "generated_product_material_mismatch_found",
            source="Segment #1 frame",
        )
        set_fact(
            payload,
            "bound_product_evidence_found",
            source="Pearl product #1 image",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_10 = category_result(finalized, 10)

        self.assertEqual(category_10["decision"], "hit")
        self.assertEqual(category_10["evidence_count"], 2)

    def test_unable_to_judge_category_2_is_preserved_without_required_facts(self):
        payload = valid_payload()
        set_decision(payload, 2, "unable_to_judge")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 2, "unable_to_judge")
        self.assertIn(2, finalized["unable_to_judge_category_ids"])

    def test_ungated_results_are_canonicalized_and_non_hits_clear_hit_fields(self):
        payload = valid_payload()
        category_4 = category_result(payload, 4)
        category_4["confidence"] = "unexpected"
        category_4["priority_rule_applied"] = ["", "existing_rule", "existing_rule"]
        category_4["evidence"] = [
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "Stale no-hit evidence.",
                "reason": "Must be cleared.",
            }
        ]
        category_4["evidence_count"] = 1
        category_4["materials_used"] = ["segment_frame"]
        category_4["product_image_used"] = True
        set_decision(payload, 8, "unable_to_judge")
        category_8 = category_result(payload, 8)
        category_8["evidence"] = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "Stale unable evidence.",
                "reason": "Must be cleared.",
            }
        ]
        category_8["evidence_count"] = 1
        category_8["materials_used"] = ["segment_asr"]
        category_8["product_image_used"] = True

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        for category_id in (4, 8):
            item = category_result(finalized, category_id)
            self.assertEqual(item["evidence"], [])
            self.assertEqual(item["evidence_count"], 0)
            self.assertEqual(item["materials_used"], [])
            self.assertFalse(item["product_image_used"])
        self.assertEqual(category_result(finalized, 4)["confidence"], "medium")
        category_4_rules = category_result(finalized, 4)["priority_rule_applied"]
        self.assertIn("existing_rule", category_4_rules)
        self.assertIn("boundary_confidence_normalization_category_4", category_4_rules)
        self.assertIn("boundary_non_hit_cleanup_category_4", category_4_rules)

    def test_category_7_product_image_evidence_cannot_preserve_hit_even_with_false_flag(self):
        payload = valid_payload()
        set_decision(payload, 7, "hit")
        customize_hit(
            payload,
            7,
            [
                {
                    "source": "Pearl product #1 image",
                    "quote_or_visual_detail": "Product image only.",
                    "reason": "Category 7 forbids product evidence.",
                }
            ],
            "Original category 7 hit.",
            "medium",
        )
        category_result(payload, 7)["product_image_used"] = False

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_7 = category_result(finalized, 7)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(category_7["decision"], "no_hit")
        self.assertEqual(category_7["evidence"], [])
        self.assertFalse(category_7["product_image_used"])

    def test_category_7_valid_frame_evidence_derives_material_flags(self):
        payload = valid_payload()
        set_decision(payload, 7, "hit")
        category_7 = category_result(payload, 7)
        category_7["materials_used"] = ["pearl_product_image"]
        category_7["product_image_used"] = True

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_7 = category_result(finalized, 7)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(category_7["decision"], "hit")
        self.assertEqual(category_7["materials_used"], ["segment_frame"])
        self.assertFalse(category_7["product_image_used"])
        self.assertTrue(
            any(
                item["category_id"] == 7
                and item["priority_rule_applied"]
                == "boundary_evidence_metadata_repair_category_7"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_category_7_filters_forbidden_evidence_when_valid_frame_remains(self):
        payload = valid_payload()
        set_decision(payload, 7, "hit")
        category_7 = category_result(payload, 7)
        category_7["evidence"].append(
            {
                "source": "Pearl product #1 image",
                "quote_or_visual_detail": "Forbidden extra evidence.",
                "reason": "Must be filtered.",
            }
        )
        category_7["evidence_count"] = 2

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_7 = category_result(finalized, 7)

        self.assertEqual(category_7["decision"], "hit")
        self.assertEqual(len(category_7["evidence"]), 1)
        self.assertEqual(category_7["evidence"][0]["source"], "Segment #1 frame")

    def test_visible_text_evidence_uses_segment_frame_availability(self):
        payload = valid_payload()
        set_decision(payload, 8, "hit")
        customize_hit(
            payload,
            8,
            [
                {
                    "source": "Segment #1 visible text",
                    "quote_or_visual_detail": "Unreadable non-target language text.",
                    "reason": "Visible-text language evidence.",
                }
            ],
            "Original category 8 hit.",
            "medium",
        )

        finalized = finalized_payload(
            finalize_judge_output(
                build_params_with_availability(payload, segment_frame=False)
            )
        )

        self.assert_decision(finalized, 8, "no_hit")

    def test_existing_hit_with_non_list_evidence_fails_closed(self):
        payload = valid_payload()
        set_decision(payload, 7, "hit")
        category_result(payload, 7)["evidence"] = None

        self.assert_payload_failure_no_raise(payload, "final_result_evidence_not_list:7")

    def test_reroute_target_with_non_list_evidence_fails_closed(self):
        payload = valid_payload()
        set_decision(payload, 5, "hit")
        set_decision(payload, 6, "hit")
        category_result(payload, 5)["evidence"] = None
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")

        self.assert_payload_failure_no_raise(payload, "final_result_evidence_not_list:5")

    def test_unsupported_keyword_like_sources_cannot_promote_a_category(self):
        payload = valid_payload()
        set_fact(
            payload,
            "disturbing_visual_dominates",
            source="keyword-only detector",
            detail="disturbing horror keyword",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 2, "no_hit")
        self.assertEqual(finalized["boundary_overrides"], [])

    def test_product_image_only_concrete_claim_cannot_promote_category_12(self):
        payload = valid_payload()
        set_fact(
            payload,
            "concrete_live_effect_claim_found",
            source="Pearl product #1 image",
        )
        set_fact(payload, "materially_misleading_basis_found", source="Pearl product #1 image")
        set_fact(
            payload,
            "effect_claim_prevalence_or_strength_threshold_met",
            source="Pearl product #1 title",
        )

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assert_decision(finalized, 12, "no_hit")
        self.assertEqual(finalized["boundary_overrides"], [])

    def test_existing_category_12_hit_with_product_only_live_claim_is_demoted(self):
        payload = valid_payload()
        set_decision(payload, 12, "hit")
        set_fact(
            payload,
            "concrete_live_effect_claim_found",
            source="Pearl product #1 image",
        )
        set_fact(payload, "materially_misleading_basis_found", source="Pearl product #1 image")
        set_fact(
            payload,
            "effect_claim_prevalence_or_strength_threshold_met",
            source="Pearl product #1 title",
        )

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_12 = category_result(finalized, 12)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(category_12["decision"], "no_hit")
        self.assertEqual(category_12["evidence"], [])
        self.assertIn("允许材料证据", category_12["judge_reason"])
        self.assertEqual(category_12["confidence"], "medium")

    def test_existing_category_12_hit_with_valid_gate_evidence_preserves_original_fields(self):
        payload = valid_payload()
        set_decision(payload, 12, "hit")
        original_evidence = [
            {
                "source": "Segment #1 ASR",
                "quote_or_visual_detail": "Original live claim quote.",
                "reason": "Original model threshold analysis.",
            }
        ]
        customize_hit(
            payload,
            12,
            original_evidence,
            "Keep the original category 12 reason.",
            "low",
        )
        set_fact(payload, "concrete_live_effect_claim_found", source="Segment #1 ASR")
        set_fact(payload, "materially_misleading_basis_found", source="Pearl product #1 image")
        set_fact(
            payload,
            "effect_claim_prevalence_or_strength_threshold_met",
            source="Pearl product #1 title",
        )

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_12 = category_result(finalized, 12)

        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(category_12["decision"], "hit")
        self.assertEqual(category_12["evidence"], original_evidence)
        self.assertEqual(category_12["judge_reason"], "Keep the original category 12 reason.")
        self.assertEqual(category_12["confidence"], "low")
        self.assertEqual(finalized["boundary_overrides"], [])

    def test_final_payload_lists_report_and_override_log_are_synchronized(self):
        payload = valid_payload()
        set_fact(payload, "sexualized_exposure_or_behavior_found")

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        report, serialized = result["finalized_judge_output"].split("\n\nFINAL_JSON:\n", 1)

        self.assertEqual(json.loads(serialized), finalized)
        self.assertEqual(finalized["hit_category_ids"], [1])
        self.assertEqual(finalized["no_hit_category_ids"], list(range(2, 20)))
        self.assertEqual(finalized["unable_to_judge_category_ids"], [])
        self.assertIn("识别到的低质问题：", report)
        self.assertIn("识别到【色情低俗低质问题】", report)
        self.assertIn("无低质问题：", report)
        self.assertIn("无法判断：", report)
        self.assertEqual(
            json.loads(result["boundary_override_log"]),
            finalized["boundary_overrides"],
        )
        self.assertEqual(json.loads(result["finalizer_errors"]), [])

    def test_top_level_coverage_and_policy_checks_are_rebuilt_unconditionally(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                payload = valid_payload()
                if missing:
                    del payload["coverage_check"]
                    del payload["policy_checks"]
                else:
                    payload["coverage_check"] = None
                    payload["policy_checks"] = None

                finalized = finalized_payload(finalize_judge_output(build_params(payload)))

                self.assertEqual(
                    finalized["coverage_check"],
                    {
                        "expected_category_count": 19,
                        "actual_category_count": 19,
                        "missing_category_ids": [],
                        "extra_category_ids": [],
                        "hit_no_hit_overlap_category_ids": [],
                    },
                )
                self.assertEqual(
                    finalized["policy_checks"],
                    {
                        "product_image_permission_violations": [],
                        "exclusive_priority_applied": [],
                        "threshold_recheck_warnings": [],
                    },
                )

    def test_stale_policy_lists_are_rebuilt_and_valid_threshold_warnings_preserved(self):
        payload = valid_payload()
        payload["coverage_check"] = {
            "expected_category_count": 99,
            "actual_category_count": 0,
            "missing_category_ids": [1],
            "extra_category_ids": [99],
            "hit_no_hit_overlap_category_ids": [1],
        }
        payload["policy_checks"] = {
            "product_image_permission_violations": [7],
            "exclusive_priority_applied": ["stale_priority"],
            "threshold_recheck_warnings": ["keep_warning"],
        }

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))

        self.assertEqual(finalized["coverage_check"]["actual_category_count"], 19)
        self.assertEqual(finalized["coverage_check"]["missing_category_ids"], [])
        self.assertEqual(finalized["coverage_check"]["extra_category_ids"], [])
        self.assertEqual(
            finalized["coverage_check"]["hit_no_hit_overlap_category_ids"],
            [],
        )
        self.assertEqual(
            finalized["policy_checks"],
            {
                "product_image_permission_violations": [],
                "exclusive_priority_applied": [],
                "threshold_recheck_warnings": ["keep_warning"],
            },
        )

        payload = valid_payload()
        payload["policy_checks"]["threshold_recheck_warnings"] = [1]
        self.assert_payload_failure_no_raise(
            payload,
            "threshold_recheck_warnings_invalid",
        )

    def test_nonempty_threshold_warnings_force_warning_status_and_audit(self):
        payload = valid_payload()
        payload["policy_checks"]["threshold_recheck_warnings"] = ["manual_recheck"]

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(
            finalized["policy_checks"]["threshold_recheck_warnings"],
            ["manual_recheck"],
        )
        self.assertTrue(
            any(
                item["priority_rule_applied"] == "threshold_recheck_warning"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_material_summary_is_rebuilt_from_trusted_inputs_and_audited(self):
        payload = valid_payload()
        payload["material_summary"] = None
        params = build_params_with_trusted_materials(
            payload,
            segments=[{"segment_index": 1, "asr_summary": "ASR", "frame_urls": []}],
            segment_count=1,
            comment_interaction="",
            products=[],
            product_count=0,
            warnings=["segment_frame_missing"],
        )

        result = finalize_judge_output(params)
        finalized = finalized_payload(result)

        self.assertEqual(result["finalization_status"], "warning")
        self.assertEqual(
            finalized["material_summary"],
            {
                "segment_count": 1,
                "product_count": 0,
                "comment_interaction_available": False,
                "material_quality_warning": ["segment_frame_missing"],
            },
        )
        self.assertTrue(
            any(
                item["priority_rule_applied"] == "material_summary_repair"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_all_missing_materials_make_categories_1_to_18_unable(self):
        payload = valid_payload()
        params = build_params_with_trusted_materials(
            payload,
            segments=[],
            segment_count=0,
            comment_interaction="",
            products=[],
            product_count=0,
        )

        finalized = finalized_payload(finalize_judge_output(params))

        self.assertEqual(finalized["unable_to_judge_category_ids"], list(range(1, 19)))
        self.assertEqual(category_result(finalized, 19)["decision"], "no_hit")

    def test_required_channel_groups_control_category_applicability(self):
        cases = (
            (
                5,
                [{"segment_index": 1, "asr_summary": "ASR", "frame_urls": []}],
                [],
            ),
            (
                7,
                [{"segment_index": 1, "asr_summary": "ASR", "frame_urls": []}],
                [],
            ),
            (
                10,
                [{"segment_index": 1, "asr_summary": "ASR", "frame_urls": ["frame"]}],
                [],
            ),
            (
                12,
                [],
                [{"product_index": 1, "title": "Product", "image_urls": ["image"]}],
            ),
        )

        for category_id, segments, products in cases:
            with self.subTest(category_id=category_id):
                payload = valid_payload()
                params = build_params_with_trusted_materials(
                    payload,
                    segments=segments,
                    segment_count=len(segments),
                    comment_interaction="",
                    products=products,
                    product_count=len(products),
                )

                finalized = finalized_payload(finalize_judge_output(params))

                self.assert_decision(finalized, category_id, "unable_to_judge")

    def test_category_3_is_applicable_with_reliable_live_material_only(self):
        payload = valid_payload()
        segments = [{"segment_index": 1, "asr_summary": "Live content", "frame_urls": []}]
        params = build_params_with_trusted_materials(
            payload,
            segments=segments,
            segment_count=1,
            comment_interaction="",
            products=[],
            product_count=0,
        )

        finalized = finalized_payload(finalize_judge_output(params))

        self.assert_decision(finalized, 3, "no_hit")

    def test_category_5_asr_promotion_without_frames_is_unable_not_hit(self):
        payload = valid_payload()
        set_fact(payload, "sustained_product_promotion_found", source="Segment #1 ASR")
        segments = [{"segment_index": 1, "asr_summary": "Promotion", "frame_urls": []}]
        params = build_params_with_trusted_materials(
            payload,
            segments=segments,
            segment_count=1,
            comment_interaction="",
            products=[{"product_index": 1, "title": "Product", "image_urls": []}],
            product_count=1,
        )

        finalized = finalized_payload(finalize_judge_output(params))

        self.assert_decision(finalized, 5, "unable_to_judge")

    def test_count_mismatch_marks_applicability_unreliable_and_warns(self):
        payload = valid_payload()
        segments = [
            {"segment_index": 1, "asr_summary": "ASR", "frame_urls": ["frame"]}
        ]
        params = build_params_with_trusted_materials(
            payload,
            segments=segments,
            segment_count=2,
            comment_interaction="",
            products=[],
            product_count=0,
            warnings=["segment_count_mismatch"],
        )

        result = finalize_judge_output(params)
        finalized = finalized_payload(result)

        self.assertEqual(result["finalization_status"], "warning")
        self.assert_decision(finalized, 1, "unable_to_judge")
        self.assertEqual(finalized["material_summary"]["segment_count"], 1)
        self.assertTrue(
            any(
                item["priority_rule_applied"] == "material_reliability_warning"
                for item in finalized["boundary_overrides"]
            )
        )

    def test_forbidden_only_evidence_keeps_no_hit_over_unable(self):
        payload = valid_payload()
        category_7 = category_result(payload, 7)
        category_7["evidence"] = [
            {
                "source": "Pearl product #1 image",
                "quote_or_visual_detail": "Forbidden category 7 evidence.",
                "reason": "Must preserve no_hit precedence.",
            }
        ]
        category_7["evidence_count"] = 1
        category_7["materials_used"] = ["pearl_product_image"]
        params = build_params_with_trusted_materials(
            payload,
            segments=[],
            segment_count=0,
            comment_interaction="",
            products=[{"product_index": 1, "title": "Product", "image_urls": ["image"]}],
            product_count=1,
        )

        finalized = finalized_payload(finalize_judge_output(params))

        self.assert_decision(finalized, 7, "no_hit")

    def test_product_image_permission_fields_are_recomputed_from_final_evidence(self):
        payload = valid_payload()
        set_decision(payload, 3, "hit")
        customize_hit(
            payload,
            3,
            [
                {
                    "source": "Pearl product #1 image",
                    "quote_or_visual_detail": "Valid category 3 product comparison.",
                    "reason": "Product evidence is permitted for category 3.",
                }
            ],
            "Original category 3 hit.",
            "medium",
        )
        category_result(payload, 3)["product_image_permission_ok"] = False
        set_fact(payload, "unrelated_content_dominates", source="Segment #1 ASR")

        finalized = finalized_payload(finalize_judge_output(build_params(payload)))
        category_3 = category_result(finalized, 3)

        self.assertTrue(category_3["product_image_used"])
        self.assertTrue(category_3["product_image_permission_ok"])
        self.assertEqual(
            finalized["policy_checks"]["product_image_permission_violations"],
            [],
        )

    def test_confidence_and_stale_non_hit_repairs_are_audited(self):
        payload = valid_payload()
        category_4 = category_result(payload, 4)
        category_4["confidence"] = "unexpected"
        category_4["evidence"] = [
            {
                "source": "Segment #1 frame",
                "quote_or_visual_detail": "Stale no-hit evidence.",
                "reason": "Must be removed with audit.",
            }
        ]
        category_4["evidence_count"] = 1
        category_4["materials_used"] = ["segment_frame"]

        result = finalize_judge_output(build_params(payload))
        finalized = finalized_payload(result)
        category_4_rules = {
            item["priority_rule_applied"]
            for item in finalized["boundary_overrides"]
            if item["category_id"] == 4
        }

        self.assertEqual(result["finalization_status"], "warning")
        self.assertIn("boundary_confidence_normalization_category_4", category_4_rules)
        self.assertIn("boundary_non_hit_cleanup_category_4", category_4_rules)

    def test_fully_valid_payload_passes_without_business_overrides(self):
        payload = valid_payload()
        expected_payload = copy.deepcopy(payload)
        expected_payload["boundary_overrides"] = []

        result = finalize_judge_output(build_params(payload))

        self.assertEqual(set(result), EXPECTED_RETURN_KEYS)
        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(json.loads(result["finalizer_errors"]), [])
        self.assertEqual(json.loads(result["boundary_override_log"]), [])
        self.assertEqual(json.loads(result["finalized_final_json"]), expected_payload)
        self.assertTrue(result["finalized_judge_output"].startswith("识别到的低质问题：\n"))
        self.assertEqual(
            json.loads(result["finalized_judge_output"].split("\n\nFINAL_JSON:\n", 1)[1]),
            expected_payload,
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
        expected_payload = copy.deepcopy(payload)
        expected_payload["boundary_overrides"] = []

        class StubArgs:
            params = build_params(payload)

        result = asyncio.run(main(StubArgs()))

        self.assertEqual(result["finalization_status"], "pass")
        self.assertEqual(json.loads(result["finalized_final_json"]), expected_payload)


if __name__ == "__main__":
    unittest.main()
