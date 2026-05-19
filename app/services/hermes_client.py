import json
import os
import urllib.error
import urllib.request

from app.services.prompt_builder import build_gemini_instruction
from app.services.service_catalog import RECOMMENDATION_RULES, SERVICE_HINTS


MAX_BUTTON_OPTIONS = 4
UNCERTAIN_BUTTON_LABEL = "我不確定"


def get_chatbot_reply(input_mode, conversation_style, message, history, system_prompt):
    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    if provider == "gemini":
        return _get_gemini_reply(
            input_mode=input_mode,
            conversation_style=conversation_style,
            message=message,
            history=history,
            system_prompt=system_prompt,
        )

    return _get_mock_reply(
        input_mode=input_mode,
        conversation_style=conversation_style,
        message=message,
        history=history,
        system_prompt=system_prompt,
    )


def _get_mock_reply(input_mode, conversation_style, message, history, system_prompt):
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
            "source": "mock",
            "is_final": True,
            "final_output": final_output,
        }

    if conversation_style == "task":
        reply = _task_led_reply(user_turn_count)
    else:
        reply = _topic_led_reply(message, input_mode, user_turn_count)

    return {"reply": reply, "source": "mock", "is_final": False, "final_output": None}


def _get_gemini_reply(input_mode, conversation_style, message, history, system_prompt):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _get_mock_reply(
            input_mode=input_mode,
            conversation_style=conversation_style,
            message=message,
            history=history,
            system_prompt=system_prompt,
        )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    prompt = build_gemini_instruction(
        input_mode,
        conversation_style,
        system_prompt,
        history=history,
    )
    contents = _build_gemini_contents(prompt, message, history)
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "response_mime_type": "application/json",
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return _ai_error_reply(_gemini_error_message(error))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return _ai_error_reply("目前 AI 連線不穩，請稍後再試。")

    text = _extract_gemini_text(response_data)
    parsed = _parse_gemini_json(text)
    if not parsed:
        return _ai_error_reply("AI 回覆格式暫時無法解析，請再試一次。")

    return _normalize_gemini_result(parsed, input_mode)


def _gemini_error_message(error):
    if error.code == 503:
        return "目前 AI 使用量較高，請稍後再試一次。"

    if error.code in {401, 403}:
        return "目前 AI 金鑰或專案權限無法使用，請通知研究人員。"

    return "目前 AI 暫時無法回覆，請稍後再試。"


def _build_gemini_contents(prompt, message, history):
    contents = []
    if isinstance(history, list):
        recent_history = history[-10:]
        for index, item in enumerate(recent_history):
            role = "model" if item.get("role") == "assistant" else "user"
            content = (item.get("content") or "").strip()
            if index == len(recent_history) - 1 and role == "user":
                content = f"{prompt}\n\n目前使用者訊息：{content}"
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})

    if not contents:
        contents.append(
            {
                "role": "user",
                "parts": [{"text": f"{prompt}\n\n目前使用者訊息：{message}"}],
            }
        )

    return contents


def _extract_gemini_text(response_data):
    try:
        parts = response_data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return ""

    return "".join(part.get("text", "") for part in parts if isinstance(part, dict))


def _parse_gemini_json(text):
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def _normalize_gemini_result(result, input_mode):
    reply = str(result.get("reply") or "").strip()
    is_final = bool(result.get("is_final"))
    final_output = result.get("final_output") if is_final else None
    buttons = _normalize_buttons(result.get("buttons"), input_mode, is_final)

    if not reply:
        reply = "我想再多了解一點。你目前比較想染髮，還是改善乾燥、毛躁或受損髮況？"

    if is_final:
        final_output = _normalize_final_output(final_output)
        if not final_output:
            is_final = False

    return {
        "reply": reply,
        "buttons": buttons,
        "source": "gemini",
        "is_final": is_final,
        "final_output": final_output if is_final else None,
    }


def _normalize_buttons(buttons, input_mode, is_final):
    if input_mode != "button" or is_final:
        return []

    if not isinstance(buttons, list):
        buttons = []

    normalized = []
    for button in buttons:
        label = str(button).strip()
        if not label:
            continue
        if label == UNCERTAIN_BUTTON_LABEL:
            continue
        if label in normalized:
            continue
        normalized.append(label)

    normalized = normalized[: MAX_BUTTON_OPTIONS - 1]
    normalized.append(UNCERTAIN_BUTTON_LABEL)
    return normalized


