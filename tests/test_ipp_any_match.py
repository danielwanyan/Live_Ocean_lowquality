import copy
import json
import unittest

from test_boundary_finalizer import build_params, fact, valid_payload
from live_boundary_finalizer import finalize_judge_output
from output_validator_node import validate_judge_output
from test_rule_calibration import _validator_params_from_finalizer
from live_boundary_gate_builder import build_boundary_gate_output


def alignment():
    return {
        'sales_mode': 'regular', 'sales_mode_evidence': [],
        'live_selling_confirmed': True,
        'selling_evidence': [{'source': 'Segment #1 ASR', 'detail': 'Host explains price and ordering for this item.'}],
        'checked_product_indexes': [1], 'matches': [],
        'unmatched_promoted_items': [{'live_source': 'Segment #1 frame', 'product_source': 'Pearl product #1 title', 'basis': 'Live clothing versus bound cleaning spray; core use differs.'}],
    }


def mismatch_payload():
    p = valid_payload()
    facts = p['boundary_checks']['facts']
    facts['live_promoted_item_evidence_found'] = fact(True, ['Segment #1 ASR'])
    facts['bound_product_evidence_found'] = fact(True, ['Pearl product #1 title'])
    facts['core_product_contradiction_found'] = fact(True, ['Segment #1 frame', 'Pearl product #1 title'])
    p['boundary_checks']['ipp_alignment'] = alignment()
    return p


def run(p):
    result = finalize_judge_output(build_params(p))
    if result['finalization_status'] == 'fail':
        return result, None
    return result, json.loads(result['finalized_final_json'])


