import re

from app.services.service_catalog import SERVICE_CATEGORIES


UNCERTAIN = "我不確定"
UNCERTAIN_ALIASES = {UNCERTAIN, "不確定"}
BUDGET_KEYWORD = "預算範圍"
DEFAULT_BUDGET_RANGE_OPTIONS = ["1200 以下", "1201-1800", "1801-2400", "2401 以上", UNCERTAIN]
BUDGET_RANGE_LABELS = ("1200 以下", "1201-1800", "1801-2400", "2401 以上")
COLOR_TARGET_OPTIONS = ["自然深色", "一般棕色", "高明度特殊色", UNCERTAIN]
CURRENT_BASE_OPTIONS = ["自然黑髮", "已染深色/中深色", "已染淺色/已漂過", UNCERTAIN]
BLEACH_PREFERENCE_OPTIONS = ["可接受漂髮", "希望不漂髮", UNCERTAIN]
COLOR_BRAND_PRIORITY_OPTIONS = ["重視染後髮質修護", "重視顏色表現與CP值", UNCERTAIN]
TRADEOFF_PRIORITY_OPTIONS = ["以預算為優先", "以效果為優先", UNCERTAIN]
PERM_BLOCKER_OPTIONS = ["曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂", "以上皆無"]
PERM_PREFERENCE_UNCERTAIN = "不確定，請用預算判斷"
PERM_OVERALL_PREFERENCE_OPTIONS = [
    "平衡預算，完成基本燙髮造型",
    "重視燙後髮質、柔順度與修護感",
    PERM_PREFERENCE_UNCERTAIN,
]

TASK_LED_STEPS = [
    {
        "question": "請選擇你這次想預約的美髮服務方向。",
        "buttons": ["染髮", "護髮", "燙髮", UNCERTAIN],
    },
    {
        "question": "如果還不確定，請選擇最接近你的目標。",
        "buttons": ["改變髮色", "改變髮型", "改善髮質", UNCERTAIN],
    },
    {
        "question": "請選擇服務細項。",
        "buttons": ["全頭染", "補染", UNCERTAIN],
    },
    {
        "question": "請選擇最重要的必要條件。",
        "buttons": ["預算範圍", "時間限制", "髮況限制", UNCERTAIN],
    },
]

TOPIC_LED_STEPS = [
    {
        "question": "你想先從哪個方向了解？",
        "buttons": ["染燙護差異", "依照髮況選擇", UNCERTAIN],
    },
    {
        "question": "如果依照你剛剛的方向來看，你比較在意哪一點？",
        "buttons": ["服務效果", "適合的髮況", UNCERTAIN],
    },
    {
        "question": "目前你比較偏向哪一種需求？",
        "buttons": ["想改變造型", "想修護髮況", UNCERTAIN],
    },
]


def get_initial_question(input_mode, conversation_style):
    if input_mode == "button":
        return _steps_for(conversation_style)[0]["question"]

    if conversation_style == "task":
        return "你好，我是 ZOBOT。接下來我會一步一步了解你的髮況與需求，協助你整理適合的染髮、燙髮或護髮方向。請先告訴我，你這次主要想改善什麼？"

    return "你好，我是 ZOBOT。你可以先從最近的髮況、想了解的染燙護問題，或對服務的疑問開始聊，我會根據你的描述提供建議。"


def get_button_options(input_mode, conversation_style, history=None, is_final=False):
    if input_mode != "button" or is_final:
        return []

    if conversation_style == "task":
        guided = get_task_guided_prompt(history)
        if guided:
            return guided["buttons"]

    step = _current_step_index(history)
    steps = _steps_for(conversation_style)
    if step >= len(steps):
        return []

    return steps[step]["buttons"]


def get_next_question(input_mode, conversation_style, history):
    if input_mode != "button":
        return None

    if conversation_style == "task":
        guided = get_task_guided_prompt(history)
        if guided:
            return guided["question"]

    step = _current_step_index(history)
    steps = _steps_for(conversation_style)
    if step >= len(steps):
        return None

    return steps[step]["question"]


