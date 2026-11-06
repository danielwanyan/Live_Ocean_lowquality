import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import live_boundary_finalizer as finalizer
import live_boundary_gate_builder as builder

CASES = json.loads((ROOT / "tests/fixtures/user_corrections_2026-11-06.json").read_text())


def run_case(case):
    payload = copy.deepcopy(case["exported_output"])
    payload["rules_version"] = builder.BOUNDARY_CONTRACT_VERSION
    payload["boundary_checks"]["contract_version"] = builder.BOUNDARY_CONTRACT_VERSION
    for key in builder.REQUIRED_FACTS:
        payload["boundary_checks"]["facts"].setdefault(key, {"value": False, "evidence_sources": [], "evidence_detail": ""})
    if 20 in finalizer.EXPECTED_CATEGORY_NAMES and not any(x["category_id"] == 20 for x in payload["final_results"]):
        item = copy.deepcopy(payload["final_results"][14])
        item.update(category_id=20, category_name="挂品与直播间商品不一致低质问题", decision="no_hit", confidence="medium", evidence_count=0, evidence=[], judge_reason="尚未判断独立IPP。", materials_used=[], product_image_used=False, product_image_permission_ok=True, priority_rule_applied=[])
        payload["final_results"].append(item)
        payload["no_hit_category_ids"].append(20)
    n = case["normalized"]
    g = builder.build_boundary_gate_output(dict(n, rules_version=builder.BOUNDARY_CONTRACT_VERSION, rules_warning=""))
    p = dict(n, **g, rules_version=builder.BOUNDARY_CONTRACT_VERSION, rules_warning="", judge_output="FINAL_JSON:" + json.dumps(payload, ensure_ascii=False))
    result = finalizer.finalize_judge_output(p)
    if result["finalization_status"] == "fail":
        raise AssertionError(result["finalizer_errors"])
    return json.loads(result["finalized_final_json"]), result


