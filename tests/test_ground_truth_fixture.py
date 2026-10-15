import json
import os
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(
    PROJECT_DIR,
    "tests",
    "fixtures",
    "live_ocean_gt_2026-10-15_normalized.json",
)


class GroundTruthFixtureTest(unittest.TestCase):
    def load_fixture(self):
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_reviews_lock_the_normalized_ground_truth(self):
        fixture = self.load_fixture()
        reviews = fixture["reviews"]

        self.assertEqual(len(reviews), 13)
        self.assertEqual(len({review["room_id"] for review in reviews}), 13)

        reviews_by_room = {review["room_id"]: review for review in reviews}
        expected_clean_room_ids = {
            "7683777632135170819",
            "7683557938614536982",
            "7684604074263579394",
            "7682666560909003523",
            "7683442568729824023",
            "7683929339473283862",
            "7683556905641429782",
            "7684303184864529174",
            "7683403737167121174",
            "7684635473842604822",
            "7684940374084045590",
        }
        expected_low_quality_reviews = {
            "7684941369542052630": [12],
            "7684150291864488726": [12, 15],
        }

        self.assertEqual(
            {
                room_id
                for room_id, review in reviews_by_room.items()
                if not review["is_low_quality"]
            },
            expected_clean_room_ids,
        )
        self.assertEqual(
            {
                room_id: review["category_ids"]
                for room_id, review in reviews_by_room.items()
                if review["is_low_quality"]
            },
            expected_low_quality_reviews,
        )

        low_quality_reviews = [review for review in reviews if review["is_low_quality"]]
        clean_reviews = [review for review in reviews if not review["is_low_quality"]]
        self.assertEqual(len(low_quality_reviews), 2)
        self.assertEqual(len(clean_reviews), 11)
        self.assertEqual(
            sorted(tuple(review["category_ids"]) for review in low_quality_reviews),
            [(12,), (12, 15)],
        )
        self.assertEqual(
            reviews_by_room["7684940374084045590"],
            {
                "room_id": "7684940374084045590",
                "is_low_quality": False,
                "category_ids": [],
            },
        )

    def test_metadata_records_source_counts_and_human_override(self):
        fixture = self.load_fixture()
        metadata = fixture["metadata"]

        self.assertEqual(metadata["schema_version"], "1.0-normalized")
        self.assertEqual(
            metadata["source_file"],
            "/Users/bytedance/Downloads/直播间低质人审结果_2026-10-15.json",
        )
        self.assertEqual(metadata["reviewed_room_count"], 13)
        self.assertEqual(metadata["expected_low_quality_room_count"], 2)
        self.assertEqual(metadata["expected_clean_room_count"], 11)
        self.assertEqual(
            metadata["human_overrides"],
            [
                {
                    "room_id": "7684940374084045590",
                    "is_low_quality": False,
                    "category_ids": [],
                    "reason": "普通营销和知识营销，没有实质功能效果虚假证据，也没有负面引导。",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