def get_task_guided_prompt(history):
    user_messages = _user_messages(history)
    turn = len(user_messages)

    # Q1 is rendered from initial UI state.
    if turn <= 0:
        return {
            "question": "請選擇你這次想預約的美髮服務方向。",
            "buttons": ["染髮", "護髮", "燙髮", UNCERTAIN],
        }

    direction = _resolve_direction(user_messages)
    if not direction:
        return {
            "question": "請先選擇最接近你的目標。",
            "buttons": ["改變髮色", "改變髮型", "改善髮質", UNCERTAIN],
        }

    if _needs_budget_range_followup(user_messages):
        budget_options = _budget_range_options_for(direction, user_messages)
        if _has_multiple_budget_options(budget_options):
            return {
                "question": "請選擇你的預算價位範圍。",
                "buttons": budget_options,
            }

    if turn == 1:
        if _is_uncertain(user_messages[0]):
            return {
                "question": "請選擇最接近你的情況。",
                "buttons": ["改變髮色", "改變髮型", "改善髮質", UNCERTAIN],
            }
        return _detail_question_for_direction(direction)

    return _next_missing_slot_prompt(direction, user_messages)


def _detail_question_for_direction(direction):
    if direction == "染髮":
        return {"question": "請選擇你想做的染髮類型。", "buttons": ["全頭染", "補染", UNCERTAIN]}
    if direction == "燙髮":
        return {"question": "請選擇你想做的燙髮類型。", "buttons": ["整體燙髮", "髮根燙", "燙瀏海", UNCERTAIN]}
    if direction == "護髮":
        return {"question": "請選擇你目前最想改善的髮絲狀況。", "buttons": ["受損修護", "柔順抗毛躁", "日常保養", UNCERTAIN]}
    if direction == "補染":
        return {"question": "請確認你想做的服務細項。", "buttons": ["髮根補染", "全頭換色", UNCERTAIN]}
    if direction == "漂髮":
        return {"question": "請確認你想做的漂髮方向。", "buttons": ["一般漂髮", "特殊色設計染", UNCERTAIN]}
    return {"question": "請選擇你想做的服務細項。", "buttons": ["染髮", "燙髮", "護髮", UNCERTAIN]}


def _next_missing_slot_prompt(direction, user_messages):
    if direction == "燙髮":
        detail = _resolve_detail(direction, user_messages)
        if not detail:
            return _detail_question_for_direction(direction)

        blocker = _resolve_perm_blocker(user_messages)
        if not blocker:
            return {"question": "是否有不可燙條件？", "buttons": PERM_BLOCKER_OPTIONS}
        if blocker != "以上皆無":
            return None

        # Q3/Q4 only apply for overall perming.
        if detail != "整體燙髮":
            return None

        preference = _resolve_perm_overall_preference(user_messages)
        if not preference:
            return {
                "question": "若是整體燙髮，請確認服務取向。",
                "buttons": PERM_OVERALL_PREFERENCE_OPTIONS,
            }

        if preference == "重視燙後髮質、柔順度與修護感":
            return None

        if preference == "平衡預算，完成基本燙髮造型":
            return None

        if not _has_budget_range(user_messages):
            budget_options = _budget_range_options_for(direction, user_messages)
            if _has_multiple_budget_options(budget_options):
                return {
                    "question": "若不確定，請用預算範圍協助判斷。",
                    "buttons": budget_options,
                }
        return None

    if direction in {"染髮", "補染", "漂髮"}:
        detail = _resolve_detail(direction, user_messages)
        if not detail:
            return _detail_question_for_direction(direction)

        if detail == "補染":
            return None

        # 全頭染才需要追問顏色、底色與是否可漂。
        if detail == "全頭染":
            if not _has_any(user_messages, set(COLOR_TARGET_OPTIONS)):
                return {"question": "請選擇你想要的染後顏色。", "buttons": COLOR_TARGET_OPTIONS}
            if not _has_any(user_messages, set(CURRENT_BASE_OPTIONS)):
                return {"question": "請選擇你目前的髮色底色。", "buttons": CURRENT_BASE_OPTIONS}
            if _likely_need_bleach(user_messages) and not _has_any(user_messages, set(BLEACH_PREFERENCE_OPTIONS)):
                return {
                    "question": "依你提供的色系與底色，可能需要漂髮，你可接受嗎？",
                    "buttons": BLEACH_PREFERENCE_OPTIONS,
                }
            if _likely_need_bleach(user_messages) and _pick_first(user_messages, set(BLEACH_PREFERENCE_OPTIONS)) == "可接受漂髮":
                return None
            if not _has_any(user_messages, set(COLOR_BRAND_PRIORITY_OPTIONS)):
                return {
                    "question": "你這次更重視哪一點？",
                    "buttons": COLOR_BRAND_PRIORITY_OPTIONS,
                }

        if not _has_budget_range(user_messages):
            budget_options = _budget_range_options_for(direction, user_messages)
            if _has_multiple_budget_options(budget_options):
                return {"question": "請選擇你的預算價位範圍。", "buttons": budget_options}
        if _needs_priority_followup(direction, user_messages):
            return {
                "question": "看起來預算與效果偏好有取捨，你想優先哪一個？",
                "buttons": TRADEOFF_PRIORITY_OPTIONS,
            }
        return None

    if direction == "護髮":
        if not _resolve_detail(direction, user_messages):
            return _detail_question_for_direction(direction)
        if not _has_budget_range(user_messages):
            budget_options = _budget_range_options_for(direction, user_messages)
            if _has_multiple_budget_options(budget_options):
                return {"question": "請選擇你的預算價位範圍。", "buttons": budget_options}
        if _needs_priority_followup(direction, user_messages):
            return {
                "question": "看起來預算與效果偏好有取捨，你想優先哪一個？",
                "buttons": TRADEOFF_PRIORITY_OPTIONS,
            }
        return None

    if not _has_budget_range(user_messages):
        budget_options = _budget_range_options_for(direction, user_messages)
        if _has_multiple_budget_options(budget_options):
            return {"question": "請選擇你的預算價位範圍。", "buttons": budget_options}
    return None