def _normalize_final_output(final_output):
    if not isinstance(final_output, dict):
        return None

    service_name = final_output.get("recommended_service")
    if service_name not in SERVICE_HINTS:
        return None

    return {
        "recommended_service": service_name,
        "reason": str(final_output.get("reason") or SERVICE_HINTS[service_name]["reason"]),
        "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。",
    }


def _fallback_reply(reason):
    return {
        "reply": reason,
        "source": "error",
        "is_final": False,
        "final_output": None,
    }


def _ai_error_reply(reason):
    return {
        "reply": reason,
        "buttons": [],
        "source": "error",
        "is_final": False,
        "final_output": None,
    }


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

    if not allow_inferred_recommendation:
        return None

    for service_name, keywords in RECOMMENDATION_RULES:
        if any(keyword in conversation_text for keyword in keywords):
            return _final_output_for(service_name)

    return None


def _final_output_for(service_name):
    return {
        "recommended_service": service_name,
        "reason": SERVICE_HINTS[service_name]["reason"],
        "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。",
    }


def _build_default_final_output(conversation_text):
    if "染後" in conversation_text or "染髮又在意髮質" in conversation_text:
        service_name = "日本哥德式染髮"
    elif "補染" in conversation_text or "補髮根" in conversation_text:
        service_name = "補染"
    elif "漂" in conversation_text or "淺色" in conversation_text or "特殊髮色" in conversation_text:
        service_name = "漂髮"
    elif "瀏海" in conversation_text:
        service_name = "燙瀏海"
    elif "髮根" in conversation_text or "蓬鬆" in conversation_text or "頭頂塌" in conversation_text:
        service_name = "髮根燙"
    elif "燙後" in conversation_text or "燙髮又重視修護" in conversation_text:
        service_name = "日本哥德式燙髮"
    elif "燙" in conversation_text or "捲度" in conversation_text or "整理造型" in conversation_text:
        service_name = "日本資生堂燙髮"
    elif "染" in conversation_text or "髮色" in conversation_text or "顏色" in conversation_text:
        service_name = "日本資生堂染髮"
    elif "深層" in conversation_text or "受損" in conversation_text or "髮尾毛裂" in conversation_text or "髮尾乾燥" in conversation_text:
        service_name = "哥德式護髮"
    elif "日常保養" in conversation_text or "入門護髮" in conversation_text or "基礎修護" in conversation_text or "光澤" in conversation_text:
        service_name = "鉑金修護"
    elif "毛躁" in conversation_text or "柔順" in conversation_text or "觸感" in conversation_text or "打結" in conversation_text:
        service_name = "哥德式可洛娜三劑式護髮"
    else:
        service_name = "鉑金修護"

    return _final_output_for(service_name)


def _task_led_reply(user_turn_count):
    if user_turn_count <= 1:
        return "第一步，我想先了解你的需求方向。你目前比較想改變髮色、調整捲度造型，還是改善乾燥、毛躁或受損髮況？"

    return "第二步，請補充你的期待。你比較重視染燙後修護、柔順光澤、髮根蓬鬆，還是整體造型變化？"


def _topic_led_reply(message, input_mode, user_turn_count):
    if "乾" in message or "毛躁" in message:
        return "乾燥或毛躁通常可以先從保濕、柔順度與髮絲表層狀態來看。你平常吹整後比較在意觸感還是光澤？"

    if "染" in message or "燙" in message:
        return "如果你想染髮、燙髮或剛染燙過，可以一起考量造型變化、染燙後質感與修護需求。你比較重視造型改變還是染燙後髮質？"

    if user_turn_count >= 2:
        return "我了解。你可以再描述最近一次染髮、燙髮、護髮或整理頭髮的經驗，我會依照你的描述整理一個參考方向。"

    if input_mode == "button":
        return "我們可以先從你的需求聊起。你可以選一個主題，也可以描述想染髮、燙髮或想改善的髮質問題。"

    return "可以。先描述你的髮況、想嘗試的髮色、捲度造型或保養困擾，我會根據需求說明適合的服務方向。"