class IPPAnyMatch(unittest.TestCase):
    def test_any_valid_catalog_match_overrides_other_contradictions(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment']['matches'] = [{'segment_index': 1, 'product_index': 1, 'live_source': 'Segment #1 frame', 'product_source': 'Pearl product #1 image', 'basis': 'Same identifiable package in live frame and catalog.'}]
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')
        self.assertNotIn(20, out['hit_category_ids'])

    def test_auction_with_live_evidence_blocks_ipp(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment'].update(sales_mode='auction', sales_mode_evidence=[{'kind':'auction_sign','source': 'Segment #1 frame', 'detail': 'Visible HALLOWEEN AUCTION sign and bidding rules.'}])
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_non_selling_hobby_display_cannot_be_ipp(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment'].update(live_selling_confirmed=False, selling_evidence=[])
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_missing_alignment_cannot_promote_old_boolean_facts_to_ipp(self):
        p = mismatch_payload()
        del p['boundary_checks']['ipp_alignment']
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_partial_catalog_check_cannot_hit(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment']['checked_product_indexes'] = []
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_valid_full_catalog_mismatch_still_hits(self):
        r, out = run(mismatch_payload())
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'hit')

    def test_invalid_product_index_is_not_accepted_as_a_match(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment']['matches'] = [{'segment_index': 1, 'product_index': 99, 'live_source': 'Segment #1 frame', 'product_source': 'Pearl product #1 image', 'basis': 'Claimed match.'}]
        r, out = run(p)
        self.assertEqual(r['finalization_status'], 'fail')
        self.assertIn('ipp_alignment', r['finalizer_errors'])

    def test_match_prevents_language_reroute_from_reviving_ipp(self):
        p = mismatch_payload()
        p['final_results'][7].update(decision='hit', evidence_count=1, evidence=[{'source':'Segment #1 ASR','quote_or_visual_detail':'Product description in another language.','reason':'Language issue.'}])
        p['boundary_checks']['ipp_alignment']['matches'] = [{'segment_index':1,'product_index':1,'live_source':'Segment #1 frame','product_source':'Pearl product #1 image','basis':'Same package.'}]
        r, out = run(p)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_unproven_auction_label_does_not_exempt_a_true_mismatch(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment'].update(sales_mode='auction', sales_mode_evidence=[])
        r, out = run(p)
        self.assertEqual(r['finalization_status'], 'fail')
        self.assertIn('ipp_alignment', r['finalizer_errors'])

    def test_validator_rejects_final_ipp_hit_with_a_match(self):
        r, out = run(mismatch_payload())
        out['boundary_checks']['ipp_alignment']['matches'] = [{'segment_index':1,'product_index':1,'live_source':'Segment #1 frame','product_source':'Pearl product #1 image','basis':'Same package.'}]
        params = _validator_params_from_finalizer(r)
        params['judge_output'] = 'FINAL_JSON:' + json.dumps(out, ensure_ascii=False)
        result = validate_judge_output(params)
        self.assertEqual(result['validation_status'], 'fail')
        self.assertIn('ipp_alignment', result['validation_errors'])

    def test_validator_rejects_final_ipp_hit_without_alignment(self):
        r, out = run(mismatch_payload())
        del out['boundary_checks']['ipp_alignment']
        params = _validator_params_from_finalizer(r)
        params['judge_output'] = 'FINAL_JSON:' + json.dumps(out, ensure_ascii=False)
        result = validate_judge_output(params)
        self.assertEqual(result['validation_status'], 'fail')
        self.assertIn('ipp_alignment', result['validation_errors'])

    def test_missing_identity_for_one_catalog_row_requires_unable(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment']['checked_product_indexes'] = [1, 2]
        p['material_summary']['product_count'] = 2
        params = build_params(p)
        products = json.loads(params['product_catalog_json'])
        products.append({'product_index':2,'product_id':'2','title':'','image_urls':[]})
        params.update(product_catalog_json=json.dumps(products), product_count=2)
        params.update(build_boundary_gate_output(params))
        r = finalize_judge_output(params)
        self.assertNotEqual(r['finalization_status'], 'fail')
        self.assertEqual(json.loads(r['finalized_final_json'])['final_results'][19]['decision'], 'unable_to_judge')

    def test_concrete_bids_and_settlement_are_valid_auction_evidence(self):
        for kind, detail in [('active_bidding','Viewer bids $50 and host declares SOLD to highest offer.'),('auction_settlement','画面显示起拍价1英镑，倒计时结束后主播宣布50英镑成交。')]:
            with self.subTest(kind=kind):
                p = mismatch_payload()
                p['boundary_checks']['ipp_alignment'].update(sales_mode='auction',sales_mode_evidence=[{'kind':kind,'source':'Segment #1 ASR','detail':detail}])
                r, out = run(p)
                self.assertNotEqual(r['finalization_status'], 'fail')
                self.assertEqual(out['final_results'][19]['decision'], 'no_hit')

    def test_incidental_auction_mention_is_not_supported_auction_evidence(self):
        p = mismatch_payload()
        p['boundary_checks']['ipp_alignment'].update(sales_mode='auction',sales_mode_evidence=[{'kind':'incidental_mention','source':'Segment #1 ASR','detail':'Mentions the word auction once while discussing shopping.'}])
        r, _ = run(p)
        self.assertEqual(r['finalization_status'], 'fail')

    def test_validator_rejects_incomplete_or_malformed_audit(self):
        for field, value in [('checked_product_indexes',[]),('selling_evidence','x'),('unmatched_promoted_items',[{'live_source':'invented','product_source':'Pearl product #1 title','basis':'Claim.'}])]:
            with self.subTest(field=field):
                r, out = run(mismatch_payload())
                out['boundary_checks']['ipp_alignment'][field] = value
                params = _validator_params_from_finalizer(r)
                params['judge_output'] = 'FINAL_JSON:' + json.dumps(out, ensure_ascii=False)
                result = validate_judge_output(params)
                self.assertEqual(result['validation_status'], 'fail')
                self.assertIn('ipp_alignment', result['validation_errors'])

    def test_validator_returns_failure_envelope_for_bad_boundary_checks(self):
        for boundary in [None, [], 'x']:
            with self.subTest(boundary=boundary):
                r, out = run(mismatch_payload())
                out['boundary_checks'] = boundary
                params = _validator_params_from_finalizer(r)
                params['judge_output'] = 'FINAL_JSON:' + json.dumps(out, ensure_ascii=False)
                result = validate_judge_output(params)
                self.assertEqual(result['validation_status'], 'fail')

    def test_malformed_image_fields_are_missing_catalog_identity(self):
        for value in ['[]', 'not-json', None]:
            with self.subTest(value=value):
                p = mismatch_payload()
                p['boundary_checks']['ipp_alignment']['checked_product_indexes'] = [1, 2]
                p['material_summary']['product_count'] = 2
                params = build_params(p)
                products = json.loads(params['product_catalog_json'])
                products.append({'product_index':2,'title':'','image_urls':value})
                params.update(product_catalog_json=json.dumps(products),product_count=2)
                params.update(build_boundary_gate_output(params))
                r = finalize_judge_output(params)
                self.assertNotEqual(r['finalization_status'], 'fail')
                self.assertEqual(json.loads(r['finalized_final_json'])['final_results'][19]['decision'], 'unable_to_judge')

    def test_sparse_segment_index_survives_finalizer_and_validator(self):
        p = json.loads(json.dumps(mismatch_payload()).replace('Segment #1', 'Segment #3'))
        params = build_params(p)
        segments = json.loads(params['segments_json']);segments[0]['segment_index'] = 3
        params['segments_json'] = json.dumps(segments)
        params.update(build_boundary_gate_output(params))
        r = finalize_judge_output(params)
        self.assertNotEqual(r['finalization_status'], 'fail')
        out = json.loads(r['finalized_final_json'])
        self.assertEqual(out['final_results'][19]['decision'], 'hit')
        v = validate_judge_output(_validator_params_from_finalizer(r))
        self.assertNotEqual(v['validation_status'], 'fail')


if __name__ == '__main__':
    unittest.main()
