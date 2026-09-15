import json
import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from normalize_input_node import build_normalized_output


class NormalizeInputNodeTest(unittest.TestCase):
    def test_parses_all_segments_without_sampling(self):
        result = build_normalized_output(
            {
                "room_id": "7680904568477125398",
                "ocean_segment_count": "3",
                "ocean_segment_ASR": (
                    "Segment #1 [00:00:00-00:05:00]:\nFirst product talk\n\n"
                    "Segment #2 [00:05:00-00:10:00]:\nSecond product talk\n\n"
                    "Segment #3 [00:10:00-00:15:00]:\nThird product talk"
                ),
                "ocean_segment_frame_urls": (
                    "Segment #1 [00:00:00-00:05:00]: https://example.com/1.jpg?x=1\n"
                    "Segment #2 [00:05:00-00:10:00]: https://example.com/2.jpg?x=2; https://example.com/2b.jpg?x=2\n"
                    "Segment #3 [00:10:00-00:15:00]: https://example.com/3.jpg?x=3"
                ),
                "ocean_summary": "内容总结\nignored\n评论互动\nusers asked about size\n数据变化\nignored",
                "pearl_product_count": "0",
                "pearl_product_ids": "",
                "pearl_product_titles": "",
                "pearl_product_images": "",
            }
        )

        segments = json.loads(result["segments_json"])
        self.assertEqual(result["room_id"], "7680904568477125398")
        self.assertEqual(result["segment_count"], 3)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[1]["segment_index"], 2)
        self.assertEqual(segments[1]["time_range"], "00:05:00-00:10:00")
        self.assertEqual(segments[1]["asr_summary"], "Second product talk")
        self.assertEqual(
            segments[1]["frame_urls"],
            ["https://example.com/2.jpg?x=2", "https://example.com/2b.jpg?x=2"],
        )

    def test_extracts_chinese_comment_interaction_only(self):
        result = build_normalized_output(
            {
                "room_id": "1",
                "ocean_summary": "内容总结\n不要传入\n评论互动\n只保留这里\n数据变化\n不要传入",
            }
        )

        self.assertEqual(result["comment_interaction"], "只保留这里")

    def test_extracts_english_comment_interaction_only(self):
        result = build_normalized_output(
            {
                "room_id": "1",
                "ocean_summary": "Content Summary\ndo not use\nComment Interaction\nkeep this section\nData Analysis\ndo not use",
            }
        )

        self.assertEqual(result["comment_interaction"], "keep this section")

    def test_groups_pearl_images_by_product_line(self):
        result = build_normalized_output(
            {
                "room_id": "1",
                "pearl_product_count": "2",
                "pearl_product_ids": "p1\np2",
                "pearl_product_titles": "Product One\nProduct Two",
                "pearl_product_images": (
                    "https://example.com/p1-a.jpg; https://example.com/p1-b.jpg\n"
                    "https://example.com/p2-a.jpg"
                ),
            }
        )

        products = json.loads(result["product_catalog_json"])
        self.assertEqual(result["product_count"], 2)
        self.assertEqual(products[0]["product_id"], "p1")
        self.assertEqual(products[0]["title"], "Product One")
        self.assertEqual(products[0]["image_urls"], ["https://example.com/p1-a.jpg", "https://example.com/p1-b.jpg"])
        self.assertEqual(products[1]["image_urls"], ["https://example.com/p2-a.jpg"])

    def test_warns_for_missing_materials_and_segment_mismatch(self):
        result = build_normalized_output(
            {
                "room_id": "1",
                "ocean_segment_count": "2",
                "ocean_segment_ASR": "Segment #1 [00:00:00-00:05:00]:\nASR only",
                "ocean_segment_frame_urls": "",
                "ocean_summary": "Content Summary\nno comment section",
                "pearl_product_count": "0",
            }
        )

        warnings = json.loads(result["material_quality_warning"])
        self.assertIn("segment_count_mismatch_expected_2_parsed_1", warnings)
        self.assertIn("segment_1_frame_urls_missing", warnings)
        self.assertIn("comment_interaction_missing", warnings)
        self.assertIn("product_catalog_missing", warnings)

    def test_missing_count_fields_do_not_create_mismatch_warnings(self):
        result = build_normalized_output(
            {
                "room_id": "1",
                "ocean_segment_ASR": "Segment #1 [00:00:00-00:05:00]:\nASR",
                "ocean_segment_frame_urls": "Segment #1 [00:00:00-00:05:00]: https://example.com/1.jpg?x=1",
                "ocean_summary": "",
                "pearl_product_ids": "",
                "pearl_product_titles": "",
                "pearl_product_images": "",
            }
        )

        warnings = json.loads(result["material_quality_warning"])
        self.assertNotIn("segment_count_mismatch_expected_0_parsed_1", warnings)
        self.assertIn("comment_interaction_missing", warnings)
        self.assertIn("product_catalog_missing", warnings)


if __name__ == "__main__":
    unittest.main()