class UserCorrections(unittest.TestCase):
    def test_four_zero_segment_rooms_cannot_hit_interaction_or_relevance(self):
        for case in CASES:
            if case["normalized"]["segment_count"] != 0:
                continue
            with self.subTest(room_id=case["room_id"]):
                p, _ = run_case(case)
                by_id = {x["category_id"]: x for x in p["final_results"]}
                self.assertEqual(by_id[3]["decision"], "unable_to_judge")
                self.assertEqual(by_id[4]["decision"], "unable_to_judge")
                self.assertEqual(by_id[3]["evidence"], [])
                self.assertEqual(by_id[4]["evidence"], [])

    def test_ipp_is_independent_and_never_illegal_goods(self):
        case = next(x for x in CASES if x["room_id"] == "ipp_case")
        p, _ = run_case(case)
        by_id = {x["category_id"]: x for x in p["final_results"]}
        self.assertEqual(by_id[15]["decision"], "no_hit")
        self.assertEqual(by_id[20]["decision"], "hit")
        self.assertEqual(by_id[20]["category_name"], "挂品与直播间商品不一致低质问题")
        self.assertEqual(len(p["final_results"]), 20)

    def test_costume_product_description_is_not_sexual_content(self):
        case = next(x for x in CASES if x["room_id"] == "costume_case")
        p, _ = run_case(case)
        self.assertEqual(p["final_results"][0]["decision"], "no_hit")
        self.assertNotIn(1, p["hit_category_ids"])

    def test_real_sexual_behavior_still_hits(self):
        case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "costume_case"))
        fact = case["exported_output"]["boundary_checks"]["facts"]["sexualized_exposure_or_behavior_found"]
        fact.update(value=True, evidence_sources=["Segment #7 frame"], evidence_detail="主播本人脱衣露出生殖器并进行明确性行为，持续聚焦裸露性部位。")
        case["exported_output"]["final_results"][0]["evidence"] = [{"source":"Segment #7 frame", "quote_or_visual_detail":fact["evidence_detail"], "reason":"明确色情行为"}]
        case["exported_output"]["final_results"][0]["evidence_count"] = 1
        p, _ = run_case(case)
        self.assertEqual(p["final_results"][0]["decision"], "hit")

    def test_illegal_goods_with_two_sources_still_hit(self):
        case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "ipp_case"))
        facts = case["exported_output"]["boundary_checks"]["facts"]
        for k in ["live_promoted_item_evidence_found", "bound_product_evidence_found", "core_product_contradiction_found"]:
            facts[k] = {"value": False, "evidence_sources": [], "evidence_detail": ""}
        facts["category_15_non_ipp_illegal_basis_found"] = {"value": True, "evidence_sources": ["Segment #1 ASR", "Pearl product #1 title"], "evidence_detail": "主播口播出售真实枪支，挂品标题明确为真实手枪。"}
        p, _ = run_case(case)
        self.assertEqual(p["final_results"][14]["decision"], "hit")
        self.assertNotIn(20, p["hit_category_ids"])

    def test_explicit_sexual_offer_is_not_exempted_by_clothing_words(self):
        for detail in ["While wearing a bra, the host offers oral sex to viewers repeatedly.", "主播穿着文胸，对观众反复说‘想跟你上床，给你口交’。"]:
            with self.subTest(detail=detail):
                case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "costume_case"))
                fact = case["exported_output"]["boundary_checks"]["facts"]["sexualized_exposure_or_behavior_found"]
                fact.update(value=True, evidence_sources=["Segment #4 ASR"], evidence_detail=detail)
                p, _ = run_case(case)
                self.assertEqual(p["final_results"][0]["decision"], "hit")

    def test_valid_live_evidence_survives_missing_comment_statistics(self):
        for category_id, fact_name, detail in [(3, "unrelated_content_dominates", "全部10段ASR均为主播持续讲个人生活，与任何商品无关；评论统计数据缺失。"), (4, "sustained_no_promotion_and_no_interaction_found", "全部10段ASR持续为主播自言自语，无商品推广或观众回应；评论统计数据缺失。")]:
            with self.subTest(category_id=category_id):
                case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "costume_case"))
                facts = case["exported_output"]["boundary_checks"]["facts"]
                facts["sustained_product_promotion_found"] = {"value":False,"evidence_sources":[],"evidence_detail":""}
                facts[fact_name] = {"value":True,"evidence_sources":["Segment #7 ASR"],"evidence_detail":detail}
                p, _ = run_case(case)
                self.assertEqual(p["final_results"][category_id-1]["decision"], "hit")

    def test_ipp_final_evidence_must_include_live_and_bound_sources(self):
        case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "ipp_case"))
        item = copy.deepcopy(case["exported_output"]["final_results"][14])
        item.update(category_id=20, category_name="挂品与直播间商品不一致低质问题", evidence=[{"source":"Pearl product #1 title", "quote_or_visual_detail":"Bound freshener title", "reason":"Bound goods"}, {"source":"Pearl product #1 image", "quote_or_visual_detail":"Bound freshener image", "reason":"Bound goods"}], evidence_count=2)
        case["exported_output"]["final_results"].append(item)
        p, _ = run_case(case)
        sources=[x["source"] for x in p["final_results"][19]["evidence"]]
        self.assertTrue(any(x.startswith("Segment #") for x in sources))
        self.assertTrue(any(x.startswith("Pearl product #") for x in sources))

    def test_interaction_fact_cannot_be_supported_by_frame_only(self):
        case = copy.deepcopy(next(x for x in CASES if x["room_id"] == "costume_case"))
        facts = case["exported_output"]["boundary_checks"]["facts"]
        facts["sustained_product_promotion_found"] = {"value":False,"evidence_sources":[],"evidence_detail":""}
        facts["sustained_no_promotion_and_no_interaction_found"] = {"value":True,"evidence_sources":["Segment #7 frame"],"evidence_detail":"Static unattended screen throughout the captured interval; no product speech or host response."}
        p, _ = run_case(case)
        self.assertNotIn(4, p["hit_category_ids"])
