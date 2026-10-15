import copy
import json
import os
import re
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
import rules_brain_node
from rules_brain_node import FALLBACK_RULES, PRODUCT_IMAGE_ALLOWED_IDS, build_rules_brain_output


RULES_PATH = os.path.join(PROJECT_DIR, "rules", "live_ocean_lowquality_rules_structured_v1.json")
COMPACT_RULES_PATH = os.path.join(PROJECT_DIR, "rules", "live_ocean_lowquality_judge_rules_compact_v1.txt")
SYSTEM_PROMPT_PATH = os.path.join(PROJECT_DIR, "prompts", "lowquality_judge_system_prompt_v1.txt")
EXPECTED_V3_VERSION = "2026-10-15-v3-cross-project-boundary-gates"
EXPECTED_PRIORITY_MAPPINGS = {
    "priority_3_over_5_for_unrelated_content": (3, 5),
    "priority_3_over_6": (3, 6),
    "priority_5_over_6_for_no_physical_display": (5, 6),
    "priority_15_over_8_for_product_mismatch": (15, 8),
    "priority_1_over_19": (1, 19),
}
EXPECTED_CATEGORY_9_HIT_DEFINITION_ZH = (
    "直播中使用有明确生成证据的 AIGC 内容进行商品推广，并对内容或展示主体的真实性造成误导。"
)
EXPECTED_CATEGORY_12_HIT_DEFINITION_ZH = (
    "仅当直播画面或 ASR 中存在具体商品功能效果主张，且该主张有实质误导依据并达到现行覆盖度/强度阈值时命中；"
    "商品物料仅可佐证，不能单独构成命中。"
)
EXPECTED_COMPACT_CATEGORY_11_HIT = (
    "Hit: a clear replay/loop/pre-recorded indicator is required, such as replay/loop labels, "
    "playback controls, video timeline, repeated sequence, abnormal jump, black/green screen, "
    "nested screen with a clear replay feature, or ASR directly mentioning replay/loop playback. "
    "Taskbar, cursor, browser, desktop, or OBS alone cannot hit."
)

