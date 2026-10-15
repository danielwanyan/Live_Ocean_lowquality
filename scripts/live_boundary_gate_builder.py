import json


BOUNDARY_CONTRACT_VERSION = "2026-10-15-v3-cross-project-boundary-gates"

REQUIRED_FACTS = [
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

GATE_DEFINITIONS = {
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

REROUTES = [
    {"from": [5], "to": 3, "rule": "priority_3_over_5_for_unrelated_content"},
    {"from": [6], "to": 3, "rule": "priority_3_over_6"},
    {"from": [6], "to": 5, "rule": "priority_5_over_6_for_no_physical_display"},
    {"from": [8], "to": 15, "rule": "priority_15_over_8_for_product_mismatch"},
    {"from": [19], "to": 1, "rule": "priority_1_over_19"},
]

BOUNDARY_GATE_PANEL_LINES = [
    "Boundary facts are LLM observations. The builder only publishes gates and material availability.",
    "Category 1: require sexualized exposure or behavior; block ordinary try-on or public-context-only evidence.",
    "Category 2: require disturbing visuals to dominate; block cleaning demonstrations and novelty or product-art context.",
    "Category 3: require unrelated content to dominate; block when sustained product promotion is found.",
    "Category 4: apply the interaction rule to available ASR and comment evidence; no additional machine fact gate.",
    "Category 5: require sustained product promotion; block real physical display and unrelated-dominant content.",
    "Category 6: require sustained promotion, real physical display, and extremely low information; block core buying information, identifiable purpose, or unrelated-dominant content.",
    "Category 7: require an interruption or layer with 80%+ occlusion of the live screen.",
    "Category 8: apply the language rule only; product mismatch reroutes to Category 15.",
    "Category 9: require explicit generated-content evidence plus authenticity misleading evidence.",
    "Category 10: require explicit generated-content evidence plus generated-product material mismatch.",
    "Category 11: require a concrete replay indicator; weak replay signals alone block the gate.",
    "Category 12: require a concrete live effect claim, a materially misleading basis, and prevalence or strength threshold; block marketing or product-image-only evidence.",
    "Category 13: apply the dangerous-behavior evidence threshold; no additional machine fact gate.",
    "Category 14: require an off-platform destination, explicit transaction guidance, and the same-scene requirement.",
    "Category 15: require live and bound product evidence plus a core contradiction, or a non-IPP illegal basis; block minor variants or background-only differences for the mismatch path.",
    "Category 16: apply the political-sensitivity evidence threshold; no additional machine fact gate.",
    "Category 17: apply the controversial-topic evidence threshold; no additional machine fact gate.",
    "Category 18: require sustained negative emotion plus hostile, shaming, or fear evidence; block routine sales or knowledge marketing only.",
    "Category 19: disabled; sexualized evidence reroutes to Category 1.",
]


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_json_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _has_nonblank_string(value):
    return isinstance(value, str) and bool(value.strip())


def _has_nonempty_list_field(value):
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        try:
            value = json.loads(stripped)
        except Exception:
            return False
    if not isinstance(value, list):
        return False
    return any(_has_nonblank_string(item) for item in value)


def _is_positive_exact_int(value):
    return type(value) is int and value > 0


def _build_allowed_source_labels(params):
    segments = _parse_json_list(params.get("segments_json"))
    products = _parse_json_list(params.get("product_catalog_json"))
    labels = set()

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_index = segment.get("segment_index")
        if not _is_positive_exact_int(segment_index):
            continue
        if _has_nonblank_string(segment.get("asr_summary")):
            labels.add("Segment #%d ASR" % segment_index)
        if _has_nonempty_list_field(segment.get("frame_urls")):
            labels.add("Segment #%d frame" % segment_index)
            labels.add("Segment #%d visible text" % segment_index)

    if _has_nonblank_string(params.get("comment_interaction")):
        labels.add("Comment Interaction")

    for product in products:
        if not isinstance(product, dict):
            continue
        product_index = product.get("product_index")
        if not _is_positive_exact_int(product_index):
            continue
        if _has_nonblank_string(product.get("title")):
            labels.add("Pearl product #%d title" % product_index)
        if _has_nonempty_list_field(product.get("image_urls")):
            labels.add("Pearl product #%d image" % product_index)

    return sorted(labels)


def _build_material_availability(params):
    segments = _parse_json_list(params.get("segments_json"))
    products = _parse_json_list(params.get("product_catalog_json"))

    segment_frame = any(
        isinstance(segment, dict) and _has_nonempty_list_field(segment.get("frame_urls"))
        for segment in segments
    )
    segment_asr = any(
        isinstance(segment, dict) and _has_nonblank_string(segment.get("asr_summary"))
        for segment in segments
    )
    pearl_product_title = any(
        isinstance(product, dict) and _has_nonblank_string(product.get("title"))
        for product in products
    )
    pearl_product_image = any(
        isinstance(product, dict) and _has_nonempty_list_field(product.get("image_urls"))
        for product in products
    )

    return {
        "segment_frame": segment_frame,
        "segment_asr": segment_asr,
        "comment_interaction": _has_nonblank_string(params.get("comment_interaction")),
        "pearl_product_title": pearl_product_title,
        "pearl_product_image": pearl_product_image,
    }


def _build_warnings(material_availability, rules_version):
    warnings = []
    if not material_availability["segment_frame"]:
        warnings.append("segment_frame_missing")
    if not material_availability["segment_asr"]:
        warnings.append("segment_asr_missing")
    if not material_availability["pearl_product_title"] and not material_availability["pearl_product_image"]:
        warnings.append("product_catalog_missing")
    if rules_version != BOUNDARY_CONTRACT_VERSION:
        warnings.append("rules_version_mismatch")
    return warnings


def build_boundary_gate_output(params):
    if not isinstance(params, dict):
        params = {}
    rules_version = _text(params.get("rules_version"))
    material_availability = _build_material_availability(params)
    allowed_source_labels = _build_allowed_source_labels(params)
    warnings = _build_warnings(material_availability, rules_version)

    boundary_gates = {
        "contract_version": BOUNDARY_CONTRACT_VERSION,
        "rules_version": rules_version,
        "material_availability": material_availability,
        "allowed_source_labels": allowed_source_labels,
        "required_facts": REQUIRED_FACTS,
        "gate_definitions": GATE_DEFINITIONS,
        "reroutes": REROUTES,
        "disabled_category_ids": [19],
    }
    output_schema = {
        "contract_version": BOUNDARY_CONTRACT_VERSION,
        "required_facts": REQUIRED_FACTS,
        "fact_shape": {
            "value": "Boolean",
            "evidence_sources": "Array<String>",
            "evidence_detail": "String",
        },
    }

    return {
        "boundary_gates_json": json.dumps(boundary_gates, ensure_ascii=False),
        "boundary_gate_panel": "\n".join(BOUNDARY_GATE_PANEL_LINES),
        "boundary_output_schema_json": json.dumps(output_schema, ensure_ascii=False),
        "boundary_contract_version": BOUNDARY_CONTRACT_VERSION,
        "boundary_builder_warnings": json.dumps(warnings, ensure_ascii=False),
    }


async def main(args: Args) -> Output:
    return build_boundary_gate_output(args.params)