def _has_priority_choice_answer(user_messages):
    return _has_any(user_messages, set(TRADEOFF_PRIORITY_OPTIONS))


def _service_price_bounds():
    bounds = {}
    for category in SERVICE_CATEGORIES:
        for service in category.get("services", []):
            name = service.get("name")
            price_text = str(service.get("price") or "")
            if not name:
                continue
            numbers = [int(token) for token in re.findall(r"\d{3,5}", price_text.replace(",", ""))]
            if not numbers:
                bounds[name] = {"min": 0, "max": 999999}
                continue
            bounds[name] = {"min": min(numbers), "max": max(numbers)}
    return bounds


SERVICE_PRICE_BOUNDS = _service_price_bounds()


def _budget_constraint_from_label(label):
    token = str(label or "").strip()
    if token == "1200 以下":
        return {"min": None, "max": 1200}
    if token == "1201-1800":
        return {"min": 1201, "max": 1800}
    if token == "1801-2400":
        return {"min": 1801, "max": 2400}
    if token == "2401 以上":
        return {"min": 2401, "max": None}
    return None


def _service_price_overlaps_budget(service_bounds, budget_constraint):
    service_min = service_bounds.get("min")
    service_max = service_bounds.get("max")
    if service_min is None or service_max is None:
        return False

    budget_min = budget_constraint.get("min")
    budget_max = budget_constraint.get("max")

    if budget_min is not None and service_max < budget_min:
        return False
    if budget_max is not None and service_min > budget_max:
        return False
    return True


def _service_matches_budget(service_name, budget_label):
    constraint = _budget_constraint_from_label(budget_label)
    if not constraint:
        return False
    bounds = SERVICE_PRICE_BOUNDS.get(service_name)
    if not bounds:
        return False
    return _service_price_overlaps_budget(bounds, constraint)


def _service_names_by_category_index(index):
    if index < 0 or index >= len(SERVICE_CATEGORIES):
        return []
    return [service.get("name") for service in SERVICE_CATEGORIES[index].get("services", []) if service.get("name")]


