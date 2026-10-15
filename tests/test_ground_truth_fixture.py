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
EXPECTED_REVIEWS = [
    {
        "room_id": "7683777632135170819",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7683557938614536982",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7684604074263579394",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7682666560909003523",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7683442568729824023",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7683929339473283862",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7683556905641429782",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7684303184864529174",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7683403737167121174",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7684635473842604822",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7684940374084045590",
        "is_low_quality": False,
        "category_ids": [],
    },
    {
        "room_id": "7684941369542052630",
        "is_low_quality": True,
        "category_ids": [12],
    },
    {
        "room_id": "7684150291864488726",
        "is_low_quality": True,
        "category_ids": [12, 15],
    },
]


class GroundTruthFixtureTest(unittest.TestCase):
    def load_fixture(self):
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_reviews_lock_the_normalized_ground_truth(self):
        fixture = self.load_fixture()
        reviews = fixture["reviews"]

        self.assertEqual(reviews, EXPECTED_REVIEWS)
        for review in reviews:
            self.assertEqual(
                set(review),
                {"room_id", "is_low_quality", "category_ids"},
            )
            self.assertIs(type(review["is_low_quality"]), bool)

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

    def test_root_fields_record_source_counts_and_keyed_human_override(self):
        fixture = self.load_fixture()
        reviews = fixture["reviews"]
        low_quality_count = sum(
            review["is_low_quality"] is True for review in reviews
        )
        clean_count = sum(
            review["is_low_quality"] is False for review in reviews
        )

        self.assertEqual(
            set(fixture),
            {
                "schema_version",
                "source_file",
                "reviewed_room_count",
                "expected_low_quality_room_count",
                "expected_clean_room_count",
                "human_overrides",
                "reviews",
            },
        )
        self.assertEqual(fixture["schema_version"], "1.0-normalized")
        self.assertEqual(
            fixture["source_file"],
            "/Users/bytedance/Downloads/直播间低质人审结果_2026-10-15.json",
        )
        self.assertEqual(fixture["reviewed_room_count"], 13)
        self.assertEqual(fixture["expected_low_quality_room_count"], 2)
        self.assertEqual(fixture["expected_clean_room_count"], 11)
        self.assertEqual(fixture["reviewed_room_count"], len(reviews))
        self.assertEqual(fixture["expected_low_quality_room_count"], low_quality_count)
        self.assertEqual(fixture["expected_clean_room_count"], clean_count)
        self.assertEqual(
            fixture["human_overrides"],
            {
                "7684940374084045590": {
                    "is_low_quality": False,
                    "category_ids": [],
                    "reason": "普通营销和知识营销，没有实质功能效果虚假证据，也没有负面引导。",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
