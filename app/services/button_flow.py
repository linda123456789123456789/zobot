"""Task-led and topic-led flow controller for ZOSS.

Design principle:
- task-led/button and task-led/free-text share the same slot schema.
- button_flow owns deterministic flow control: current slots -> next missing slot -> prompt.
- AI/free-text parsing may fill slots, but it must not own the main flow.
"""

UNCERTAIN = "我不確定"
UNCERTAIN_ALIASES = {UNCERTAIN, "不確定", "不知道", "還不確定", "不清楚"}

BUDGET_RANGES = ("1200 以下", "1201-1800", "1801-2400", "2401 以上", "預算不確定")

TASK_SLOT_ENUMS = {
    "direction": ("染髮", "燙髮", "護髮"),
    "goal": ("改變髮色", "改變髮型", "改善髮質"),
    "dye_detail": ("全頭染", "補染", "漂髮設計染"),
    "dye_root_range": ("是，主要在頭皮三公分內", "不是，超過三公分或接近全頭"),
    "target_color": ("自然深色", "一般棕色", "高明度特殊色"),
    "current_base": ("自然黑髮", "已染深色/中深色", "已染淺色/已漂過"),
    "bleach_accept": ("可接受漂髮", "希望不漂髮"),
    "brand_priority": ("重視染後髮質修護", "重視顏色表現與CP值", "兩者都重視"),
    "tradeoff_priority": ("以預算為優先", "以效果為優先"),
    "perm_detail": ("整體燙髮", "髮根燙", "燙瀏海"),
    "perm_blocker": ("曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂", "以上皆無"),
    "perm_preference": ("平衡預算，完成基本燙髮造型", "重視燙後髮質、柔順度與修護感"),
    "treatment_detail": ("受損修護", "柔順抗毛躁", "日常保養"),
    "budget_range": BUDGET_RANGES,
}

TASK_SLOT_ORDER = (
    "direction",
    "dye_detail",
    "dye_root_range",
    "target_color",
    "current_base",
    "bleach_accept",
    "brand_priority",
    "tradeoff_priority",
    "perm_detail",
    "perm_blocker",
    "perm_preference",
    "treatment_detail",
    "budget_range",
)

TASK_PROMPTS = {
    "direction": {
        "question": "請選擇你這次想預約的美髮服務方向。",
        "buttons": ["染髮", "護髮", "燙髮"],
    },
    "goal": {
        "question": "如果還不確定服務類型，請選擇最接近你的目標。",
        "buttons": ["改變髮色", "改變髮型", "改善髮質"],
    },
    "dye_detail": {
        "question": "請選擇你想做的染髮類型。",
        "buttons": ["全頭染", "補染", "漂髮設計染"],
    },
    "dye_detail_easy": {
        "question": "你目前比較接近哪一種情況？",
        "buttons": ["整頭換色", "只補新長出的髮根", "想做特殊色或局部設計"],
    },
    "dye_root_range": {
        "question": "你想補染的範圍主要在頭皮三公分內嗎？",
        "buttons": ["是，主要在頭皮三公分內", "不是，超過三公分或接近全頭"],
    },
    "target_color": {
        "question": "請選擇你想要的染後顏色方向。",
        "buttons": ["自然深色", "一般棕色", "高明度特殊色"],
    },
    "target_color_easy": {
        "question": "如果不確定色系，請選擇你想要的變化程度。",
        "buttons": ["低調自然", "明顯變淺或特殊色"],
    },
    "current_base": {
        "question": "請選擇你目前的髮色底色。",
        "buttons": ["自然黑髮", "已染深色/中深色", "已染淺色/已漂過"],
    },
    "current_base_easy": {
        "question": "你目前頭髮比較接近哪一種狀態？",
        "buttons": ["沒染過或自然黑", "有染過但偏深", "有漂過或目前偏淺"],
    },
    "bleach_accept": {
        "question": "依你的目標色，可能需要漂髮。你可接受漂髮嗎？",
        "buttons": ["可接受漂髮", "希望不漂髮"],
    },
    "brand_priority": {
        "question": "你這次更重視哪一點？",
        "buttons": ["重視染後髮質修護", "重視顏色表現與CP值", "兩者都重視"],
    },
    "tradeoff_priority": {
        "question": "如果目標效果與預算無法同時滿足，你會優先考量哪一點？",
        "buttons": ["以預算為優先", "以效果為優先"],
    },
    "perm_detail": {
        "question": "請選擇你想做的燙髮類型。",
        "buttons": ["整體燙髮", "髮根燙", "燙瀏海"],
    },
    "perm_detail_easy": {
        "question": "你比較想改善哪一個造型問題？",
        "buttons": ["想整體有捲度", "頭頂想更蓬鬆", "只想整理瀏海"],
    },
    "perm_blocker": {
        "question": "請選擇是否有以下不適合燙髮的狀況。",
        "buttons": ["曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂", "以上皆無"],
    },
    "perm_preference": {
        "question": "整體燙髮時，你比較重視哪一點？",
        "buttons": ["平衡預算，完成基本燙髮造型", "重視燙後髮質、柔順度與修護感"],
    },
    "treatment_detail": {
        "question": "請選擇你目前最想改善的髮絲狀況。",
        "buttons": ["受損修護", "柔順抗毛躁", "日常保養"],
    },
    "treatment_detail_easy": {
        "question": "如果不確定護髮類型，請選擇最接近的髮況。",
        "buttons": ["染燙後偏乾受損", "毛躁打結不柔順", "想做一般保養"],
    },
    "budget_range": {
        "question": "請選擇你的預算價位範圍。",
        "buttons": list(BUDGET_RANGES),
    },
}