EXPECTED_RULE_CATEGORY_NAMES = [
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

EXPECTED_ALLOWED_MATERIALS = {
    1: ["segment_frame", "segment_asr"],
    2: ["segment_frame", "segment_asr"],
    3: ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"],
    4: ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"],
    5: ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"],
    6: ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"],
    7: ["segment_frame"],
    8: ["segment_asr", "segment_frame_visible_text"],
    9: ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"],
    10: ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"],
    11: ["segment_frame", "segment_asr"],
    12: ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"],
    13: ["segment_frame", "segment_asr"],
    14: ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"],
    15: ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"],
    16: ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"],
    17: ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"],
    18: ["segment_frame", "segment_asr", "comment_interaction"],
    19: ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"],
}

UNCHANGED_CATEGORY_SNAPSHOTS = {
    4: {
        "trigger_threshold": "Hit when most available segment ASR evidence, supported by comment_interaction when available, shows both no product promotion and no host-audience interaction. Do not use a fixed ratio threshold from the old workflow.",
        "exemptions": [],
    },
    7: {
        "trigger_threshold": "Any segment frame group shows an occlusion/interruption layer covering at least 80% of the live screen and seriously blocking viewing.",
        "exemptions": [],
    },
    8: {
        "trigger_threshold": "Hit only when segment ASR or visible text in segment frames uses a language that is not acceptable for the target market, Chinese/CJK in product promotion, Chinglish, incomprehensible English, or severely broken English, and this prevents normal product understanding across the live. Product mismatch, ethnic clothing style, non-English product titles, or OCR noise alone is not a language hit.",
        "exemptions": [
            "Coworker daily Chinese conversation unrelated to product promotion.",
            "Minor accent that is easy to understand.",
            "Normal English/local EU-language mixing, including German, French, Spanish, Italian, Dutch, Polish, or other EU language words mixed with English.",
            'German "Englisch" as a local-language word.',
            "Isolated frame-text recognition noise, stylized labels, usernames, product names, or minor spelling mistakes unless overall promotion text becomes incomprehensible.",
            "Product mismatch or item/category difference is not a language violation.",
        ],
    },
    13: {
        "trigger_threshold": "Cumulative at least 2 segment frame or segment ASR evidence units show life-threatening violent behavior or dangerous goods demonstration, including heavy-smoke products creating fire illusion.",
        "exemptions": ["Normal product demonstration, explanation, and safe behavior."],
    },
    16: {
        "trigger_threshold": "Cumulative at least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show political controversy, sensitive political symbols/movements, political hate symbols, racial discrimination, or polarized political narratives.",
        "exemptions": ["General non-political content unrelated to controversy or sensitive symbols."],
    },
    17: {
        "trigger_threshold": "Cumulative at least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show sensitive topics related to religion, racial discrimination, moral boundary, LGBT, or similarly high-conflict socio-cultural themes.",
        "exemptions": ["General non-sensitive content outside the specified topic scope."],
    },
}

V3_CATEGORY_GUARD_TERMS = {
    1: [
        "ordinary try-on",
        "gym",
        "swimwear",
        "shapewear",
        "without explicit sexual framing",
    ],
    2: [
        "dominant",
        "strong discomfort",
        "cleaning",
        "novelty/product art",
        "calendar",
        "packaging",
        "hard-exempt",
    ],
    3: [
        "sustained unrelated core",
        "short opening",
        "later substantive product demonstration",
    ],
    5: [
        "real package",
        "wearing",
        "installation",
        "operation",
        "application/use",
        "physical display",
        "unrelated dominance",
        "category 3",
    ],
    6: [
        "identifiable product or package",
        "core purpose",
        "core buying fact",
        "blocks category 6",
        "deep ingredient",
        "mechanism",
    ],
    9: [
        "ai-like style alone is insufficient",
        "explicit generated-content evidence",
        "authenticity misleading",
    ],
    10: [
        "ai-like style alone is insufficient",
        "explicit generated product or use-scene",
        "material mismatch",
    ],
    11: ["browser", "desktop", "obs", "card", "spin", "cursor", "weak signals"],
    12: [
        "concrete live frame or asr claim",
        "materially misleading basis",
        "current prevalence/strength threshold",
        "product image is corroborative only",
        "product image copy",
        "routine marketing",
        "subjective praise alone cannot hit",
    ],
    14: ["same scene", "off-platform destination", "transaction guidance"],
    15: [
        "cumulative at least 2",
        "live promoted item evidence",
        "bound product evidence",
        "entity/category/use/quantity/spec contradiction",
        "minor variant",
        "background difference",
        "prohibited",
        "counterfeit",
        "jailbreak",
        "non-ipp",
    ],
    18: [
        "cumulative at least 2",
        "routine sales pressure",
        "knowledge marketing",
        "normal risk explanation",
        "hostile",
        "shaming",
        "fear",
    ],
    19: ["disabled", "always return no_hit"],
}


def _load_structured_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _category_text(category):
    return json.dumps(category, ensure_ascii=False).lower()


def _compact_category_sections(compact_rules):
    matches = list(re.finditer(r"(?m)^(\d+) .+$", compact_rules))
    sections = {}
    for index, match in enumerate(matches):
        category_id = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(compact_rules)
        sections[category_id] = compact_rules[match.start():end].lower()
    return sections


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
    def _assert_rules_brain_fallback(self, candidate_rules):
        result = build_rules_brain_output(
            {"rules_json": json.dumps(candidate_rules, ensure_ascii=False)}
        )
        category_catalog = json.loads(result["category_catalog"])

        self.assertEqual(result["rules_version"], EXPECTED_V3_VERSION)
        self.assertIn("invalid v3 rules contract", result["rules_warning"])
        self.assertIn("using fallback", result["rules_warning"])
        self.assertEqual(result["category_count"], 19)
        self.assertEqual(result["category_integrity_check"], "ok")
        self.assertEqual(result["permission_matrix_check"], "ok")
        self.assertEqual(
            [item["category_id"] for item in category_catalog],
            list(range(1, 20)),
        )

    def test_structured_rules_use_exact_v3_contract_version(self):
        rules = _load_structured_rules()

        self.assertEqual(rules["version"], EXPECTED_V3_VERSION)
        self.assertEqual(rules["boundary_contract_version"], EXPECTED_V3_VERSION)
        self.assertIn(
            "normalized 2026-10-15 reviewed baseline (13 reviewed, user override)",
            rules["global_rules"]["case_calibration_source"],
        )

    def test_structured_rules_preserve_fixed_categories_materials_and_permissions(self):
        rules = _load_structured_rules()
        categories = rules["categories"]

        self.assertEqual(rules["fixed_category_count"], 19)
        self.assertEqual([item["category_id"] for item in categories], list(range(1, 20)))
        self.assertEqual([item["category_name"] for item in categories], EXPECTED_RULE_CATEGORY_NAMES)
        self.assertEqual(
            {item["category_id"]: item["allowed_materials"] for item in categories},
            EXPECTED_ALLOWED_MATERIALS,
        )
        self.assertEqual(
            rules["product_image_allowed_category_ids"],
            PRODUCT_IMAGE_ALLOWED_IDS,
        )
        self.assertEqual(
            [item["category_id"] for item in categories if item["product_image_allowed"]],
            PRODUCT_IMAGE_ALLOWED_IDS,
        )

    def test_structured_rules_define_exact_five_exclusive_priorities(self):
        rules = _load_structured_rules()
        priorities = {
            item["id"]: (
                item["higher_priority_category_id"],
                item["lower_priority_category_id"],
            )
            for item in rules["exclusive_priority_rules"]
        }

        self.assertEqual(
            priorities,
            EXPECTED_PRIORITY_MAPPINGS,
        )
        priority_3_over_5 = next(
            item
            for item in rules["exclusive_priority_rules"]
            if item["id"] == "priority_3_over_5_for_unrelated_content"
        )
        for phrase in ("核心内容与商品无关", "没有持续商品推广", "category 3", "not category 5"):
            with self.subTest(phrase=phrase):
                self.assertIn(
                    phrase.lower(),
                    json.dumps(priority_3_over_5, ensure_ascii=False).lower(),
                )

    def test_structured_rules_include_each_v3_mapped_category_guard(self):
        rules = _load_structured_rules()
        by_id = {item["category_id"]: item for item in rules["categories"]}

        for category_id, terms in V3_CATEGORY_GUARD_TERMS.items():
            category_text = _category_text(by_id[category_id])
            for term in terms:
                with self.subTest(category_id=category_id, term=term):
                    self.assertIn(term, category_text)

    def test_unmapped_categories_keep_trigger_and_exemption_semantics(self):
        rules = _load_structured_rules()
        by_id = {item["category_id"]: item for item in rules["categories"]}

        for category_id, expected in UNCHANGED_CATEGORY_SNAPSHOTS.items():
            with self.subTest(category_id=category_id):
                self.assertEqual(by_id[category_id]["trigger_threshold"], expected["trigger_threshold"])
                self.assertEqual(by_id[category_id]["exemptions"], expected["exemptions"])

    def test_compact_rules_use_v3_contract_and_keep_all_categories_ordered(self):
        with open(COMPACT_RULES_PATH, encoding="utf-8") as f:
            compact_rules = f.read()

        self.assertTrue(
            compact_rules.startswith("Live Ocean Low Quality Single-Judge Compact Rules v3\n")
        )
        self.assertIn("Boundary contract version: " + EXPECTED_V3_VERSION, compact_rules)
        headings = re.findall(r"(?m)^(\d+) (.+)$", compact_rules)
        self.assertEqual([int(category_id) for category_id, _ in headings], list(range(1, 20)))
        self.assertEqual([name for _, name in headings], EXPECTED_RULE_CATEGORY_NAMES)

    def test_compact_rules_map_v3_guards_and_keep_category_7_as_occlusion_only(self):
        with open(COMPACT_RULES_PATH, encoding="utf-8") as f:
            compact_rules = f.read()

        sections = _compact_category_sections(compact_rules)
        for category_id, terms in V3_CATEGORY_GUARD_TERMS.items():
            for term in terms:
                with self.subTest(category_id=category_id, term=term):
                    self.assertIn(term, sections[category_id])

        category_7_section = compact_rules.split("7 静态帧遮挡低质问题", 1)[1].split(
            "8 非母语违规低质问题", 1
        )[0]
        self.assertIn("80%", category_7_section)
        self.assertNotIn("still_frame", category_7_section.lower())
        self.assertNotIn("still-frame", category_7_section.lower())
        self.assertNotIn("LowqualityVideo", category_7_section)

    def test_rules_brain_rejects_stale_or_invalid_top_level_contracts(self):
        stale_version = copy.deepcopy(_load_structured_rules())
        stale_version["version"] = "2026-09-18-v2-human-review-boundaries"
        missing_boundary_version = copy.deepcopy(_load_structured_rules())
        del missing_boundary_version["boundary_contract_version"]
        wrong_boundary_version = copy.deepcopy(_load_structured_rules())
        wrong_boundary_version["boundary_contract_version"] = "wrong-boundary"
        wrong_fixed_count = copy.deepcopy(_load_structured_rules())
        wrong_fixed_count["fixed_category_count"] = 18
        wrong_allowed_ids = copy.deepcopy(_load_structured_rules())
        wrong_allowed_ids["product_image_allowed_category_ids"] = PRODUCT_IMAGE_ALLOWED_IDS[:-1]

        cases = {
            "stale_version": stale_version,
            "missing_boundary_version": missing_boundary_version,
            "wrong_boundary_version": wrong_boundary_version,
            "wrong_fixed_count": wrong_fixed_count,
            "wrong_allowed_ids": wrong_allowed_ids,
        }
        for name, candidate_rules in cases.items():
            with self.subTest(name=name):
                self._assert_rules_brain_fallback(candidate_rules)

    def test_rules_brain_rejects_invalid_category_contracts(self):
        empty_categories = copy.deepcopy(_load_structured_rules())
        empty_categories["categories"] = []
        incomplete_categories = copy.deepcopy(_load_structured_rules())
        incomplete_categories["categories"].pop()
        duplicate_categories = copy.deepcopy(_load_structured_rules())
        duplicate_categories["categories"][-1] = copy.deepcopy(
            duplicate_categories["categories"][0]
        )
        out_of_order_categories = copy.deepcopy(_load_structured_rules())
        out_of_order_categories["categories"][0:2] = reversed(
            out_of_order_categories["categories"][0:2]
        )
        wrong_category_name = copy.deepcopy(_load_structured_rules())
        wrong_category_name["categories"][0]["category_name"] = "wrong-name"
        wrong_english_key = copy.deepcopy(_load_structured_rules())
        wrong_english_key["categories"][0]["english_key"] = "wrong_key"
        wrong_materials = copy.deepcopy(_load_structured_rules())
        wrong_materials["categories"][0]["allowed_materials"].append(
            "pearl_product_image"
        )
        wrong_product_permission = copy.deepcopy(_load_structured_rules())
        wrong_product_permission["categories"][0]["product_image_allowed"] = True
        wrong_threshold = copy.deepcopy(_load_structured_rules())
        wrong_threshold["categories"][0]["trigger_threshold"] = "stale threshold"
        missing_required_field = copy.deepcopy(_load_structured_rules())
        del missing_required_field["categories"][0]["trigger_threshold"]

        cases = {
            "empty_categories": empty_categories,
            "incomplete_categories": incomplete_categories,
            "duplicate_categories": duplicate_categories,
            "out_of_order_categories": out_of_order_categories,
            "wrong_category_name": wrong_category_name,
            "wrong_english_key": wrong_english_key,
            "wrong_materials": wrong_materials,
            "wrong_product_permission": wrong_product_permission,
            "wrong_threshold": wrong_threshold,
            "missing_required_field": missing_required_field,
        }
        for name, candidate_rules in cases.items():
            with self.subTest(name=name):
                self._assert_rules_brain_fallback(candidate_rules)

    def test_rules_brain_rejects_invalid_priority_contracts(self):
        wrong_priority_id = copy.deepcopy(_load_structured_rules())
        wrong_priority_id["exclusive_priority_rules"][0]["id"] = "wrong-priority"
        missing_priority = copy.deepcopy(_load_structured_rules())
        missing_priority["exclusive_priority_rules"].pop()
        wrong_priority_mapping = copy.deepcopy(_load_structured_rules())
        wrong_priority_mapping["exclusive_priority_rules"][0][
            "higher_priority_category_id"
        ] = 5
        wrong_lower_priority_mapping = copy.deepcopy(_load_structured_rules())
        wrong_lower_priority_mapping["exclusive_priority_rules"][0][
            "lower_priority_category_id"
        ] = 6
        duplicate_priority = copy.deepcopy(_load_structured_rules())
        duplicate_priority["exclusive_priority_rules"][-1] = copy.deepcopy(
            duplicate_priority["exclusive_priority_rules"][0]
        )

        cases = {
            "wrong_priority_id": wrong_priority_id,
            "missing_priority": missing_priority,
            "wrong_priority_mapping": wrong_priority_mapping,
            "wrong_lower_priority_mapping": wrong_lower_priority_mapping,
            "duplicate_priority": duplicate_priority,
        }
        for name, candidate_rules in cases.items():
            with self.subTest(name=name):
                self._assert_rules_brain_fallback(candidate_rules)

    def test_rules_brain_fallback_matches_structured_v3_category_contract_exactly(self):
        structured_categories = _load_structured_rules()["categories"]
        core_fields = (
            "category_id",
            "category_name",
            "english_key",
            "allowed_materials",
            "product_image_allowed",
            "trigger_threshold",
        )

        self.assertEqual(
            [item["trigger_threshold"] for item in FALLBACK_RULES["categories"]],
            [item["trigger_threshold"] for item in structured_categories],
        )
        self.assertEqual(
            [
                {field: item[field] for field in core_fields}
                for item in FALLBACK_RULES["categories"]
            ],
            [
                {field: item[field] for field in core_fields}
                for item in structured_categories
            ],
        )

    def test_category_11_compact_hit_rule_requires_replay_evidence(self):
        with open(COMPACT_RULES_PATH, encoding="utf-8") as f:
            compact_rules = f.read()
        category_11 = _compact_category_sections(compact_rules)[11]

        self.assertIn(EXPECTED_COMPACT_CATEGORY_11_HIT.lower(), category_11)
        self.assertNotIn("hit: any segment frame shows taskbar/cursor", category_11)

    def test_structured_aigc_authenticity_definition_does_not_overlap_category_10(self):
        by_id = {
            item["category_id"]: item for item in _load_structured_rules()["categories"]
        }

        self.assertEqual(
            by_id[9]["hit_definition_zh"],
            EXPECTED_CATEGORY_9_HIT_DEFINITION_ZH,
        )
        self.assertNotIn("与绑定实物商品不符", by_id[9]["hit_definition_zh"])

    def test_structured_category_12_definition_requires_live_claim(self):
        by_id = {
            item["category_id"]: item for item in _load_structured_rules()["categories"]
        }

        self.assertEqual(
            by_id[12]["hit_definition_zh"],
            EXPECTED_CATEGORY_12_HIT_DEFINITION_ZH,
        )
        self.assertNotIn("直播或商品物料对商品功能效果作出", by_id[12]["hit_definition_zh"])

    def test_rules_brain_invalid_rules_json_uses_exact_v3_fallback_with_warning(self):
        result = build_rules_brain_output({"rules_json": "{"})

        self.assertEqual(result["rules_version"], EXPECTED_V3_VERSION)
        self.assertIn("parse failed", result["rules_warning"])
        self.assertIn("Boundary contract version: " + EXPECTED_V3_VERSION, result["rules_context"])

    def test_rules_brain_fetched_structured_rules_return_exact_v3(self):
        rules = _load_structured_rules()
        result = build_rules_brain_output({"rules_json": json.dumps(rules, ensure_ascii=False)})

        self.assertEqual(result["rules_version"], EXPECTED_V3_VERSION)
        self.assertEqual(result["rules_warning"], "")
        self.assertEqual(result["category_count"], 19)
        self.assertEqual(result["category_integrity_check"], "ok")
        self.assertEqual(result["permission_matrix_check"], "ok")

    def test_rules_brain_fallback_preserves_category_and_permission_integrity(self):
        categories = FALLBACK_RULES["categories"]

        self.assertEqual(FALLBACK_RULES["version"], EXPECTED_V3_VERSION)
        self.assertEqual(FALLBACK_RULES["boundary_contract_version"], EXPECTED_V3_VERSION)
        self.assertEqual(FALLBACK_RULES["fixed_category_count"], 19)
        self.assertEqual([item["category_id"] for item in categories], list(range(1, 20)))
        self.assertEqual([item["category_name"] for item in categories], EXPECTED_RULE_CATEGORY_NAMES)
        self.assertEqual(
            {item["category_id"]: item["allowed_materials"] for item in categories},
            EXPECTED_ALLOWED_MATERIALS,
        )
        self.assertEqual(FALLBACK_RULES["product_image_allowed_category_ids"], PRODUCT_IMAGE_ALLOWED_IDS)
        self.assertEqual(
            [item["category_id"] for item in categories if item["product_image_allowed"]],
            PRODUCT_IMAGE_ALLOWED_IDS,
        )
        self.assertEqual(
            {
                item["id"]: (
                    item["higher_priority_category_id"],
                    item["lower_priority_category_id"],
                )
                for item in FALLBACK_RULES["exclusive_priority_rules"]
            },
            EXPECTED_PRIORITY_MAPPINGS,
        )

    def test_rules_brain_dynamic_context_exposes_required_v3_guards(self):
        result = build_rules_brain_output({"rules_json": "not-json"})
        context = result["rules_context"]

        self.assertIn("Boundary contract version: " + EXPECTED_V3_VERSION, context)
        self.assertIn("Category 3 product_unrelated overrides Category 5", context)
        self.assertIn("Category 2 hard exemptions: cleaning and novelty/product art/calendar/packaging", context)
        self.assertIn("Category 12 guard: require a concrete LIVE frame/ASR claim", context)
        self.assertIn("Product images are corroborative only", context)
        self.assertIn("Category 18 guard: routine sales pressure, knowledge marketing, and normal risk explanation", context)

    def test_cross_asset_contract_version_matches_gate_and_finalizer_expectations(self):
        rules = _load_structured_rules()

        self.assertEqual(BOUNDARY_CONTRACT_VERSION, EXPECTED_V3_VERSION)
        self.assertEqual(
            getattr(rules_brain_node, "BOUNDARY_CONTRACT_VERSION", None),
            EXPECTED_V3_VERSION,
        )
        self.assertEqual(rules["version"], BOUNDARY_CONTRACT_VERSION)
        self.assertEqual(rules["boundary_contract_version"], BOUNDARY_CONTRACT_VERSION)

        finalized = finalize_judge_output(_finalizer_params(_valid_finalizer_payload()))
        finalized_payload = json.loads(finalized["finalized_final_json"])
        self.assertEqual(finalized["finalization_status"], "pass")
        self.assertEqual(finalized_payload["rules_version"], EXPECTED_V3_VERSION)

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
