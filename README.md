# Live Ocean Low Quality

This repository contains Aicolate assets for live-room low-quality detection using Ocean and Pearl materials supplied directly by the Start node.

## Workflow

```text
Start
  -> Normalize_Input Code
  -> Rules_JSON HTTP + Judge_Rules_Compact HTTP
  -> Rules_Brain Code
  -> LowQuality_Judge LLM
  -> Output_Validator Code
```

## Start Inputs

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

## Rule Raw URLs

```text
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/Live_Ocean_lowquality/main/rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Verify the raw URLs after every rules push.

## Copy Sources

Use these files when configuring Aicolate manually:

```text
scripts/normalize_input_node.py
scripts/rules_brain_node.py
scripts/output_validator_node.py
prompts/lowquality_judge_system_prompt_v1.txt
prompts/lowquality_judge_user_prompt_v1.txt
rules/live_ocean_lowquality_rules_structured_v1.json
rules/live_ocean_lowquality_judge_rules_compact_v1.txt
```

Durable project documentation is maintained in:

```text
/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/live-ocean-lowquality/
```

## Aicolate Notes

- `Normalize_Input` must expose all returned keys in the Output panel.
- Downstream nodes must map returned fields again in Input Variables.
- `all_frame_urls` and `all_product_image_urls` are flat URL arrays intended for the LLM node Vision Inputs.
- `ocean_summary` is restricted to the `评论互动` or `Comment Interaction` section.
- The final workflow must be validated by running real cases in Aicolate after manual canvas setup.
