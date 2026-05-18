TASK_LED_STEPS = [
    {
        "question": "你這次主要想改善哪一類需求？",
        "buttons": ["想改變髮色", "想修護髮況", "我不確定"],
    },
    {
        "question": "你目前的頭髮狀況比較接近哪一種？",
        "buttons": ["近期有染燙", "髮尾乾燥或毛躁", "我不確定"],
    },
    {
        "question": "你比較希望這次服務達到什麼效果？",
        "buttons": ["整體造型改變", "柔順有光澤", "我不確定"],
    },
]

TOPIC_LED_STEPS = [
    {
        "question": "你想先從哪個方向了解？",
        "buttons": ["染髮和護髮差異", "依照髮況選擇", "我不確定"],
    },
    {
        "question": "如果依照你剛剛的方向來看，你比較在意哪一點？",
        "buttons": ["服務效果", "適合的髮況", "我不確定"],
    },
    {
        "question": "目前你比較偏向哪一種需求？",
        "buttons": ["想改變髮色", "想修護髮況", "我不確定"],
    },
]


def get_initial_question(input_mode, conversation_style):
    if input_mode == "button":
        return _steps_for(conversation_style)[0]["question"]

    if conversation_style == "task":
        return "你好，我是 ZOBOT。接下來我會一步一步了解你的髮況與需求，協助你整理適合的染髮或護髮方向。請先告訴我，你這次主要想改善什麼？"

    return "你好，我是 ZOBOT。你可以先從最近的髮況、想了解的染護問題，或對服務的疑問開始聊，我會根據你的描述提供建議。"


def get_button_options(input_mode, conversation_style, history=None, is_final=False):
    if input_mode != "button" or is_final:
        return []

    step = _current_step_index(history)
    steps = _steps_for(conversation_style)
    if step >= len(steps):
        return []

    return steps[step]["buttons"]


def get_next_question(input_mode, conversation_style, history):
    if input_mode != "button":
        return None

    step = _current_step_index(history)
    steps = _steps_for(conversation_style)
    if step >= len(steps):
        return None

    return steps[step]["question"]


def _steps_for(conversation_style):
    if conversation_style == "topic":
        return TOPIC_LED_STEPS

    return TASK_LED_STEPS


def _current_step_index(history):
    if not isinstance(history, list):
        return 0

    user_turn_count = sum(1 for item in history if item.get("role") == "user")
    return max(user_turn_count, 0)
