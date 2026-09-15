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
