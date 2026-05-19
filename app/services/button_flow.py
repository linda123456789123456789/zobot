TASK_LED_STEPS = [
    {
        "question": "你這次主要想改善哪一類需求？",
        "buttons": ["想改變髮色", "想燙髮或調整造型", "想修護受損", "還不確定"],
    },
    {
        "question": "你目前的頭髮狀況比較接近哪一種？",
        "buttons": ["近期有染燙", "髮尾乾燥或毛裂", "頭髮容易打結毛躁", "髮根或瀏海需要整理"],
    },
    {
        "question": "你比較希望這次服務達到什麼效果？",
        "buttons": ["整體造型改變", "深層修護", "柔順有光澤", "蓬鬆或局部整理"],
    },
]

TOPIC_LED_STEPS = [
    {
        "question": "你想先從哪個方向了解？",
        "buttons": ["我想知道染髮、燙髮和護髮差在哪", "我想依照髮況選", "我想依照想要的效果選"],
    },
    {
        "question": "如果依照你剛剛的方向來看，你比較在意哪一點？",
        "buttons": ["服務效果", "適合的髮況", "染燙後的修護", "造型與整理需求"],
    },
    {
        "question": "目前你比較偏向哪一種需求？",
        "buttons": ["想改變髮色", "想燙髮或整理造型", "想修護受損", "還想再比較"],
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
