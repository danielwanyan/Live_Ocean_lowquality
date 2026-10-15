# Live Ocean Low Quality

This repository contains the v3 Aicolate assets for live-room low-quality detection using Ocean and Pearl materials supplied directly by the Start node.

## Release status

- Rule version and boundary contract version: `2026-10-15-v3-cross-project-boundary-gates`.
- `LowQuality_Judge` remains the only LLM call. Every other workflow stage is HTTP or deterministic code.
- The v3 feature-branch assets are locally tested but have not been deployed to or persisted in Aicolate.
- Deploy the nodes, prompts, and rules as one coordinated cutover. Do not leave the active canvas on a mixed v2/v3 contract.
- Do not claim precision, recall, F1, or runtime quality before a real Aicolate rerun on the reviewed rooms. Platform/runtime errors must be reported separately from model-quality results.

## v3 workflow

```text
Start
  -> Normalize_Input
  -> Rules_JSON HTTP + Judge_Rules_Compact HTTP
  -> Rules_Brain
  -> Live_Boundary_Gate_Builder
  -> LowQuality_Judge (only LLM)
  -> Live_Boundary_Finalizer
  -> Output_Validator
  -> End
```

`Rules_JSON` supplies structured rules to `Rules_Brain`; `Judge_Rules_Compact.body` supplies the compact text rules to `LowQuality_Judge.judge_rules_compact`.

## Start and Normalize contracts

Start inputs remain:

```text
room_id
ocean_segment_count
ocean_summary
ocean_segment_ASR
ocean_segment_frame_urls
pearl_product_count
pearl_product_ids
pearl_product_titles
pearl_product_images
```

`Normalize_Input` outputs remain:

```text
room_id: String
segments_json: String
segment_count: Integer
comment_interaction: String
product_catalog_json: String
product_count: Integer
material_quality_warning: String
debug_input_shape: String
all_frame_urls: Array<String>
all_product_image_urls: Array<String>
```

## Live_Boundary_Gate_Builder

Configure exactly these 11 Input Variables:

| Input Variable | Type | Source |
|---|---|---|
| `segments_json` | String | `Normalize_Input.segments_json` |
| `segment_count` | Integer | `Normalize_Input.segment_count` |
| `comment_interaction` | String | `Normalize_Input.comment_interaction` |
| `product_catalog_json` | String | `Normalize_Input.product_catalog_json` |
| `product_count` | Integer | `Normalize_Input.product_count` |
| `material_quality_warning` | String | `Normalize_Input.material_quality_warning` |
| `rules_context` | String | `Rules_Brain.rules_context` |
| `category_catalog` | String | `Rules_Brain.category_catalog` |
| `priority_rules_context` | String | `Rules_Brain.priority_rules_context` |
| `threshold_rules_context` | String | `Rules_Brain.threshold_rules_context` |
| `rules_version` | String | `Rules_Brain.rules_version` |

Declare exactly these five Output Panel fields; every field is `String`:

```text
boundary_gates_json: String
boundary_gate_panel: String
boundary_output_schema_json: String
boundary_contract_version: String
boundary_builder_warnings: String
```

## LowQuality_Judge

Keep every existing text input:

```text
room_id
segments_json
segment_count
comment_interaction
product_catalog_json
product_count
material_quality_warning
rules_context
category_catalog
product_image_permission_matrix
priority_rules_context
threshold_rules_context
rules_version
judge_rules_compact             Judge_Rules_Compact.body
```

Add exactly these three flat `String` text inputs:

| Input Variable | Type | Source |
|---|---|---|
| `boundary_gate_panel` | String | `Live_Boundary_Gate_Builder.boundary_gate_panel` |
| `boundary_output_schema_json` | String | `Live_Boundary_Gate_Builder.boundary_output_schema_json` |
| `boundary_contract_version` | String | `Live_Boundary_Gate_Builder.boundary_contract_version` |

Vision inputs are unchanged:

```text
all_frame_urls                  Normalize_Input.all_frame_urls
all_product_image_urls          Normalize_Input.all_product_image_urls
```

The System Prompt is plain text. The User Prompt contains the JSON contract and variable interpolation.

## Live_Boundary_Finalizer

Configure exactly these inputs:

| Input Variable | Type | Source |
|---|---|---|
| `judge_output` | String | Select the exact current raw-text field already wired from `LowQuality_Judge` to the old Validator in the live UI; do not guess `output` versus `result` |
| `boundary_gates_json` | String | `Live_Boundary_Gate_Builder.boundary_gates_json` |
| `boundary_contract_version` | String | `Live_Boundary_Gate_Builder.boundary_contract_version` |
| `rules_version` | String | `Rules_Brain.rules_version` |
| `room_id` | String | `Normalize_Input.room_id` |

Declare exactly these five Output Panel fields; every field is `String`:

```text
finalized_judge_output: String
finalized_final_json: String
finalization_status: String
boundary_override_log: String
finalizer_errors: String
```

## Output_Validator and End

Change the Validator mapping as follows:

```text
judge_output        Live_Boundary_Finalizer.finalized_judge_output
finalization_status Live_Boundary_Finalizer.finalization_status
finalizer_errors    Live_Boundary_Finalizer.finalizer_errors
```

Keep all other existing Validator inputs. Its Output Panel keys are unchanged:

```text
validation_status
validation_errors
validated_final_json
final_report_text
room_id
hit_category_ids
no_hit_category_ids
unable_to_judge_category_ids
```

`End` continues to consume the Validator outputs. Declare every returned Code Node key in its Output Panel and map downstream variables explicitly; do not add extra canvas edges merely to make variables visible.

## Rule raw URLs

```text
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Verify the published raw URLs after every rules or prompt release.

## Copy sources

Use these files when configuring Aicolate manually:

```text
scripts/normalize_input_node.py
scripts/rules_brain_node.py
scripts/live_boundary_gate_builder.py
scripts/live_boundary_finalizer.py
scripts/output_validator_node.py
prompts/lowquality_judge_system_prompt_v1.txt
prompts/lowquality_judge_user_prompt_v1.txt
rules/live_ocean_lowquality_rules_structured_v1.json
rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Durable project documentation and paste-ready mirrors are maintained under:

```text
/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/live-ocean-lowquality/
```

## Tests

Run the full repository suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Local tests verify deterministic assets and contracts only. They do not prove Aicolate deployment state or runtime metrics.
