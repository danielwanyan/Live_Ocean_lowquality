import json
import re


PRODUCT_IMAGE_ALLOWED_IDS = [3, 5, 6, 9, 10, 12, 15, 16, 17, 19]

FALLBACK_CATEGORIES = [
    {"category_id": 1, "category_name": "色情低俗低质问题", "english_key": "sexual_vulgar", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Any segment frame or segment ASR evidence shows listed sexualized exposure or sexualized behavior."},
    {"category_id": 2, "category_name": "恶心恐怖低质问题", "english_key": "disgusting_horror", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Any segment frame or segment ASR evidence shows disgusting or horror content over threshold and no active cleaning exemption."},
    {"category_id": 3, "category_name": "商品无关低质问题", "english_key": "product_unrelated", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Sustained pattern across available segments shows live core content unrelated to bound products and lacks sustained product promotion."},
    {"category_id": 4, "category_name": "无互动低质问题", "english_key": "no_interaction", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "Most available segment ASR evidence, supported by comment_interaction when available, shows both no product promotion and no host-audience interaction."},
    {"category_id": 5, "category_name": "无实物商品展示低质问题", "english_key": "no_physical_product_display", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Most available segment frame groups show no real physical display of the bound product."},
    {"category_id": 6, "category_name": "商品描述不详细低质问题", "english_key": "product_description_not_detailed", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Clear promotion exists, but recurring segment evidence shows low-information product explanation."},
    {"category_id": 7, "category_name": "静态帧遮挡低质问题", "english_key": "static_frame_occlusion", "allowed_materials": ["segment_frame"], "product_image_allowed": False, "trigger_threshold": "Any segment frame has an occlusion or interruption layer covering at least 80% of the live screen."},
    {"category_id": 8, "category_name": "非母语违规低质问题", "english_key": "non_native_language_violation", "allowed_materials": ["segment_asr", "segment_frame_visible_text"], "product_image_allowed": False, "trigger_threshold": "Hit only when segment ASR or visible text in segment frames contains Chinese/CJK used in product promotion, Chinglish, incomprehensible English, or severely broken English that prevents normal product understanding."},
    {"category_id": 9, "category_name": "AIGC真实性低质问题", "english_key": "aigc_authenticity", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Any segment frame, segment ASR, visible frame text, or Pearl product evidence shows AIGC-generated content used for product promotion that misleads authenticity or differs from bound physical product."},
    {"category_id": 10, "category_name": "AIGC商品展示低质问题", "english_key": "aigc_product_display", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Any segment frame, segment ASR, visible frame text, or Pearl product evidence shows rendered/generated product or use scene with exaggerated size/style/effect compared with the bound real product."},
    {"category_id": 11, "category_name": "录播回放低质问题", "english_key": "replay_recorded_content", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Clear replay, loop, or pre-recorded indicators are present. Browser, desktop, card-list, or spin UI alone is not enough in card-opening or lottery-like rooms."},
    {"category_id": 12, "category_name": "功能效果虚假宣传低质问题", "english_key": "false_function_effect_claim", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Any segment frame, segment ASR, or Pearl product evidence shows exaggerated or unreliable product function/effect likely to mislead consumers."},
    {"category_id": 13, "category_name": "危险行为低质问题", "english_key": "dangerous_behavior", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "At least 2 segment frame or segment ASR evidence units show life-threatening violent behavior or dangerous goods demonstration."},
    {"category_id": 14, "category_name": "站外引流交易低质问题", "english_key": "off_platform_transaction", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "Same scene has both off-platform payment/account/site/app info and explicit transaction guidance."},
    {"category_id": 15, "category_name": "违法违规商品低质问题", "english_key": "illegal_prohibited_goods", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "At least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show prohibited goods, counterfeit, imitation, inferior product, or missing qualification claim tied to bound product."},
    {"category_id": 16, "category_name": "政治敏感低质问题", "english_key": "politically_sensitive", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "At least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show political controversy, political symbols, political hate symbols, racial discrimination, or polarized political narratives."},
    {"category_id": 17, "category_name": "争议话题低质问题", "english_key": "controversial_topic", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "At least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show sensitive religion, racial discrimination, moral boundary, LGBT, or similarly high-conflict socio-cultural themes."},
    {"category_id": 18, "category_name": "负面引导低质问题", "english_key": "negative_guidance", "allowed_materials": ["segment_frame", "segment_asr", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "At least 2 segment frame, segment ASR, or Comment Interaction evidence units show persistent negative emotional guidance, hostile comparison, resentment, anxiety induction, or purchase-pressure emotion."},
    {"category_id": 19, "category_name": "隐私敏感商品低质问题", "english_key": "privacy_sensitive_product", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "At least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show intimate, gender-specific, or private-use non-pornographic product tied to bound product."},
]

FALLBACK_RULES = {
    "version": "fallback-2026-09-15-v1",
    "fixed_category_count": 19,
    "product_image_allowed_category_ids": PRODUCT_IMAGE_ALLOWED_IDS,
    "exclusive_priority_rules": [
        {
            "id": "priority_3_over_6",
            "rule_en": "If live content is unrelated to bound products and lacks sustained promotion, category 3 has priority over category 6.",
        },
        {
            "id": "priority_1_over_19",
            "rule_en": "Sexual exposure or sexualized implication belongs to category 1, not category 19.",
        },
    ],
    "categories": FALLBACK_CATEGORIES,
}


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_json(value, fallback):
    if isinstance(value, (dict, list)):
        return value
    text = _text(value)
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _unwrap_body(value):
    if isinstance(value, dict):
        for key in ("body", "Body", "data", "content", "output"):
            if key in value:
                return _unwrap_body(value.get(key))
    return value


def _find_param(params, names):
    for name in names:
        if name in params:
            return params.get(name)
    for value in params.values():
        if isinstance(value, dict):
            found = _find_param(value, names)
            if found is not None:
                return found
    return None


def _parse_json_array(value):
    parsed = _parse_json(_unwrap_body(value), [])
    return parsed if isinstance(parsed, list) else []


def _load_rules(params):
    raw_rules = _unwrap_body(_find_param(params, ("rules_json", "Rules_JSON", "rules_body")))
    parsed = _parse_json(raw_rules, None)
    if not isinstance(parsed, dict):
        return FALLBACK_RULES, "rules_json parse failed; using fallback"
    if not isinstance(parsed.get("categories"), list):
        return FALLBACK_RULES, "rules_json missing categories list; using fallback"
    return parsed, ""


def _has_cjk(text):
    return re.search(r"[\u4e00-\u9fff]", text or "") is not None


def _collect_material_text(params):
    values = []
    for segment in _parse_json_array(_find_param(params, ("segments_json", "Segments_JSON"))):
        if not isinstance(segment, dict):
            continue
        segment_index = segment.get("segment_index", "")
        asr_summary = _text(segment.get("asr_summary"))
        if asr_summary:
            values.append(f"Segment #{segment_index} ASR: {asr_summary}")
    comment_interaction = _text(_find_param(params, ("comment_interaction", "Comment_Interaction")))
    if comment_interaction:
        values.append(f"Comment Interaction: {comment_interaction}")
    for product in _parse_json_array(_find_param(params, ("product_catalog_json", "Product_Catalog_JSON"))):
        if not isinstance(product, dict):
            continue
        title = _text(product.get("title"))
        if title:
            values.append(f"Pearl product #{product.get('product_index', '')}: {title}")
    return "\n".join(values)


def _count_product_images(params):
    count = 0
    for product in _parse_json_array(_find_param(params, ("product_catalog_json", "Product_Catalog_JSON"))):
        if not isinstance(product, dict):
            continue
        image_urls = product.get("image_urls", [])
        if isinstance(image_urls, list):
            count += len([url for url in image_urls if isinstance(url, str) and url.strip()])
    return count


def _collect_material_warnings(params):
    return [str(item) for item in _parse_json_array(_find_param(params, ("material_quality_warning", "Material_Quality_Warning")))]


def _build_category_catalog(categories):
    return [
        {
            "category_id": item.get("category_id"),
            "category_name": item.get("category_name"),
            "english_key": item.get("english_key", ""),
            "allowed_materials": item.get("allowed_materials", []),
            "product_image_allowed": bool(item.get("product_image_allowed")),
            "trigger_threshold": item.get("trigger_threshold", ""),
        }
        for item in categories
    ]


def _build_permission_matrix(rules):
    allowed_ids = rules.get("product_image_allowed_category_ids", PRODUCT_IMAGE_ALLOWED_IDS)
    return {
        "allowed_category_ids": allowed_ids,
        "forbidden_category_ids": [idx for idx in range(1, 20) if idx not in allowed_ids],
        "rule": "Product images may only be used for allowed_category_ids.",
    }


def _build_priority_context(rules):
    lines = []
    for rule in rules.get("exclusive_priority_rules", []):
        rule_id = rule.get("id", "")
        text = rule.get("rule_en") or rule.get("rule") or rule.get("rule_zh") or ""
        lines.append(f"{rule_id}: {text}")
    return "\n".join(lines)


def _build_threshold_context(categories):
    return "\n".join(
        f"Category {item.get('category_id')} {item.get('category_name')}: {item.get('trigger_threshold', '')}"
        for item in categories
    )


def _build_dynamic_context(params, rules, rules_warning):
    text = _collect_material_text(params)
    product_image_count = _count_product_images(params)
    material_warnings = _collect_material_warnings(params)
    lower = text.lower()
    lines = [
        f"Rules version: {rules.get('version', '')}",
        "All 19 categories must be checked. Do not omit, merge, rename, skip, or reorder categories.",
        "Use all available Ocean segments. Do not convert the input into a fixed-size sample.",
        "Only the provided comment_interaction field from ocean_summary may be used. Other ocean_summary sections are excluded.",
        "Every hit requires concrete evidence from allowed materials and a source label.",
        "Product image permission: product images may only be used by categories 3,5,6,9,10,12,15,16,17,19.",
        "Priority: Category 3 product_unrelated overrides Category 6 product_description_not_detailed when there is no clear sustained product promotion intent.",
        "Priority: Category 1 sexual_vulgar overrides Category 19 privacy_sensitive_product for sexualized exposure or implication.",
    ]
    if rules_warning:
        lines.append(f"Rules warning: {rules_warning}")
    if material_warnings:
        lines.append("Material warnings: " + "; ".join(material_warnings))
    if product_image_count == 0:
        lines.append("Product catalog is missing or contains no product images. Do not make product-image-dependent judgments without sufficient evidence.")
    if _has_cjk(text):
        lines.append("Category 8 attention: ASR/comment/product text contains CJK characters. Apply EU language guard and product-promotion context before any hit.")
    if any(term in lower for term in ("paypal", "venmo", "whatsapp", "qr", ".com", ".net", "payment", "link")):
        lines.append("Category 14 attention: possible off-platform transaction signal. Hit requires BOTH payment/off-platform info AND explicit transaction guidance in the same scene.")
    if any(term in lower for term in ("ai", "aigc", "digital human", "virtual", "generated")):
        lines.append("Category 9/10 attention: possible AIGC signal. Distinguish authenticity misleading from generated product display mismatch.")
    if any(term in lower for term in ("freespin", "gold ticket", "booster", "display", "ticket", "spin", "auction")):
        lines.append("Commerce context note: ASR/comment mentions tickets, boosters, spins, or auction mechanics. Apply only listed live-low-quality categories and evidence thresholds.")
    return "\n".join(lines)


def build_rules_brain_output(params):
    rules, warning = _load_rules(params)
    categories = rules.get("categories", [])
    catalog = _build_category_catalog(categories)
    permission_matrix = _build_permission_matrix(rules)
    category_ids = [item.get("category_id") for item in catalog]
    category_integrity = "ok" if len(catalog) == 19 and category_ids == list(range(1, 20)) else "invalid"
    permission_check = "ok" if permission_matrix["allowed_category_ids"] == PRODUCT_IMAGE_ALLOWED_IDS else "invalid"
    return {
        "rules_context": _build_dynamic_context(params, rules, warning),
        "category_catalog": json.dumps(catalog, ensure_ascii=False),
        "product_image_permission_matrix": json.dumps(permission_matrix, ensure_ascii=False),
        "priority_rules_context": _build_priority_context(rules),
        "threshold_rules_context": _build_threshold_context(categories),
        "rules_version": str(rules.get("version", "")),
        "rules_warning": warning,
        "category_count": len(catalog),
        "category_integrity_check": category_integrity,
        "permission_matrix_check": permission_check,
    }


async def main(args: Args) -> Output:
    params = args.params
    return build_rules_brain_output(params)
