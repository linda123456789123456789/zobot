UNCERTAIN = "我不確定"
UNCERTAIN_ALIASES = {UNCERTAIN, "不確定"}
BUDGET_KEYWORD = "預算範圍"
DEFAULT_BUDGET_RANGE_OPTIONS = ["1200 以下", "1201-1800", "1801-2400", "2401 以上", UNCERTAIN]
COLOR_TARGET_OPTIONS = ["自然深色", "一般棕色", "高明度特殊色", UNCERTAIN]
CURRENT_BASE_OPTIONS = ["自然黑髮", "已染深色/中深色", "已染淺色/已漂過", UNCERTAIN]
BLEACH_PREFERENCE_OPTIONS = ["可接受漂髮", "希望不漂髮", UNCERTAIN]
COLOR_BRAND_PRIORITY_OPTIONS = ["重視染後髮質修護", "重視顏色表現與CP值", UNCERTAIN]

TASK_LED_STEPS = [
    {
        "question": "請選擇你這次想預約的美髮服務方向。",
        "buttons": ["染髮", "護髮", "燙髮", UNCERTAIN],
    },
    {
        "question": "如果還不確定，請選擇最接近你的目標。",
        "buttons": ["改變髮色", "改變髮型", "改善髮質頭皮", UNCERTAIN],
    },
    {
        "question": "請選擇服務細項。",
        "buttons": ["全頭染", "補染", "漂髮設計染", UNCERTAIN],
    },
    {
        "question": "請選擇最重要的必要條件。",
        "buttons": ["預算範圍", "時間限制", "髮況限制", UNCERTAIN],
    },
    {
        "question": "請選擇是否有以下限制。",
        "buttons": ["不想漂髮", "希望時間不要太久", "希望價格不要太高", "沒有特別限制", UNCERTAIN],
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

    if _needs_budget_range_followup(user_messages):
        return {
            "question": "請選擇你的預算價位範圍。",
            "buttons": _budget_range_options_for(direction, user_messages),
        }

    if turn == 1:
        if _is_uncertain(user_messages[0]):
            return {
                "question": "請選擇最接近你的情況。",
                "buttons": ["改變髮色", "改變髮型", "改善髮質頭皮", UNCERTAIN],
            }
        return _detail_question_for_direction(direction)

    requirement_question = _next_requirement_question(direction, user_messages)
    if requirement_question:
        return requirement_question

    if not _has_restriction_answer(user_messages, direction):
        return _restriction_question_for_direction(direction)

    return None


def _detail_question_for_direction(direction):
    if direction == "染髮":
        return {"question": "請選擇你想做的染髮類型。", "buttons": ["全頭染", "補染", "漂髮設計染", UNCERTAIN]}
    if direction == "燙髮":
        return {"question": "請選擇你想做的燙髮類型。", "buttons": ["整體燙髮", "髮根燙", "燙瀏海", UNCERTAIN]}
    if direction == "護髮":
        return {"question": "請選擇你想做的護理類型。", "buttons": ["護髮修護", "頭皮護理", UNCERTAIN]}
    if direction == "補染":
        return {"question": "請確認你想做的服務細項。", "buttons": ["髮根補染", "全頭換色", UNCERTAIN]}
    if direction == "漂髮":
        return {"question": "請確認你想做的漂髮方向。", "buttons": ["一般漂髮", "特殊色設計染", UNCERTAIN]}
    if direction == "組合服務":
        return {"question": "請選擇你偏好的組合方向。", "buttons": ["染髮＋護髮", "燙髮＋護髮", UNCERTAIN]}
    return {"question": "請選擇你想做的服務細項。", "buttons": ["染髮", "燙髮", "護髮", UNCERTAIN]}


def _requirement_question_for_direction(direction):
    if direction in {"染髮", "補染", "漂髮"}:
        return {
            "question": "請選擇是否需要漂髮。",
            "buttons": ["需要漂髮", "不需要漂髮", UNCERTAIN],
        }
    if direction == "燙髮":
        return {
            "question": "你有漂過頭髮嗎？",
            "buttons": ["有漂過", "沒有漂過", UNCERTAIN],
        }
    if direction in {"護髮", "頭皮護理"}:
        return {
            "question": "這次會搭配染燙一起做嗎？",
            "buttons": ["要搭配染燙", "不搭配染燙", UNCERTAIN],
        }
    return {"question": "請選擇你的預算價位範圍。", "buttons": _budget_range_options_for(direction, [])}


def _restriction_question_for_direction(direction):
    return {
        "question": "請選擇是否有以下限制。",
        "buttons": ["不想漂髮", "希望時間不要太久", "希望價格不要太高", "沒有特別限制", UNCERTAIN],
    }


def _next_requirement_question(direction, user_messages):
    if direction == "燙髮":
        if not _has_any(user_messages, {"有漂過", "沒有漂過", UNCERTAIN}):
            return {"question": "你有漂過頭髮嗎？", "buttons": ["有漂過", "沒有漂過", UNCERTAIN]}
        if not _has_budget_range(user_messages):
            return {"question": "請選擇你的預算價位範圍。", "buttons": _budget_range_options_for(direction, user_messages)}
        return None

    if direction in {"染髮", "補染", "漂髮"}:
        detail = _resolve_detail(direction, user_messages)

        # 補染多半可直接進入預算與限制，不強制再問色系與底色。
        if detail != "補染":
            if not _has_any(user_messages, set(COLOR_TARGET_OPTIONS)):
                return {"question": "請選擇你想要的染後顏色。", "buttons": COLOR_TARGET_OPTIONS}
            if not _has_any(user_messages, set(CURRENT_BASE_OPTIONS)):
                return {"question": "請選擇你目前的髮色底色。", "buttons": CURRENT_BASE_OPTIONS}
            if _likely_need_bleach(user_messages) and not _has_any(user_messages, set(BLEACH_PREFERENCE_OPTIONS)):
                return {
                    "question": "依你提供的色系與底色，可能需要漂髮，你可接受嗎？",
                    "buttons": BLEACH_PREFERENCE_OPTIONS,
                }
            if not _has_any(user_messages, set(COLOR_BRAND_PRIORITY_OPTIONS)):
                return {
                    "question": "你這次更重視哪一點？",
                    "buttons": COLOR_BRAND_PRIORITY_OPTIONS,
                }

        if not _has_budget_range(user_messages):
            return {"question": "請選擇你的預算價位範圍。", "buttons": _budget_range_options_for(direction, user_messages)}
        return None

    if direction in {"護髮", "頭皮護理"}:
        if not _has_any(user_messages, {"要搭配染燙", "不搭配染燙", UNCERTAIN}):
            return {
                "question": "這次會搭配染燙一起做嗎？",
                "buttons": ["要搭配染燙", "不搭配染燙", UNCERTAIN],
            }
        if not _has_budget_range(user_messages):
            return {"question": "請選擇你的預算價位範圍。", "buttons": _budget_range_options_for(direction, user_messages)}
        return None

    if not _has_budget_range(user_messages):
        return {"question": "請選擇你的預算價位範圍。", "buttons": _budget_range_options_for(direction, user_messages)}
    return None


def _has_restriction_answer(user_messages, direction):
    candidates = {"不想漂髮", "希望時間不要太久", "希望價格不要太高", "沒有特別限制", UNCERTAIN}

    return any((msg or "").strip() in candidates for msg in user_messages)


def _needs_budget_range_followup(user_messages):
    selected_budget_keyword = any("預算" in (msg or "") for msg in user_messages)
    if not selected_budget_keyword:
        return False

    return not any(_is_budget_range_answer(msg) for msg in user_messages)


def _is_budget_range_answer(text):
    label = (text or "").strip()
    if not label:
        return False
    if label in DEFAULT_BUDGET_RANGE_OPTIONS:
        return True
    return any(token in label for token in ("1200", "1800", "2400", "以下", "以上"))


def _has_budget_range(user_messages):
    return any(_is_budget_range_answer(msg) for msg in user_messages)


def _has_any(user_messages, candidates):
    normalized = {(msg or "").strip() for msg in user_messages}
    return any(candidate in normalized for candidate in candidates)


def _budget_range_options_for(direction, user_messages):
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
        if detail == "漂髮設計染":
            return ["1201-1800", "1801-2400", "2401 以上", UNCERTAIN]
        return ["1200 以下", "1201-1800", "1801-2400", "2401 以上", UNCERTAIN]

    if direction in {"護髮", "頭皮護理"}:
        return ["1200 以下", "1201-1800", UNCERTAIN]

    return DEFAULT_BUDGET_RANGE_OPTIONS


def _resolve_detail(direction, user_messages):
    labels = {(msg or "").strip() for msg in user_messages}

    if direction == "燙髮":
        for option in ("整體燙髮", "髮根燙", "燙瀏海"):
            if option in labels:
                return option
        return None

    if direction in {"染髮", "補染", "漂髮"}:
        for option in ("全頭染", "補染", "漂髮設計染"):
            if option in labels:
                return option
        return None

    if direction in {"護髮", "頭皮護理"}:
        for option in ("護髮修護", "頭皮護理"):
            if option in labels:
                return option
        return None

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
    direct_map = {"染髮", "補染", "漂髮", "燙髮", "護髮", "頭皮護理", "組合服務"}
    if first in direct_map:
        return first

    if _is_uncertain(first) and len(user_messages) >= 2:
        classifier = user_messages[1]
        if classifier == "改變髮色":
            return "染髮"
        if classifier == "改變髮型":
            return "燙髮"
        if classifier == "改善髮質頭皮":
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
