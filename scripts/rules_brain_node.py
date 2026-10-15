import json
import re


BOUNDARY_CONTRACT_VERSION = "2026-10-15-v3-cross-project-boundary-gates"
PRODUCT_IMAGE_ALLOWED_IDS = [3, 5, 6, 9, 10, 12, 15, 16, 17]

FALLBACK_CATEGORIES = [
    {"category_id": 1, "category_name": "色情低俗低质问题", "english_key": "sexual_vulgar", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Any segment frame or segment ASR evidence hits the listed visual or speech scenario."},
    {"category_id": 2, "category_name": "恶心恐怖低质问题", "english_key": "disgusting_horror", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Hit only when the dominant content creates strong discomfort through qualifying disgusting or horror material. Cleaning and novelty/product art, calendar, or packaging contexts are hard-exempt."},
    {"category_id": 3, "category_name": "商品无关低质问题", "english_key": "product_unrelated", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit only when a sustained unrelated core dominates across available segments and there is no sustained promotion of bound products. A short opening or off-topic passage followed by a later substantive product demonstration is clean."},
    {"category_id": 4, "category_name": "无互动低质问题", "english_key": "no_interaction", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "Hit when most available segment ASR evidence, supported by comment_interaction when available, shows both no product promotion and no host-audience interaction. Do not use a fixed ratio threshold from the old workflow."},
    {"category_id": 5, "category_name": "无实物商品展示低质问题", "english_key": "no_physical_product_display", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit when most available segment frame groups show no real physical video display of the bound product: only sticker/cutout/photo/screenshot/static image, product card, small product thumbnail/overlay, no product, or only unrecognizable partial product. A real package, wearing, installation, operation, or application/use counts as physical display."},
    {"category_id": 6, "category_name": "商品描述不详细低质问题", "english_key": "product_description_not_detailed", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit only when clear product promotion exists and most relevant promotion remains extremely low-information after considering all available segments. An identifiable product or package plus its core purpose, or any core buying fact, blocks category 6. Do not require deep ingredient detail or mechanism explanation."},
    {"category_id": 7, "category_name": "静态帧遮挡低质问题", "english_key": "static_frame_occlusion", "allowed_materials": ["segment_frame"], "product_image_allowed": False, "trigger_threshold": "Any segment frame group shows an occlusion/interruption layer covering at least 80% of the live screen and seriously blocking viewing."},
    {"category_id": 8, "category_name": "非母语违规低质问题", "english_key": "non_native_language_violation", "allowed_materials": ["segment_asr", "segment_frame_visible_text"], "product_image_allowed": False, "trigger_threshold": "Hit only when segment ASR or visible text in segment frames uses a language that is not acceptable for the target market, Chinese/CJK in product promotion, Chinglish, incomprehensible English, or severely broken English, and this prevents normal product understanding across the live. Product mismatch, ethnic clothing style, non-English product titles, or OCR noise alone is not a language hit."},
    {"category_id": 9, "category_name": "AIGC真实性低质问题", "english_key": "aigc_authenticity", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit only when explicit generated-content evidence is present and its use in product promotion is authenticity misleading. AI-like style alone is insufficient."},
    {"category_id": 10, "category_name": "AIGC商品展示低质问题", "english_key": "aigc_product_display", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit only with explicit generated product or use-scene evidence plus a material mismatch in product size, style, function, use, or effect against the bound real product. AI-like style alone is insufficient."},
    {"category_id": 11, "category_name": "录播回放低质问题", "english_key": "replay_recorded_content", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Any segment frame or segment ASR evidence shows clear replay/loop/pre-recorded indicators such as replay/loop labels, playback controls, video timeline, repeated sequence, abnormal jump, black/green screen, nested screen with clear replay/loop/pre-recorded feature, or segment ASR directly mentioning replay/loop playback. Browser, desktop, card-list, or spin UI alone in card-opening or lottery-like live rooms is not enough."},
    {"category_id": 12, "category_name": "功能效果虚假宣传低质问题", "english_key": "false_function_effect_claim", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Hit only when a concrete LIVE frame or ASR claim has a materially misleading basis and meets the current prevalence/strength threshold: at least half of relevant effective live promotion or repeated strong evidence. A Pearl product image is corroborative only and cannot independently create a hit."},
    {"category_id": 13, "category_name": "危险行为低质问题", "english_key": "dangerous_behavior", "allowed_materials": ["segment_frame", "segment_asr"], "product_image_allowed": False, "trigger_threshold": "Cumulative at least 2 segment frame or segment ASR evidence units show life-threatening violent behavior or dangerous goods demonstration, including heavy-smoke products creating fire illusion."},
    {"category_id": 14, "category_name": "站外引流交易低质问题", "english_key": "off_platform_transaction", "allowed_materials": ["segment_frame", "segment_asr", "segment_frame_visible_text", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "Hit only when the same scene contains both an off-platform destination/payment/account/site/app and explicit transaction guidance, with no exemption."},
    {"category_id": 15, "category_name": "违法违规商品低质问题", "english_key": "illegal_prohibited_goods", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Independent prohibited, counterfeit/imitation/inferior, jailbreak/device-modification, qualification, and other non-IPP subtypes retain their cumulative at least 2 evidence threshold. IPP specifically requires live promoted item evidence plus bound product evidence and a core entity/category/use/quantity/spec contradiction."},
    {"category_id": 16, "category_name": "政治敏感低质问题", "english_key": "politically_sensitive", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Cumulative at least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show political controversy, sensitive political symbols/movements, political hate symbols, racial discrimination, or polarized political narratives."},
    {"category_id": 17, "category_name": "争议话题低质问题", "english_key": "controversial_topic", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": True, "trigger_threshold": "Cumulative at least 2 segment frame, segment ASR, Pearl product title, or Pearl product image evidence units show sensitive topics related to religion, racial discrimination, moral boundary, LGBT, or similarly high-conflict socio-cultural themes."},
    {"category_id": 18, "category_name": "负面引导低质问题", "english_key": "negative_guidance", "allowed_materials": ["segment_frame", "segment_asr", "comment_interaction"], "product_image_allowed": False, "trigger_threshold": "Cumulative at least 2 segment frame, segment ASR, or Comment Interaction evidence units show sustained negative emotional guidance such as hostile arguments with viewers, insults, resentment, jealousy, anxiety/fear induction beyond routine sales, wealth flaunting or comparison pressure, or content likely to trigger negative emotion. Routine commercial urgency alone does not hit."},
    {"category_id": 19, "category_name": "隐私敏感商品低质问题", "english_key": "privacy_sensitive_product", "allowed_materials": ["segment_frame", "segment_asr", "pearl_product_title", "pearl_product_image"], "product_image_allowed": False, "trigger_threshold": "Disabled for current Live Ocean Low Quality calibration. Always return no_hit for this category unless future policy explicitly re-enables it. Do not identify sanitary products, underwear, gender-specific care, or private-use non-pornographic products under category 19 in this workflow version."},
]

FALLBACK_RULES = {
    "version": BOUNDARY_CONTRACT_VERSION,
    "boundary_contract_version": BOUNDARY_CONTRACT_VERSION,
    "fixed_category_count": 19,
    "product_image_allowed_category_ids": PRODUCT_IMAGE_ALLOWED_IDS,
    "exclusive_priority_rules": [
        {
            "id": "priority_3_over_5_for_unrelated_content",
            "higher_priority_category_id": 3,
            "lower_priority_category_id": 5,
            "rule_en": "If the unrelated live core has no sustained promotion, classify as category 3, not category 5.",
            "rule_zh": "若直播核心内容与商品无关且没有持续商品推广，应判定【商品无关低质问题】（类别3），而非【无实物商品展示低质问题】（类别5）。",
        },
        {
            "id": "priority_3_over_6",
            "higher_priority_category_id": 3,
            "lower_priority_category_id": 6,
            "rule_en": "If there is no clear sustained product promotion, explanation, or demonstration intent, including long periods with no pinned product, no product talk, sports/game/life-chat as the core content, classify as category 3 and do not classify as category 6.",
            "rule_zh": "若直播内容无明确、持续的商品推广、讲解、演示行为，核心内容与绑定商品无任何关联，或长时间不挂品/不讲品/只直播比赛、聊天、个人生活，一律优先判定为【商品无关低质问题】，不得改判为【商品描述不详细低质问题】。",
        },
        {
            "id": "priority_1_over_19",
            "higher_priority_category_id": 1,
            "lower_priority_category_id": 19,
            "rule_en": "Sexual exposure or sexualized implication belongs to category 1, not category 19.",
            "rule_zh": "色情暴露、性暗示类内容归为【色情低俗低质问题】，不得同时归为【隐私敏感商品低质问题】。",
        },
        {
            "id": "priority_15_over_8_for_product_mismatch",
            "higher_priority_category_id": 15,
            "lower_priority_category_id": 8,
            "rule_en": "When the core issue is a clear entity/category/use-case mismatch between the live displayed item and bound Pearl product, route it to category 15 product-mismatch/IPP boundary, not category 8 language violation.",
            "rule_zh": "若问题本质是直播展示商品与挂车商品/商品图在实体、类目、用途上明显不一致，优先按【违法违规商品低质问题】中的货不对板/IPP 边界判断，不得因为商品图语言、异域服饰、OCR 文本或标题语言而判为【非母语违规低质问题】。",
        },
        {
            "id": "priority_5_over_6_for_no_physical_display",
            "higher_priority_category_id": 5,
            "lower_priority_category_id": 6,
            "rule_en": "If product talk exists but most live frames lack real physical video display of the bound product and show only stickers, screenshots, product cards, static photos, overlays, or unrecognizable partials, classify category 5 before category 6.",
            "rule_zh": "若主播围绕商品说话但直播画面长期没有真实实物视频展示，只出现贴图、截图、商品卡、静态照片、产品角标或不可识别局部，优先判定【无实物商品展示低质问题】，不得仅因讲解信息少而判定【商品描述不详细低质问题】。",
        },
    ],
    "categories": FALLBACK_CATEGORIES,
}

CATEGORY_CONTRACT_FIELDS = (
    "category_name",
    "english_key",
    "allowed_materials",
    "product_image_allowed",
    "trigger_threshold",
)

EXPECTED_PRIORITY_MAPPINGS = {
    "priority_3_over_5_for_unrelated_content": (3, 5),
    "priority_3_over_6": (3, 6),
    "priority_5_over_6_for_no_physical_display": (5, 6),
    "priority_15_over_8_for_product_mismatch": (15, 8),
    "priority_1_over_19": (1, 19),
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


def _validate_rules_contract(rules):
    if rules.get("version") != BOUNDARY_CONTRACT_VERSION:
        return "version mismatch"
    if rules.get("boundary_contract_version") != BOUNDARY_CONTRACT_VERSION:
        return "boundary_contract_version mismatch"
    if type(rules.get("fixed_category_count")) is not int or rules.get("fixed_category_count") != 19:
        return "fixed_category_count must be 19"

    allowed_ids = rules.get("product_image_allowed_category_ids")
    if type(allowed_ids) is not list or allowed_ids != PRODUCT_IMAGE_ALLOWED_IDS:
        return "product_image_allowed_category_ids mismatch"
    if any(type(category_id) is not int for category_id in allowed_ids):
        return "product_image_allowed_category_ids must contain integers"

    categories = rules.get("categories")
    if type(categories) is not list or len(categories) != 19:
        return "categories must contain exactly 19 items"
    for index, (category, canonical) in enumerate(
        zip(categories, FALLBACK_CATEGORIES), start=1
    ):
        if type(category) is not dict:
            return "category %d must be an object" % index
        if type(category.get("category_id")) is not int or category.get("category_id") != index:
            return "category IDs must be ordered 1..19"
        for field in CATEGORY_CONTRACT_FIELDS:
            if field not in category:
                return "category %d missing %s" % (index, field)
            if field == "product_image_allowed" and type(category.get(field)) is not bool:
                return "category %d product_image_allowed must be boolean" % index
            if field == "allowed_materials" and type(category.get(field)) is not list:
                return "category %d allowed_materials must be a list" % index
            if category.get(field) != canonical.get(field):
                return "category %d %s mismatch" % (index, field)

    priority_rules = rules.get("exclusive_priority_rules")
    if type(priority_rules) is not list or len(priority_rules) != len(EXPECTED_PRIORITY_MAPPINGS):
        return "exclusive priority rules must contain exactly five items"
    canonical_priorities = {
        priority["id"]: priority
        for priority in FALLBACK_RULES["exclusive_priority_rules"]
    }
    seen_priority_ids = set()
    for priority in priority_rules:
        if type(priority) is not dict:
            return "exclusive priority rule must be an object"
        rule_id = priority.get("id")
        if type(rule_id) is not str or rule_id in seen_priority_ids:
            return "exclusive priority rule IDs must be unique strings"
        canonical = canonical_priorities.get(rule_id)
        if canonical is None:
            return "exclusive priority IDs mismatch"
        for field in (
            "higher_priority_category_id",
            "lower_priority_category_id",
            "rule_en",
            "rule_zh",
        ):
            if field not in priority or priority.get(field) != canonical.get(field):
                return "exclusive priority %s %s mismatch" % (rule_id, field)
        if type(priority.get("higher_priority_category_id")) is not int:
            return "exclusive priority mappings must use integer category IDs"
        if type(priority.get("lower_priority_category_id")) is not int:
            return "exclusive priority mappings must use integer category IDs"
        if type(priority.get("rule_en")) is not str or type(priority.get("rule_zh")) is not str:
            return "exclusive priority instructions must be strings"
        seen_priority_ids.add(rule_id)
    if seen_priority_ids != set(EXPECTED_PRIORITY_MAPPINGS):
        return "exclusive priority IDs mismatch"
    return ""


def _fallback_warning(reason):
    return "invalid v3 rules contract: %s; using fallback" % reason


def _load_rules(params):
    raw_rules = _unwrap_body(_find_param(params, ("rules_json", "Rules_JSON", "rules_body")))
    parsed = _parse_json(raw_rules, None)
    if not isinstance(parsed, dict):
        return FALLBACK_RULES, _fallback_warning("rules_json parse failed")
    invalid_reason = _validate_rules_contract(parsed)
    if invalid_reason:
        return FALLBACK_RULES, _fallback_warning(invalid_reason)
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
        f"Boundary contract version: {BOUNDARY_CONTRACT_VERSION}",
        "All 19 categories must be checked. Do not omit, merge, rename, skip, or reorder categories.",
        "Use all available Ocean segments. Do not convert the input into a fixed-size sample.",
        "Only the provided comment_interaction field from ocean_summary may be used. Other ocean_summary sections are excluded.",
        "Every hit requires concrete evidence from allowed materials and a source label.",
        "Product image permission: product images may only be used by categories 3,5,6,9,10,12,15,16,17. Category 19 is disabled and should return no_hit.",
        "Priority: Category 3 product_unrelated overrides Category 5 no_physical_product_display when the unrelated live core has no sustained promotion.",
        "Priority: Category 3 product_unrelated overrides Category 6 product_description_not_detailed when there is no clear sustained product promotion intent.",
        "Priority: Category 5 no_physical_product_display overrides Category 6 when product talk exists but live frames lack real physical display.",
        "Priority: Category 15 product mismatch / IPP overrides Category 8 when the issue is live product versus bound product mismatch rather than language.",
        "Priority: Category 1 sexual_vulgar overrides Category 19 privacy_sensitive_product for sexualized exposure or implication.",
        "Category 2 hard exemptions: cleaning and novelty/product art/calendar/packaging; require dominant strong discomfort.",
        "Category 12 guard: require a concrete LIVE frame/ASR claim, a materially misleading basis, and the current prevalence/strength threshold. Product images are corroborative only; product image copy, routine marketing, and subjective praise alone cannot hit.",
        "Category 18 guard: routine sales pressure, knowledge marketing, and normal risk explanation are clean without sustained hostile, shaming, fear, resentment, jealousy, or similar negative guidance; cumulative at least 2 evidence units remain required.",
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
