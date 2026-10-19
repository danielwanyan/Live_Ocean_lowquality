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

Configure exactly these 8 Input Variables:

| Input Variable | Type | Source |
|---|---|---|
| `segments_json` | String | `Normalize_Input.segments_json` |
| `segment_count` | Integer | `Normalize_Input.segment_count` |
| `comment_interaction` | String | `Normalize_Input.comment_interaction` |
| `product_catalog_json` | String | `Normalize_Input.product_catalog_json` |
| `product_count` | Integer | `Normalize_Input.product_count` |
| `material_quality_warning` | String | `Normalize_Input.material_quality_warning` |
| `rules_version` | String | `Rules_Brain.rules_version` |
| `rules_warning` | String | `Rules_Brain.rules_warning` |

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

Configure exactly these 13 Text Input Variables:

```text
room_id
segments_json
segment_count
comment_interaction
product_catalog_json
product_count
material_quality_warning
rules_context
rules_version
judge_rules_compact             Judge_Rules_Compact.body
boundary_gate_panel             Live_Boundary_Gate_Builder.boundary_gate_panel
boundary_output_schema_json     Live_Boundary_Gate_Builder.boundary_output_schema_json
boundary_contract_version       Live_Boundary_Gate_Builder.boundary_contract_version
```

Vision inputs are unchanged:

```text
all_frame_urls                  Normalize_Input.all_frame_urls
all_product_image_urls          Normalize_Input.all_product_image_urls
```

The System Prompt is plain text. The compact User Prompt keeps `rules_context`, `judge_rules_compact`, and the boundary contract, while removing duplicate catalog/permission/priority/threshold injections and the expanded 31-fact/19-result all-false example.

The Judge output envelope is a Chinese human-review report followed by `FINAL_JSON:` and valid JSON; `raw_json_only` is `false`. Decision precedence is fixed:

1. Missing or unreliable required channel/material becomes `unable_to_judge`.
2. Required channels present but evidence below threshold becomes `no_hit`.
3. Disabled categories or forbidden-only evidence become `no_hit`, overriding missing-material handling.

Applicability is channel-specific: Category 3 requires reliable live Segment or Comment Interaction material; Category 6 requires reliable live frames; Category 10 requires a reliable live frame/ASR/visible-text channel plus Pearl title/image material. Missing a required group is `unable_to_judge`.

Category 9 permits concrete authenticity-deception evidence from any allowed live or Pearl material and remains distinct from Category 10. Category 10 requires a live Segment source proving generated content, an independent Pearl title/image source proving the bound product, a material mismatch comparison, and at least two distinct trusted sources. Category 5 still requires reliable live frames; product-promotion ASR without frames is `unable_to_judge`.

## Live_Boundary_Finalizer

Configure all 13 mandatory v3 inputs. The v3 path has no legacy bridge:

| Input Variable | Type | Source |
|---|---|---|
| `judge_output` | String | Select the exact current raw-text field already wired from `LowQuality_Judge` to the old Validator in the live UI; do not guess `output` versus `result` |
| `boundary_gates_json` | String | `Live_Boundary_Gate_Builder.boundary_gates_json` |
| `boundary_contract_version` | String | `Live_Boundary_Gate_Builder.boundary_contract_version` |
| `rules_version` | String | `Rules_Brain.rules_version` |
| `rules_warning` | String | `Rules_Brain.rules_warning` |
| `room_id` | String | `Normalize_Input.room_id` |
| `segments_json` | String | `Normalize_Input.segments_json` |
| `segment_count` | Integer | `Normalize_Input.segment_count` |
| `comment_interaction` | String | `Normalize_Input.comment_interaction` |
| `product_catalog_json` | String | `Normalize_Input.product_catalog_json` |
| `product_count` | Integer | `Normalize_Input.product_count` |
| `material_quality_warning` | String | `Normalize_Input.material_quality_warning` |
| `boundary_builder_warnings` | String | `Live_Boundary_Gate_Builder.boundary_builder_warnings` |

Declare exactly these five Output Panel fields; every field is `String`:

```text
finalized_judge_output: String
finalized_final_json: String
finalization_status: String
boundary_override_log: String
finalizer_errors: String
```

The Finalizer rebuilds `material_summary`, observed counts, material availability/reliability, the exact source manifest, and expected builder warnings from trusted Normalize and Rules Brain inputs rather than trusting model JSON or Gate claims. It rejects any mismatch between the reconstructed builder warnings, the Gate JSON root, and `boundary_builder_warnings`. `boundary_checks.facts` must contain exactly the 31 required fact names with no extras. Contradictory boundary facts fail closed. Gate-driven reroutes require same-source evidence overlap, including Category 19 to Category 1; independent Category 8 and Category 15 evidence may coexist. Nonempty Rules Brain warnings, Gate Builder warnings, material warnings, count/reliability warnings, or threshold recheck warnings propagate as `finalization_status=warning` and block rollout cutover pending review.

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

## Stable main rule URLs

Per the maintained Aicolate contract, the workflow uses stable `main` URLs so future verified rule pushes do not require manual URL edits. Both main URLs were verified HTTP 200 and byte-identical to the locally tested v3 assets on 2026-10-19:

```text
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Only push validated, synchronized rule assets to `main`. Rules_Brain version validation and downstream warning propagation block a mismatched update.

Keep the retained v2 rollback path pinned to commit `eac91fbdee39f3f38e6a84c4b7932aa42184cdeb` in the same repository:

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

0. Use the documented Start and Normalize contracts directly; no user screenshot is required. When configuring Finalizer, reuse the existing Judge raw-text mapping already selected by the retained v2 Validator.
1. Use the two main URL values above; both are verified HTTP 200 and currently return the v3 contract.
2. Retain or clone the complete active v2 path as rollback. Do not change `End`.
3. Configure inactive v3 `Rules_JSON` and `Judge_Rules_Compact` HTTP nodes with the maintained main URL values.
4. Paste/update v3 `Rules_Brain` on the inactive path; keep its Output Panel unchanged.
5. Add `Live_Boundary_Gate_Builder` on the inactive path.
6. Update or create the v3 `LowQuality_Judge` prompts and inputs on the inactive path.
7. Add `Live_Boundary_Finalizer` on the inactive path.
8. Update or create the v3 `Output_Validator`; map `finalization_status`, `finalizer_errors`, and `judge_output` from `finalized_judge_output`.
9. Run the boundary smoke entirely on the inactive path. Do not connect it to `End` if any node, contract, version, HTTP, Finalizer, or Validator check fails.
10. Make one cutover change: switch `End` from the retained v2 Validator to the verified v3 Validator.
11. Rerun the 13 reviewed rooms before any metric claim or human approval.

Stop immediately before cutover if either main URL is not HTTP 200 or has the wrong content/version, the retained v2 rollback path is incomplete, any of the 13 Finalizer inputs or required Code Node outputs is missing, versions disagree, or the inactive smoke has any error/non-pass result. A nonempty `rules_warning`, `boundary_builder_warnings`, trusted `material_quality_warning`, material reliability warning, or `threshold_recheck_warnings` requires review and blocks cutover even when the Finalizer/Validator status is `warning` rather than `fail`.

Rollback is a single `End` switch back to the retained v2 Validator. The rollback path must continue using the v2 pinned URLs above, the prior v2 `Rules_Brain`, the prior Judge prompt, and the prior Validator mapping. Retain this complete v2 path until a human approves the 13-room v3 rerun.

## Tests

Run the full repository suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Local tests verify deterministic assets and contracts only. They do not prove Aicolate deployment state or runtime metrics.