TOPIC_LED_STEPS = [
    {"question": "你想先從哪個方向了解？", "buttons": ["染燙護差異", "依照髮況選擇", UNCERTAIN]},
    {"question": "目前你比較在意哪一點？", "buttons": ["服務效果", "適合的髮況", UNCERTAIN]},
    {"question": "目前你比較偏向哪一種需求？", "buttons": ["想改變造型", "想修護髮況", UNCERTAIN]},
]

BUTTON_ALIASES = {
    "改變髮色": ("direction", "染髮"),
    "改變髮型": ("direction", "燙髮"),
    "改善髮質": ("direction", "護髮"),
    "整頭換色": ("dye_detail", "全頭染"),
    "只補新長出的髮根": ("dye_detail", "補染"),
    "想做特殊色或局部設計": ("dye_detail", "漂髮設計染"),
    "不是，超過三公分或接近全頭": ("dye_detail", "全頭染"),
    "低調自然": ("target_color", "自然深色"),
    "明顯變淺或特殊色": ("target_color", "高明度特殊色"),
    "沒染過或自然黑": ("current_base", "自然黑髮"),
    "有染過但偏深": ("current_base", "已染深色/中深色"),
    "有漂過或目前偏淺": ("current_base", "已染淺色/已漂過"),
    "想整體有捲度": ("perm_detail", "整體燙髮"),
    "頭頂想更蓬鬆": ("perm_detail", "髮根燙"),
    "只想整理瀏海": ("perm_detail", "燙瀏海"),
    "染燙後偏乾受損": ("treatment_detail", "受損修護"),
    "毛躁打結不柔順": ("treatment_detail", "柔順抗毛躁"),
    "想做一般保養": ("treatment_detail", "日常保養"),
}


def get_initial_question(input_mode, conversation_style):
    if input_mode == "button":
        if conversation_style == "task":
            return TASK_PROMPTS["direction"]["question"]
        return TOPIC_LED_STEPS[0]["question"]
    if conversation_style == "task":
        return "你好，我是 ZOBOT。接下來我會一步一步了解你的髮況與需求，協助你整理適合的染髮、燙髮或護髮方向。請先告訴我，你這次主要想改善什麼？"
    return "你好，我是 ZOBOT。你可以先從最近的髮況、想了解的染燙護問題，或對服務的疑問開始聊，我會根據你的描述提供建議。"


def get_button_options(input_mode, conversation_style, history=None, is_final=False):
    if input_mode != "button" or is_final:
        return []
    if conversation_style == "task":
        prompt = get_task_guided_prompt(history)
        return prompt["buttons"] if prompt else []
    step = _current_step_index(history)
    return TOPIC_LED_STEPS[step]["buttons"] if step < len(TOPIC_LED_STEPS) else []


def get_next_question(input_mode, conversation_style, history):
    if input_mode != "button":
        return None
    if conversation_style == "task":
        prompt = get_task_guided_prompt(history)
        return prompt["question"] if prompt else None
    step = _current_step_index(history)
    return TOPIC_LED_STEPS[step]["question"] if step < len(TOPIC_LED_STEPS) else None


