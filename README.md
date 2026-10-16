# Live Ocean Low Quality

This repository contains the v3 Aicolate assets for live-room low-quality detection using Ocean and Pearl materials supplied directly by the Start node.

## Release status

- Rule version and boundary contract version: `2026-10-15-v3-cross-project-boundary-gates`.
- `LowQuality_Judge` remains the only LLM call. Every other workflow stage is HTTP or deterministic code.
- The v3 feature-branch assets are locally tested but have not been deployed to or persisted in Aicolate.
- Keep the active v2 path untouched while preparing an inactive/cloned v3 path. Duplicate the nodes/canvas branch when Aicolate supports it; otherwise create unconnected inactive v3 nodes that do not feed the active `End`.
- Deploy the nodes, prompts, and rules as one coordinated cutover. The only activation change is a single `End` switch from the retained v2 Validator to the verified v3 Validator.
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

For manual Aicolate paste, use only this scaffold-free copy:

```text
/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/live-ocean-lowquality/code_nodes/normalize_input_node.py
```

The repository `scripts/normalize_input_node.py` is local/test source, not the manual paste source. The Wiki copy omits the forbidden custom `Args`/`Output` scaffold and typing-only imports.

## Rules_Brain v3 update

The inactive v3 path must receive the v3 `Rules_Brain` code update before Gate Builder configuration. Paste the complete code from:

```text
/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/live-ocean-lowquality/code_nodes/rules_brain_node.py
```

Its Output Panel remains unchanged:

```text
rules_context: String
category_catalog: String
product_image_permission_matrix: String
priority_rules_context: String
threshold_rules_context: String
rules_version: String
rules_warning: String
category_count: Integer
category_integrity_check: String
permission_matrix_check: String
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

The five-field Output Panel is unchanged. Inside `boundary_gates_json`, v3 now carries the declared and observed segment/product counts, normalized material warnings, per-channel material reliability, material availability, and the exact allowed-source manifest (`allowed_source_labels`). The Finalizer reconstructs the same values from trusted Normalize inputs and rejects any mismatch.

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

The Judge output envelope is a Chinese human-review report followed by `FINAL_JSON:` and valid JSON; `raw_json_only` is `false`. Decision precedence is fixed:

1. Missing or unreliable required channel/material becomes `unable_to_judge`.
2. Required channels present but evidence below threshold becomes `no_hit`.
3. Disabled categories or forbidden-only evidence become `no_hit`, overriding missing-material handling.

Applicability is channel-specific: Category 3 requires reliable live Segment or Comment Interaction material; Category 6 requires reliable live frames; Category 10 requires a reliable live frame/ASR/visible-text channel plus Pearl title/image material. Missing a required group is `unable_to_judge`.

Category 9 permits concrete authenticity-deception evidence from any allowed live or Pearl material and remains distinct from Category 10. Category 10 requires a live Segment source proving generated content, an independent Pearl title/image source proving the bound product, a material mismatch comparison, and at least two distinct trusted sources. Category 5 still requires reliable live frames; product-promotion ASR without frames is `unable_to_judge`.

## Live_Boundary_Finalizer

Configure all 11 mandatory v3 inputs. The v3 path has no legacy bridge:

| Input Variable | Type | Source |
|---|---|---|
| `judge_output` | String | Select the exact current raw-text field already wired from `LowQuality_Judge` to the old Validator in the live UI; do not guess `output` versus `result` |
| `boundary_gates_json` | String | `Live_Boundary_Gate_Builder.boundary_gates_json` |
| `boundary_contract_version` | String | `Live_Boundary_Gate_Builder.boundary_contract_version` |
| `rules_version` | String | `Rules_Brain.rules_version` |
| `room_id` | String | `Normalize_Input.room_id` |
| `segments_json` | String | `Normalize_Input.segments_json` |
| `segment_count` | Integer | `Normalize_Input.segment_count` |
| `comment_interaction` | String | `Normalize_Input.comment_interaction` |
| `product_catalog_json` | String | `Normalize_Input.product_catalog_json` |
| `product_count` | Integer | `Normalize_Input.product_count` |
| `material_quality_warning` | String | `Normalize_Input.material_quality_warning` |

Declare exactly these five Output Panel fields; every field is `String`:

```text
finalized_judge_output: String
finalized_final_json: String
finalization_status: String
boundary_override_log: String
finalizer_errors: String
```

The Finalizer rebuilds `material_summary`, observed counts, material availability/reliability, and the exact source manifest from the six trusted Normalize inputs rather than trusting model JSON or Gate claims. `boundary_checks.facts` must contain exactly the 31 required fact names with no extras. Contradictory boundary facts fail closed. Gate-driven reroutes require same-source evidence overlap; independent Category 8 and Category 15 evidence may coexist. Nonempty material warnings, count/reliability warnings, or threshold recheck warnings propagate as `finalization_status=warning` and block rollout cutover pending review.

## Output_Validator and End

Change the Validator mapping as follows:

```text
judge_output        Live_Boundary_Finalizer.finalized_judge_output
finalization_status Live_Boundary_Finalizer.finalization_status
finalizer_errors    Live_Boundary_Finalizer.finalizer_errors
```

Both `finalization_status` and `finalizer_errors` are mandatory on the v3 Validator. Missing either—or both—fails validation as incomplete Finalizer metadata. Compatibility without these fields exists only on the separately retained v2 rollback path; do not use it as a v3 bridge.

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

## Commit-pinned rule URLs

The final local v3 rule pin is commit `27cbff1c51f3a71f40ce92a962446fa858cc2616`. Its remote raw URLs return 404 until an authorized push. After that push, verify HTTP 200 and expected contents before entering either immutable URL in the inactive canvas:

```text
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/27cbff1c51f3a71f40ce92a962446fa858cc2616/rules/live_ocean_lowquality_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/27cbff1c51f3a71f40ce92a962446fa858cc2616/rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Do not use mutable `main` raw URLs for the v3 rollout.

