from __future__ import annotations

import json
import re
from typing import Any, Dict, List


Output = Dict[str, Any]


class Args:
    params: Dict[str, Any]


SEGMENT_HEADER_RE = re.compile(r"Segment\s*#(\d+)\s*\[([^\]]+)\]:\s*", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s;]+")
SUMMARY_MARKERS = {
    "评论互动": {"数据变化", "执行时间"},
    "Comment Interaction": {"Data Analysis", "执行时间"},
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _parse_int(value: Any) -> int | None:
    text = _text(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _non_empty_lines(value: Any) -> List[str]:
    return [line.strip() for line in _text(value).splitlines() if line.strip()]


def _split_semicolon_urls(value: str) -> List[str]:
    return [item.strip() for item in URL_RE.findall(value)]


def _parse_segment_blocks(value: Any) -> Dict[int, Dict[str, Any]]:
    text = _text(value)
    matches = list(SEGMENT_HEADER_RE.finditer(text))
    blocks: Dict[int, Dict[str, Any]] = {}

    for position, match in enumerate(matches):
        next_start = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        segment_index = int(match.group(1))
        blocks[segment_index] = {
            "segment_index": segment_index,
            "time_range": match.group(2).strip(),
            "content": text[match.end() : next_start].strip(),
        }

    return blocks


def _extract_comment_interaction(summary: Any) -> str:
    lines = _text(summary).splitlines()

    for start_marker, end_markers in SUMMARY_MARKERS.items():
        for index, line in enumerate(lines):
            if line.strip() != start_marker:
                continue

            section_lines: List[str] = []
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if stripped in end_markers:
                    break
                section_lines.append(candidate)

            return "\n".join(section_lines).strip()

    return ""


def _build_segments(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    asr_blocks = _parse_segment_blocks(params.get("ocean_segment_ASR", ""))
    frame_blocks = _parse_segment_blocks(params.get("ocean_segment_frame_urls", ""))
    segment_indexes = sorted(set(asr_blocks) | set(frame_blocks))

    segments: List[Dict[str, Any]] = []
    for segment_index in segment_indexes:
        asr_block = asr_blocks.get(segment_index, {})
        frame_block = frame_blocks.get(segment_index, {})
        frame_content = _text(frame_block.get("content", ""))
        segments.append(
            {
                "segment_index": segment_index,
                "time_range": _text(asr_block.get("time_range") or frame_block.get("time_range", "")),
                "asr_summary": _text(asr_block.get("content", "")),
                "frame_urls": _split_semicolon_urls(frame_content),
                "source_labels": ["ocean_segment_ASR", "ocean_segment_frame_urls"],
            }
        )

    return segments


def _build_product_catalog(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    product_ids = _non_empty_lines(params.get("pearl_product_ids", ""))
    product_titles = _non_empty_lines(params.get("pearl_product_titles", ""))
    image_lines = _non_empty_lines(params.get("pearl_product_images", ""))
    product_total = max(len(product_ids), len(product_titles), len(image_lines))

    products: List[Dict[str, Any]] = []
    for index in range(product_total):
        products.append(
            {
                "product_index": index + 1,
                "product_id": product_ids[index] if index < len(product_ids) else "",
                "title": product_titles[index] if index < len(product_titles) else "",
                "image_urls": _split_semicolon_urls(image_lines[index]) if index < len(image_lines) else [],
            }
        )

    return products


def _build_warnings(
    params: Dict[str, Any],
    segments: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    comment_interaction: str,
) -> List[str]:
    warnings: List[str] = []
    expected_segment_count = _parse_int(params.get("ocean_segment_count", ""))
    expected_product_count = _parse_int(params.get("pearl_product_count", ""))

    if expected_segment_count is not None and expected_segment_count != len(segments):
        warnings.append(f"segment_count_mismatch_expected_{expected_segment_count}_parsed_{len(segments)}")

    for segment in segments:
        if not segment["asr_summary"]:
            warnings.append(f"segment_{segment['segment_index']}_asr_missing")
        if not segment["frame_urls"]:
            warnings.append(f"segment_{segment['segment_index']}_frame_urls_missing")

    if not comment_interaction:
        warnings.append("comment_interaction_missing")

    if expected_product_count is not None and expected_product_count != len(products):
        warnings.append(f"product_count_mismatch_expected_{expected_product_count}_parsed_{len(products)}")

    if not products:
        warnings.append("product_catalog_missing")

    return warnings


def _debug_input_shape(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "keys": sorted(params.keys()),
        "field_lengths": {key: len(_text(value)) for key, value in sorted(params.items())},
    }


def build_normalized_output(params: Dict[str, Any]) -> Output:
    segments = _build_segments(params)
    products = _build_product_catalog(params)
    comment_interaction = _extract_comment_interaction(params.get("ocean_summary", ""))
    warnings = _build_warnings(params, segments, products, comment_interaction)

    return {
        "room_id": _text(params.get("room_id", "")),
        "segment_count": len(segments),
        "segments_json": json.dumps(segments, ensure_ascii=False),
        "comment_interaction": comment_interaction,
        "product_count": len(products),
        "product_catalog_json": json.dumps(products, ensure_ascii=False),
        "material_quality_warning": json.dumps(warnings, ensure_ascii=False),
        "debug_input_shape": json.dumps(_debug_input_shape(params), ensure_ascii=False),
    }


async def main(args: Args) -> Output:
    return build_normalized_output(args.params)
