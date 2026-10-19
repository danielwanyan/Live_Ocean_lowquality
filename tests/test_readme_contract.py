import os
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(PROJECT_DIR, "README.md")


def _section(text, heading, next_heading):
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


class ReadmeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(README_PATH, encoding="utf-8") as file_obj:
            cls.readme = file_obj.read()

    def test_gate_builder_documents_exact_eight_inputs(self):
        section = _section(
            self.readme,
            "## Live_Boundary_Gate_Builder",
            "## LowQuality_Judge",
        )
        self.assertIn("Configure exactly these 8 Input Variables:", section)
        expected_rows = (
            "| `segments_json` | String | `Normalize_Input.segments_json` |",
            "| `segment_count` | Integer | `Normalize_Input.segment_count` |",
            "| `comment_interaction` | String | `Normalize_Input.comment_interaction` |",
            "| `product_catalog_json` | String | `Normalize_Input.product_catalog_json` |",
            "| `product_count` | Integer | `Normalize_Input.product_count` |",
            "| `material_quality_warning` | String | `Normalize_Input.material_quality_warning` |",
            "| `rules_version` | String | `Rules_Brain.rules_version` |",
            "| `rules_warning` | String | `Rules_Brain.rules_warning` |",
        )
        for row in expected_rows:
            self.assertIn(row, section)
        for retired_input in (
            "`rules_context`",
            "`category_catalog`",
            "`priority_rules_context`",
            "`threshold_rules_context`",
        ):
            self.assertNotIn(retired_input, section)

    def test_finalizer_documents_exact_thirteen_inputs(self):
        section = _section(
            self.readme,
            "## Live_Boundary_Finalizer",
            "## Output_Validator and End",
        )
        self.assertIn("Configure all 13 mandatory v3 inputs.", section)
        self.assertIn("| `rules_warning` | String | `Rules_Brain.rules_warning` |", section)
        self.assertIn(
            "| `boundary_builder_warnings` | String | `Live_Boundary_Gate_Builder.boundary_builder_warnings` |",
            section,
        )
        self.assertIn("builder warnings", section.lower())

    def test_v3_rule_urls_use_published_live_lowquality_commit(self):
        base = "https://raw.githubusercontent.com/danielwanyan/Live_lowquality/d8355c94be3bece9836a6d5a2e889b091208afc6/rules/"
        self.assertIn(
            base + "live_ocean_lowquality_rules_structured_v1.json",
            self.readme,
        )
        self.assertIn(
            base + "live_ocean_lowquality_judge_rules_compact_v1.txt",
            self.readme,
        )
        self.assertNotIn("27cbff1c51f3a71f40ce92a962446fa858cc2616", self.readme)
        self.assertNotIn("remote 404 until", self.readme)

    def test_rollout_uses_documented_contract_without_user_preflight(self):
        self.assertNotIn("Mandatory live-UI preflight", self.readme)
        self.assertIn("reuse the existing Judge raw-text mapping", self.readme)


if __name__ == "__main__":
    unittest.main()