def _candidate_services_for_direction(direction, user_messages):
    if direction in {"染髮", "補染", "漂髮"}:
        dye_services = _service_names_by_category_index(0)
        if len(dye_services) < 4:
            return dye_services

        detail = _resolve_detail(direction, user_messages)
        if detail == "補染":
            return [dye_services[2]]
        bleach_accept = _pick_first(user_messages, set(BLEACH_PREFERENCE_OPTIONS))
        brand_priority = _pick_first(user_messages, set(COLOR_BRAND_PRIORITY_OPTIONS))
        if detail == "全頭染" and _likely_need_bleach(user_messages) and bleach_accept == "可接受漂髮":
            return [dye_services[3]]

        candidates = []
        if brand_priority == "重視染後髮質修護":
            candidates.extend([dye_services[1], dye_services[0]])
        elif brand_priority == "重視顏色表現與CP值":
            candidates.extend([dye_services[0], dye_services[1]])
        else:
            candidates.extend([dye_services[0], dye_services[1]])

        deduped = []
        for item in candidates:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    if direction == "燙髮":
        perm_services = _service_names_by_category_index(1)
        if len(perm_services) < 4:
            return perm_services

        detail = _resolve_detail(direction, user_messages)
        blocker = _resolve_perm_blocker(user_messages)
        if blocker and blocker != "以上皆無":
            return []

        if detail == "髮根燙":
            return [perm_services[2]]
        if detail == "燙瀏海":
            return [perm_services[3]]

        preference = _resolve_perm_overall_preference(user_messages)
        if preference == "平衡預算，完成基本燙髮造型":
            return [perm_services[0], perm_services[1]]
        if preference == "重視燙後髮質、柔順度與修護感":
            return [perm_services[1], perm_services[0]]
        if preference == PERM_PREFERENCE_UNCERTAIN:
            return [perm_services[0], perm_services[1]]
        return [perm_services[0], perm_services[1]]

    if direction == "護髮":
        treatment_services = _service_names_by_category_index(2)
        if len(treatment_services) < 3:
            return treatment_services

        detail = _resolve_detail(direction, user_messages)
        if detail == "受損修護":
            return [treatment_services[0], treatment_services[1], treatment_services[2]]
        if detail == "柔順抗毛躁":
            return [treatment_services[1], treatment_services[0], treatment_services[2]]
        if detail == "日常保養":
            return [treatment_services[2], treatment_services[1], treatment_services[0]]
        return [treatment_services[1], treatment_services[0], treatment_services[2]]

    return []


def _needs_priority_followup(direction, user_messages):
    if _has_priority_choice_answer(user_messages):
        return False
    budget_label = _pick_first(user_messages, set(DEFAULT_BUDGET_RANGE_OPTIONS))
    if not budget_label:
        return False

    ranked = _candidate_services_for_direction(direction, user_messages)
    if len(ranked) < 2:
        return False

    filtered = [service_name for service_name in ranked if _service_matches_budget(service_name, budget_label)]
    if not filtered:
        return False

    return ranked[0] != filtered[0]


def _needs_budget_range_followup(user_messages):
    selected_budget_keyword = any((msg or "").strip() == BUDGET_KEYWORD for msg in user_messages)
    if not selected_budget_keyword:
        return False

    return not any(_is_budget_range_answer(msg) for msg in user_messages)


def _is_budget_range_answer(text):
    label = (text or "").strip()
    if not label:
        return False
    if label in DEFAULT_BUDGET_RANGE_OPTIONS:
        return True
    return re.search(r"\d{3,5}", label) is not None


def _has_budget_range(user_messages):
    return any(_is_budget_range_answer(msg) for msg in user_messages)


def _has_multiple_budget_options(options):
    actionable = [option for option in (options or []) if option != UNCERTAIN]
    return len(actionable) > 1


def _has_any(user_messages, candidates):
    normalized = {(msg or "").strip() for msg in user_messages}
    return any(candidate in normalized for candidate in candidates)


