SERVICE_HINTS = {
    "日本哥德式染髮": {
        "reason": "適合想染髮，同時在意染後髮質與修護感的顧客。",
        "keywords": ["哥德式染髮", "染後", "染髮修護", "染後髮質"],
    },
    "日本資生堂染髮": {
        "reason": "適合想改變髮色、提升整體造型，並重視染後質感的顧客。",
        "keywords": ["資生堂染髮", "染髮", "髮色", "顏色", "造型", "質感"],
    },
    "哥德式護髮": {
        "reason": "適合染燙後受損、乾燥或髮尾毛裂，需要深層修護的顧客。",
        "keywords": ["哥德式護髮", "受損", "修護", "深層", "染燙", "髮尾毛裂"],
    },
    "資生堂護髮": {
        "reason": "適合想提升柔順度、光澤與髮絲觸感的顧客。",
        "keywords": ["資生堂護髮", "柔順", "光澤", "毛躁", "觸感"],
    },
}


def get_chatbot_reply(input_mode, conversation_style, message, history, system_prompt):
    """Return a mock chatbot response with an optional final output.

    TODO: Replace the mock logic below with Hermes Agent API integration.
    Future implementation notes:
    1. Read HERMES_API_URL, HERMES_API_KEY, and HERMES_AGENT_ID from
       environment variables.
    2. Send input_mode, conversation_style, system_prompt, message, and
       history to the Hermes Agent API from the Flask backend only.
    3. Keep API keys, agent IDs, prompt text, and Hermes request logic out of
       frontend JavaScript.
    4. Parse the Hermes response and normalize it to:
       {"reply": str, "is_final": bool, "final_output": dict | None}
    5. final_output must remain a consultation recommendation only. Final
       service selection is handled by the left-side service card buttons.
    """
    del system_prompt

    user_turn_count = _count_user_turns(history)
    conversation_text = _conversation_text(history, message)
    allow_inferred_recommendation = _should_finish_consultation(
        input_mode,
        conversation_style,
        user_turn_count,
    )
    final_output = _build_final_output(
        conversation_text,
        allow_inferred_recommendation,
    )

    if not final_output and allow_inferred_recommendation:
        final_output = _build_default_final_output(conversation_text)

    if final_output:
        return {
            "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
            "is_final": True,
            "final_output": final_output,
        }

    if conversation_style == "task":
        reply = _task_led_reply(user_turn_count)
    else:
        reply = _topic_led_reply(message, input_mode, user_turn_count)

    return {"reply": reply, "is_final": False, "final_output": None}


def _count_user_turns(history):
    if not isinstance(history, list):
        return 1

    user_turns = [item for item in history if item.get("role") == "user"]
    return max(len(user_turns), 1)


def _conversation_text(history, message):
    if not isinstance(history, list):
        return message

    user_messages = [
        item.get("content", "")
        for item in history
        if item.get("role") == "user"
    ]
    if message not in user_messages:
        user_messages.append(message)

    return " ".join(user_messages)


def _should_finish_consultation(input_mode, conversation_style, user_turn_count):
    if input_mode == "button":
        return user_turn_count >= 3

    if conversation_style == "task":
        return user_turn_count >= 3

    return user_turn_count >= 4


def _build_final_output(conversation_text, allow_inferred_recommendation):
    for service_name, details in SERVICE_HINTS.items():
        if service_name in conversation_text:
            return _final_output_for(service_name)

        if allow_inferred_recommendation and any(
            keyword in conversation_text for keyword in details["keywords"]
        ):
            return _final_output_for(service_name)

    return None


def _final_output_for(service_name):
    return {
        "recommended_service": service_name,
        "reason": SERVICE_HINTS[service_name]["reason"],
        "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。",
    }


def _build_default_final_output(conversation_text):
    if "染" in conversation_text or "髮色" in conversation_text or "顏色" in conversation_text:
        if "修護" in conversation_text or "染後" in conversation_text or "受損" in conversation_text:
            service_name = "日本哥德式染髮"
        else:
            service_name = "日本資生堂染髮"
    elif "乾" in conversation_text or "受損" in conversation_text or "髮尾毛裂" in conversation_text:
        service_name = "哥德式護髮"
    elif "毛躁" in conversation_text or "柔順" in conversation_text or "光澤" in conversation_text:
        service_name = "資生堂護髮"
    else:
        service_name = "資生堂護髮"

    return _final_output_for(service_name)


def _task_led_reply(user_turn_count):
    if user_turn_count <= 1:
        return "第一步，我想先了解你的需求方向。你目前比較想改變髮色，還是改善乾燥、毛躁或受損髮況？"

    return "第二步，請補充你的期待。你比較重視染後質感、修護感、柔順光澤，還是整體造型變化？"


def _topic_led_reply(message, input_mode, user_turn_count):
    if "乾" in message or "毛躁" in message:
        return "乾燥或毛躁通常可以先從保濕、柔順度與髮絲表層狀態來看。你平常吹整後比較在意觸感還是光澤？"

    if "染" in message or "燙" in message:
        return "如果你想染髮或剛染燙過，可以一起考量髮色變化、染後質感與修護需求。你比較重視造型改變還是染後髮質？"

    if user_turn_count >= 2:
        return "我了解。你可以再描述最近一次染髮、護髮或整理頭髮的經驗，我會依照你的描述整理一個參考方向。"

    if input_mode == "button":
        return "我們可以先從你的需求聊起。你可以選一個主題，也可以描述想染髮或想改善的髮質問題。"

    return "可以。先描述你的髮況、想嘗試的髮色或保養困擾，我會根據需求說明適合的服務方向。"