def get_task_guided_prompt(history):
    slots = extract_task_slots_from_history(history)
    key = next_prompt_key(slots)
    if not key:
        return None
    prompt = dict(TASK_PROMPTS[key])
    prompt["slot"] = canonical_prompt_slot(key)
    prompt["buttons"] = _with_uncertain(prompt["buttons"])
    return prompt


def extract_task_slots_from_history(history, latest_user_message=None):
    slots = {}
    current_slot = None
    for message in _messages(history):
        role = str(message.get("role") or "").lower()
        content = str(message.get("content") or message.get("message") or "")
        if role in {"assistant", "bot", "ai"}:
            current_slot = infer_slot_from_question(content) or current_slot
        elif role == "user":
            _merge_answer_into_slots(slots, content, current_slot)
    if latest_user_message is not None:
        _merge_answer_into_slots(slots, str(latest_user_message), current_slot)
    normalize_dependent_slots(slots)
    return slots


def merge_slots(base_slots, new_slots):
    merged = dict(base_slots or {})
    for key, value in (new_slots or {}).items():
        if value is None or value == "":
            continue
        if key in TASK_SLOT_ENUMS and value not in TASK_SLOT_ENUMS[key] and value != UNCERTAIN:
            continue
        merged[key] = value
    normalize_dependent_slots(merged)
    return merged


def normalize_dependent_slots(slots):
    goal = slots.get("goal")
    if goal == "改變髮色":
        slots.setdefault("direction", "染髮")
    elif goal == "改變髮型":
        slots.setdefault("direction", "燙髮")
    elif goal == "改善髮質":
        slots.setdefault("direction", "護髮")

    if slots.get("dye_root_range") == "不是，超過三公分或接近全頭":
        slots["dye_detail"] = "全頭染"

    detail = slots.get("dye_detail")
    if detail in {"補染", "漂髮設計染"}:
        for key in ("target_color", "bleach_accept", "brand_priority", "tradeoff_priority"):
            slots.pop(key, None)

    direction = slots.get("direction")
    if direction == "染髮":
        for key in ("perm_detail", "perm_blocker", "perm_preference", "treatment_detail"):
            slots.pop(key, None)
    elif direction == "燙髮":
        for key in ("dye_detail", "dye_root_range", "target_color", "current_base", "bleach_accept", "brand_priority", "tradeoff_priority", "treatment_detail"):
            slots.pop(key, None)
    elif direction == "護髮":
        for key in ("dye_detail", "dye_root_range", "target_color", "current_base", "bleach_accept", "brand_priority", "tradeoff_priority", "perm_detail", "perm_blocker", "perm_preference"):
            slots.pop(key, None)
    return slots


def next_prompt_key(slots):
    direction = slots.get("direction")
    if not direction or _is_uncertain(direction):
        return "goal" if _is_uncertain(direction) else "direction"

    if direction == "染髮":
        return _next_dye_prompt_key(slots)
    if direction == "燙髮":
        return _next_perm_prompt_key(slots)
    if direction == "護髮":
        return _next_treatment_prompt_key(slots)
    return "direction"


def is_task_ready(slots):
    return next_prompt_key(slots) is None


def canonical_prompt_slot(prompt_key):
    return {
        "goal": "direction",
        "dye_detail_easy": "dye_detail",
        "target_color_easy": "target_color",
        "current_base_easy": "current_base",
        "perm_detail_easy": "perm_detail",
        "treatment_detail_easy": "treatment_detail",
    }.get(prompt_key, prompt_key)


def infer_slot_from_question(question):
    text = str(question or "")
    checks = [
        ("direction", ("服務方向", "服務類型", "想預約", "主要想改善")),
        ("goal", ("最接近你的目標", "還不確定服務")),
        ("dye_detail", ("染髮類型", "哪一種情況")),
        ("dye_root_range", ("三公分", "補染的範圍")),
        ("target_color", ("染後顏色", "色系", "變化程度")),
        ("current_base", ("目前的髮色", "目前頭髮", "底色")),
        ("bleach_accept", ("接受漂髮", "可接受漂髮")),
        ("brand_priority", ("更重視哪一點", "染後髮質", "顏色表現")),
        ("tradeoff_priority", ("優先考量", "預算無法同時")),
        ("perm_detail", ("燙髮類型", "造型問題")),
        ("perm_blocker", ("不適合燙髮", "是否有以下")),
        ("perm_preference", ("整體燙髮時", "比較重視哪一點")),
        ("treatment_detail", ("髮絲狀況", "護髮類型", "最接近的髮況")),
        ("budget_range", ("預算價位", "預算範圍")),
    ]
    for slot, keywords in checks:
        if any(keyword in text for keyword in keywords):
            return slot
    return None