def _budget_range_options_for(direction, user_messages):
    ranked_candidates = _candidate_services_for_direction(direction, user_messages)
    dynamic_options = _budget_range_options_from_candidates(ranked_candidates)
    if dynamic_options:
        return dynamic_options + [UNCERTAIN]

    detail = _resolve_detail(direction, user_messages)

    if direction == "燙髮":
        if detail == "整體燙髮":
            return ["1201-1800", "1801-2400", "2401 以上", UNCERTAIN]
        if detail == "髮根燙":
            return ["1201-1800", UNCERTAIN]
        if detail == "燙瀏海":
            return ["1200 以下", UNCERTAIN]
        return ["1200 以下", "1201-1800", "1801-2400", "2401 以上", UNCERTAIN]

    if direction in {"染髮", "補染", "漂髮"}:
        if detail == "全頭染":
            return ["1201-1800", "1801-2400", "2401 以上", UNCERTAIN]
        if detail == "補染":
            return ["1200 以下", "1201-1800", UNCERTAIN]
        return ["1200 以下", "1201-1800", "1801-2400", "2401 以上", UNCERTAIN]

    if direction == "護髮":
        if detail == "受損修護":
            return ["1201-1800", UNCERTAIN]
        return ["1200 以下", "1201-1800", UNCERTAIN]

    return DEFAULT_BUDGET_RANGE_OPTIONS


def _budget_range_options_from_candidates(ranked_candidates):
    if not ranked_candidates:
        return []

    options = []
    previous_signature = None
    for budget_label in BUDGET_RANGE_LABELS:
        filtered = [service_name for service_name in ranked_candidates if _service_matches_budget(service_name, budget_label)]
        if not filtered:
            continue

        # Keep only ranges that actually change the remaining candidate set.
        signature = tuple(filtered)
        if signature == previous_signature:
            continue

        options.append(budget_label)
        previous_signature = signature

    return options


def _resolve_detail(direction, user_messages):
    labels = {(msg or "").strip() for msg in user_messages}

    if direction == "燙髮":
        for option in ("整體燙髮", "髮根燙", "燙瀏海"):
            if option in labels:
                return option
        return None

    if direction in {"染髮", "補染", "漂髮"}:
        for option in ("全頭染", "補染"):
            if option in labels:
                return option
        if "漂髮設計染" in labels:
            return "全頭染"
        return None

    if direction == "護髮":
        for option in ("受損修護", "柔順抗毛躁", "日常保養"):
            if option in labels:
                return option
        return None

    return None


def _resolve_perm_blocker(user_messages):
    labels = {(msg or "").strip() for msg in user_messages}
    for option in PERM_BLOCKER_OPTIONS:
        if option in labels:
            return option
    return None


def _resolve_perm_overall_preference(user_messages):
    labels = {(msg or "").strip() for msg in user_messages}
    for option in PERM_OVERALL_PREFERENCE_OPTIONS:
        if option in labels:
            return option
    return None


def _likely_need_bleach(user_messages):
    target = _pick_first(user_messages, set(COLOR_TARGET_OPTIONS))
    current = _pick_first(user_messages, set(CURRENT_BASE_OPTIONS))

    if not target or not current:
        return False

    if target == "高明度特殊色":
        return True
    if target == "一般棕色" and current == "自然黑髮":
        return True
    return False


def _pick_first(user_messages, candidates):
    for msg in user_messages:
        label = (msg or "").strip()
        if label in candidates:
            return label
    return None


def _resolve_direction(user_messages):
    if not user_messages:
        return None

    first = user_messages[0]
    direct_map = {"染髮", "補染", "漂髮", "燙髮", "護髮"}
    if first in direct_map:
        return first

    if _is_uncertain(first) and len(user_messages) >= 2:
        classifier = user_messages[1]
        if classifier == "改變髮色":
            return "染髮"
        if classifier == "改變髮型":
            return "燙髮"
        if classifier == "改善髮質":
            return "護髮"
    return None


def _is_uncertain(text):
    return (text or "").strip() in UNCERTAIN_ALIASES


def _steps_for(conversation_style):
    if conversation_style == "topic":
        return TOPIC_LED_STEPS

    return TASK_LED_STEPS


def _current_step_index(history):
    if not isinstance(history, list):
        return 0

    user_turn_count = sum(1 for item in history if item.get("role") == "user")
    return max(user_turn_count, 0)


def _user_messages(history):
    if not isinstance(history, list):
        return []
    return [(item.get("content") or "").strip() for item in history if item.get("role") == "user" and (item.get("content") or "").strip()]