Keep the retained v2 rollback path pinned to commit `eac91fbdee39f3f38e6a84c4b7932aa42184cdeb`:

```text
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/eac91fbdee39f3f38e6a84c4b7932aa42184cdeb/rules/live_ocean_lowquality_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/eac91fbdee39f3f38e6a84c4b7932aa42184cdeb/rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

## Copy sources

Use these files when configuring Aicolate manually:

```text
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

## Safe preparation, cutover, and rollback

Continue one node per manual message. v3 remains unreleased throughout preparation.

0. Mandatory live-UI preflight: record the exact current `LowQuality_Judge` raw-text output field already wired to the v2 Validator, and record the actual Start Output-panel types of `ocean_segment_count` and `pearl_product_count`. Stop if any value is not confirmed; do not guess `output` versus `result` or either count type.
1. The final local v3 URLs at `27cbff1c51f3a71f40ce92a962446fa858cc2616` remain remote 404 until authorized push; after push, verify HTTP 200 and contents.
2. Retain or clone the complete active v2 path as rollback. Do not change `End`.
3. Configure inactive v3 `Rules_JSON` and `Judge_Rules_Compact` HTTP nodes with the pinned v3 SHA URLs.
4. Paste/update v3 `Rules_Brain` on the inactive path; keep its Output Panel unchanged.
5. Add `Live_Boundary_Gate_Builder` on the inactive path.
6. Update or create the v3 `LowQuality_Judge` prompts and inputs on the inactive path.
7. Add `Live_Boundary_Finalizer` on the inactive path.
8. Update or create the v3 `Output_Validator`; map `finalization_status`, `finalizer_errors`, and `judge_output` from `finalized_judge_output`.
9. Run the boundary smoke entirely on the inactive path. Do not connect it to `End` if any node, contract, version, HTTP, Finalizer, or Validator check fails.
10. Make one cutover change: switch `End` from the retained v2 Validator to the verified v3 Validator.
11. Rerun the 13 reviewed rooms before any metric claim or human approval.

Stop immediately before cutover if the live-UI preflight is incomplete, either pinned v3 URL is not HTTP 200 or has the wrong content/version, the retained v2 rollback path is incomplete, any of the 11 Finalizer inputs or required Code Node outputs is missing, versions disagree, or the inactive smoke has any error/non-pass result. A nonempty `boundary_builder_warnings`, trusted `material_quality_warning`, material reliability warning, or `threshold_recheck_warnings` requires review and blocks cutover even when the Finalizer/Validator status is `warning` rather than `fail`.

Rollback is a single `End` switch back to the retained v2 Validator. The rollback path must continue using the v2 pinned URLs above, the prior v2 `Rules_Brain`, the prior Judge prompt, and the prior Validator mapping. Retain this complete v2 path until a human approves the 13-room v3 rerun.

## Tests

Run the full repository suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Local tests verify deterministic assets and contracts only. They do not prove Aicolate deployment state or runtime metrics.
