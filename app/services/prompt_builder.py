from app.services.service_catalog import SERVICE_OPTIONS

TURN_LIMITS = {
    ("button", "task"): 3,
    ("button", "topic"): 3,
    ("text", "task"): 4,
    ("text", "topic"): 5,
}


def build_system_prompt(input_mode, conversation_style):
    service_list = "\n".join(
        f"- {name}: {description}"
        for name, description in SERVICE_OPTIONS.items()
    )
    return (
        "你是 ZOBOT，一位自然、簡潔、具體的美髮諮詢助理。"
        "請像正在和顧客對話，不要像問卷或客服公告。\n\n"
        "你只能根據下列店家服務提供建議，不要編造不存在的服務：\n"
        f"{service_list}\n\n"
        f"互動模式：{_input_mode_instruction(input_mode)}\n"
        f"對話風格：{_conversation_style_instruction(conversation_style)}\n\n"
        "對話規則：\n"
        "- 根據完整對話上下文決定下一步，不要只看最後一句。\n"
        "- 資訊不足時，只問一個自然且具體的追問。\n"
        "- 使用者選「我不確定」時，代表資訊不足；請降低假設，改問更容易回答的澄清問題，不要直接強行推薦。\n"
        "- 不要替使用者完成預約或服務選擇；最後選擇只能由頁面左側服務卡片完成。\n"
        "- 資訊足夠時，可以給 final_output，但 final_output 只是諮詢建議。\n"
        "- final_output.reason 必須同時說明使用者的需求或髮況，以及推薦服務在頁面上的服務特色。\n"
        "- 一律使用繁體中文。\n"
    )


def build_model_instruction(input_mode, conversation_style, system_prompt, history=None):
    return (
        f"{system_prompt}\n"
        f"{_turn_instruction(input_mode, conversation_style, history)}\n"
        "請回傳純 JSON，不要 markdown，不要加 JSON 以外文字。\n\n"
        f"{_json_schema_instruction(input_mode)}\n"
        f"{_button_json_instruction(input_mode)}"
        "final_output.recommended_service 必須完全等於頁面上的服務名稱之一。"
    )


def get_turn_limit(input_mode, conversation_style):
    return TURN_LIMITS.get((input_mode, conversation_style), 4)


def _input_mode_instruction(input_mode):
    if input_mode == "button":
        return (
            "使用者透過按鈕回覆。你的 reply 要適合搭配按鈕選項，"
            "並在資訊不足時提供兩個符合上下文的按鈕選項。"
        )

    return "使用者自由輸入。請自然追問或整理建議。"


def _conversation_style_instruction(conversation_style):
    if conversation_style == "task":
        return (
            "task-led。用步驟式諮詢快速釐清需求，逐步收斂到適合的染髮、燙髮或護髮建議。"
        )

    return (
        "topic-led。先圍繞髮況、染護知識或服務差異自然討論，再連結到適合的服務。"
    )


def _button_json_instruction(input_mode):
    if input_mode != "button":
        return ""

    return (
        "這是按鈕模式。當 is_final 為 false 時：\n"
        "- buttons 請提供 2 個選項即可，系統會自動補上「我不確定」。\n"
        "- 兩個選項要根據目前完整對話生成，不要每輪都一樣。\n"
        "- 如果使用者剛選「我不確定」，兩個選項要更寬鬆、容易判斷，例如需求方向或髮況感受。\n"
        "- 每個選項盡量 4 到 12 個中文字。\n"
        "- 不要在 buttons 中放「我不確定」。\n"
        "當 is_final 為 true 時，不要回傳 buttons。\n"
    )


def _json_schema_instruction(input_mode):
    button_field = '  "buttons": ["選項一", "選項二"],\n' if input_mode == "button" else ""
    service_names = "|".join(SERVICE_OPTIONS.keys())
    return (
        "資訊不足時：\n"
        "{\n"
        '  "reply": "自然、簡潔的下一句回覆",\n'
        f"{button_field}"
        '  "is_final": false,\n'
        '  "final_output": null\n'
        "}\n"
        "資訊足夠時：\n"
        "{\n"
        '  "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",\n'
        '  "is_final": true,\n'
        '  "final_output": {\n'
        f'    "recommended_service": "{service_names}",\n'
        '    "reason": "根據使用者需求與服務特色的具體原因",\n'
        '    "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。"\n'
        "  }\n"
        "}\n"
    )


def _turn_instruction(input_mode, conversation_style, history):
    current_turn = _count_user_turns(history)
    turn_limit = get_turn_limit(input_mode, conversation_style)
    remaining_turns = max(turn_limit - current_turn, 0)

    return (
        f"目前使用者已回答第 {current_turn} 輪；此情境最多 {turn_limit} 輪。\n"
        f"剩餘可追問輪數：{remaining_turns}。\n"
        "若尚有追問空間，請優先問最能幫助判斷服務的下一題。\n"
        "若已達上限，請根據目前資訊整理 final_output；資訊不足時採保守建議，並在 reason 說明依據。\n"
    )


def _count_user_turns(history):
    if not isinstance(history, list):
        return 1

    user_turns = [item for item in history if item.get("role") == "user"]
    return max(len(user_turns), 1)