def _next_dye_prompt_key(slots):
    detail = slots.get("dye_detail")
    if not detail:
        return "dye_detail"
    if _is_uncertain(detail):
        return "dye_detail_easy"

    if detail == "補染":
        if not slots.get("dye_root_range"):
            return "dye_root_range"
        return None

    if detail == "漂髮設計染":
        if not slots.get("current_base"):
            return "current_base"
        if _is_uncertain(slots.get("current_base")):
            return "current_base_easy"
        if not slots.get("budget_range"):
            return "budget_range"
        return None

    if detail == "全頭染":
        if not slots.get("target_color"):
            return "target_color"
        if _is_uncertain(slots.get("target_color")):
            return "target_color_easy"
        if not slots.get("current_base"):
            return "current_base"
        if _is_uncertain(slots.get("current_base")):
            return "current_base_easy"
        if _likely_need_bleach(slots) and not slots.get("bleach_accept"):
            return "bleach_accept"
        if _likely_need_bleach(slots) and slots.get("bleach_accept") == "可接受漂髮":
            return "budget_range" if not slots.get("budget_range") else None
        if _likely_need_bleach(slots) and slots.get("bleach_accept") == "希望不漂髮":
            if not slots.get("tradeoff_priority"):
                return "tradeoff_priority"
        if not slots.get("brand_priority"):
            return "brand_priority"
        return None
    return "dye_detail"


def _next_perm_prompt_key(slots):
    if not slots.get("perm_detail"):
        return "perm_detail"
    if _is_uncertain(slots.get("perm_detail")):
        return "perm_detail_easy"
    if not slots.get("perm_blocker"):
        return "perm_blocker"
    if slots.get("perm_blocker") != "以上皆無":
        return None
    if slots.get("perm_detail") == "整體燙髮" and not slots.get("perm_preference"):
        return "perm_preference"
    return None


def _next_treatment_prompt_key(slots):
    if not slots.get("treatment_detail"):
        return "treatment_detail"
    if _is_uncertain(slots.get("treatment_detail")):
        return "treatment_detail_easy"
    return None


def _merge_answer_into_slots(slots, answer, current_slot=None):
    text = str(answer or "").strip()
    if not text:
        return
    if _is_uncertain(text):
        if current_slot:
            slots[canonical_prompt_slot(current_slot)] = UNCERTAIN
        else:
            slots.setdefault("direction", UNCERTAIN)
        return

    if text in BUTTON_ALIASES:
        slot, value = BUTTON_ALIASES[text]
        slots[slot] = value
        return

    for slot, values in TASK_SLOT_ENUMS.items():
        if text in values:
            slots[slot] = text
            return

    # tolerate compact budget strings produced by free-text/parser.
    compact = text.replace(" ", "")
    for item in BUDGET_RANGES:
        if compact == item.replace(" ", ""):
            slots["budget_range"] = item
            return

    # Last-resort exact direction keywords.
    if "染" in text and "燙" not in text and "護" not in text:
        slots.setdefault("direction", "染髮")
    elif "燙" in text:
        slots.setdefault("direction", "燙髮")
    elif "護" in text or "修護" in text or "保養" in text:
        slots.setdefault("direction", "護髮")


def _likely_need_bleach(slots):
    return slots.get("target_color") == "高明度特殊色" or slots.get("current_base") == "已染深色/中深色"


def _is_uncertain(value):
    return str(value or "").strip() in UNCERTAIN_ALIASES


def _with_uncertain(buttons):
    result = []
    for button in buttons:
        if button not in result:
            result.append(button)
    if UNCERTAIN not in result:
        result.append(UNCERTAIN)
    return result


def _messages(history):
    if not history:
        return []
    if isinstance(history, dict):
        history = history.get("messages", [])
    result = []
    for item in history or []:
        if isinstance(item, dict):
            result.append(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            result.append({"role": item[0], "content": item[1]})
    return result


def _current_step_index(history):
    return len([m for m in _messages(history) if str(m.get("role", "")).lower() == "user"])
