import json
import os
import re
import urllib.error
import urllib.request

from app.services.button_flow import get_task_guided_prompt
from app.services.prompt_builder import build_model_instruction, get_turn_limit
from app.services.service_catalog import RECOMMENDATION_RULES, SERVICE_HINTS


MAX_BUTTON_OPTIONS = 5
UNCERTAIN_BUTTON_LABEL = "我不確定"
TEMPLATE_REPLY_PATTERNS = (
    "自然、簡潔的下一句回覆",
    "自然, 簡潔的下一句回覆",
)
FREE_TEXT_NORMALIZE_MAP = {
    "染頭髮": "染髮",
    "染发": "染髮",
    "染頭毛": "染髮",
    "換髮色": "染髮",
    "換顏色": "染髮",
    "上色": "染髮",
    "整頭換顏色": "全頭染",
    "整頭都換顏色": "全頭染",
    "整頭換色": "全頭染",
    "整頭染": "全頭染",
    "髮根補色": "補染",
    "補髮根": "補染",
    "補布丁": "補染",
    "布丁頭": "補染",
    "特殊色": "漂髮設計染",
    "漂色": "漂髮設計染",
    "漂染": "漂髮設計染",
    "全染": "全頭染",
    "整體燙": "整體燙髮",
    "燙全頭": "整體燙髮",
    "燙頭髮": "燙髮",
    "護理": "護髮",
    "做護髮": "護髮",
    "修瀏海": "瀏海修剪",
    "剪瀏海": "瀏海修剪",
}

TASK_SLOT_KEYWORDS = {
    "direction": {
        "染髮": ("染髮", "染髮", "染发", "上色", "換髮色", "換顏色", "髮色"),
        "燙髮": ("燙髮", "燙头髮", "燙捲", "捲度", "燙"),
        "護髮": ("護髮", "修護", "護理", "保養", "頭皮護理"),
        "剪髮": ("剪髮", "修剪", "剪", "瀏海修剪"),
    },
    "dye_detail": {
        "全頭染": ("全頭染", "整頭染", "整頭都染", "整頭換色", "整頭都換顏色", "全染"),
        "補染": ("補染", "補髮根", "髮根補色", "補布丁", "布丁頭"),
        "漂髮設計染": ("漂髮設計染", "漂髮", "漂色", "漂染", "特殊色", "耳圈染", "挑染"),
    },
    "target_color": {
        "自然深色": ("自然黑", "自然深色", "深色", "黑色", "深咖"),
        "一般棕色": ("棕色", "咖啡色", "茶色", "可可棕", "奶茶棕"),
        "高明度特殊色": (
            "高明度特殊色",
            "金色",
            "霧金",
            "亞麻金",
            "奶金",
            "銀色",
            "灰色",
            "白金",
            "粉色",
            "藍色",
            "紫色",
            "橘色",
            "紅色",
        ),
    },
    "current_base": {
        "自然黑髮": ("自然黑髮", "黑髮", "原生髮", "沒染過"),
        "已染深色/中深色": ("已染深色", "染過深色", "中深色", "咖啡色底", "深棕底"),
        "已染淺色/已漂過": ("已染淺色", "已漂過", "漂過", "淺色底", "金色底"),
    },
    "bleach_accept": {
        "可接受漂髮": ("可接受漂髮", "可以漂", "可漂", "接受漂", "能漂"),
        "希望不漂髮": ("希望不漂髮", "不想漂", "不要漂", "不漂"),
    },
    "brand_priority": {
        "重視染後髮質修護": ("重視染後髮質修護", "髮質修護", "比較護髮", "髮質優先"),
        "重視顏色表現與CP值": ("重視顏色表現與CP值", "顏色表現", "cp值", "價格優先", "預算優先"),
    },
    "perm_detail": {
        "整體燙髮": ("整體燙髮", "全頭燙", "燙全頭", "燙捲"),
        "髮根燙": ("髮根燙", "髮根蓬鬆", "頭頂扁塌"),
        "燙瀏海": ("燙瀏海", "瀏海燙"),
    },
    "perm_bleached_history": {
        "有漂過": ("有漂過", "漂過", "曾漂過"),
        "沒有漂過": ("沒有漂過", "沒漂過", "未漂過"),
    },
    "treatment_detail": {
        "護髮修護": ("護髮修護", "護髮", "修護", "柔順", "毛躁"),
        "頭皮護理": ("頭皮護理", "頭皮", "頭皮保養"),
    },
    "treatment_combo": {
        "要搭配染燙": ("搭配染燙", "一起染燙", "順便染燙"),
        "不搭配染燙": ("不搭配染燙", "單做", "只做護髮", "不一起染燙"),
    },
    "cut_detail": {
        "全頭剪髮": ("全頭剪髮", "剪短", "修短", "整體修剪"),
        "瀏海修剪": ("瀏海修剪", "剪瀏海", "修瀏海"),
    },
    "restriction": {
        "時間限制": ("趕時間", "時間不要太久", "快一點", "時間限制"),
        "價格限制": ("不要太貴", "希望價格不要太高", "價格限制", "預算有限"),
        "無特別限制": ("沒有特別限制", "都可以", "沒限制"),
    },
}


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

    if provider == "ollama":
        return _get_ollama_reply(
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
    task_ready = _is_task_ready(
        input_mode=input_mode,
        conversation_style=conversation_style,
        history=history,
        message=message,
    )
    allow_inferred_recommendation = _should_finish_consultation(
        input_mode,
        conversation_style,
        user_turn_count,
    )
    if conversation_style == "task":
        allow_inferred_recommendation = task_ready
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
    prompt = build_model_instruction(
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
    parsed = _parse_model_json(text)
    if not parsed:
        return _ai_error_reply("AI 回覆格式暫時無法解析，請再試一次。")

    model_response = _normalize_model_result(parsed, input_mode, source="gemini")
    return _force_final_at_turn_limit(
        model_response,
        input_mode=input_mode,
        conversation_style=conversation_style,
        message=message,
        history=history,
    )


def _get_ollama_reply(input_mode, conversation_style, message, history, system_prompt):
    model = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    endpoint = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat").strip()
    prompt = build_model_instruction(
        input_mode,
        conversation_style,
        system_prompt,
        history=history,
    )
    payload = {
        "model": model,
        "messages": _build_ollama_messages(prompt, message, history),
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.4,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return _ai_error_reply("目前本機 AI 無法回覆，請確認 Ollama 是否已啟動。")

    text = _extract_ollama_text(response_data)
    parsed = _parse_model_json(text)
    if not parsed:
        return _ai_error_reply("本機 AI 回覆格式暫時無法解析，請再試一次。")

    model_response = _normalize_model_result(parsed, input_mode, source="ollama")
    return _force_final_at_turn_limit(
        model_response,
        input_mode=input_mode,
        conversation_style=conversation_style,
        message=message,
        history=history,
    )


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


def _build_ollama_messages(prompt, message, history):
    messages = [{"role": "system", "content": prompt}]

    if isinstance(history, list):
        for item in history[-10:]:
            role = "assistant" if item.get("role") == "assistant" else "user"
            content = (item.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})

    if not messages or messages[-1]["content"] != message:
        messages.append({"role": "user", "content": message})

    return messages


def _extract_gemini_text(response_data):
    try:
        parts = response_data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return ""

    return "".join(part.get("text", "") for part in parts if isinstance(part, dict))


def _extract_ollama_text(response_data):
    try:
        return response_data["message"]["content"]
    except (KeyError, TypeError):
        return ""


def _parse_model_json(text):
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


def _normalize_model_result(result, input_mode, source):
    reply = _sanitize_template_reply(str(result.get("reply") or "").strip())
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
        "source": source,
        "is_final": is_final,
        "final_output": final_output if is_final else None,
    }


def _force_final_at_turn_limit(model_response, input_mode, conversation_style, message, history):
    task_button_mode = _is_task_button_mode(input_mode, conversation_style)
    task_mode = conversation_style == "task"
    task_ready = _is_task_ready(
        input_mode=input_mode,
        conversation_style=conversation_style,
        history=history,
        message=message,
    )
    if task_mode:
        model_response["reply"] = _guard_task_reply_if_not_ready(
            reply=model_response.get("reply") or "",
            ready=task_ready,
            input_mode=input_mode,
            history=history,
            message=message,
        )

    if model_response["is_final"]:
        if task_mode and not task_ready:
            return {
                "reply": _next_task_free_text_question(_conversation_text(history, message)),
                "buttons": model_response.get("buttons") or [],
                "source": model_response.get("source"),
                "is_final": False,
                "final_output": None,
            }
        return model_response

    user_turn_count = _count_user_turns(history)
    conversation_text = _conversation_text(history, message)

    if task_button_mode:
        if task_ready:
            final_output = (
                _build_final_output(conversation_text, allow_inferred_recommendation=True)
                or _build_default_final_output(conversation_text)
            )
            return {
                "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                "buttons": [],
                "source": model_response.get("source"),
                "is_final": True,
                "final_output": final_output,
            }

        if user_turn_count < 12:
            return model_response

        final_output = (
            _build_final_output(conversation_text, allow_inferred_recommendation=True)
            or _build_default_final_output(conversation_text)
        )
        return {
            "reply": "我先用目前已知條件提供保守建議，若你願意可再補充一題讓推薦更精準。",
            "buttons": [],
            "source": model_response.get("source"),
            "is_final": True,
            "final_output": final_output,
        }

    turn_limit = get_turn_limit(input_mode, conversation_style)
    if user_turn_count < turn_limit:
        return model_response

    final_output = (
        _build_final_output(conversation_text, allow_inferred_recommendation=True)
        or _build_default_final_output(conversation_text)
    )

    return {
        "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
        "buttons": [],
        "source": model_response.get("source"),
        "is_final": True,
        "final_output": final_output,
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
    return len(user_turns) + 1


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
    turn_limit = get_turn_limit(input_mode, conversation_style)
    return user_turn_count >= turn_limit


def _is_task_button_mode(input_mode, conversation_style):
    return input_mode == "button" and conversation_style == "task"


def _is_task_ready(input_mode, conversation_style, history, message):
    if conversation_style != "task":
        return False

    if _is_task_button_mode(input_mode, conversation_style):
        return get_task_guided_prompt(history) is None

    conversation_text = _conversation_text(history, message)
    return _is_task_free_text_ready(conversation_text)


def _is_task_button_ready(input_mode, conversation_style, history):
    if not _is_task_button_mode(input_mode, conversation_style):
        return False
    return get_task_guided_prompt(history) is None


def _is_task_free_text_ready(conversation_text):
    text = _normalize_task_free_text(conversation_text)
    if not text:
        return False

    slots = _extract_task_free_text_slots(text)
    direction = slots.get("direction")
    if direction is None:
        return False

    if not slots.get("budget_range"):
        return False

    if direction == "染髮":
        required = ("dye_detail", "target_color", "current_base", "bleach_accept", "brand_priority", "restriction")
        return all(slots.get(field) for field in required)

    if direction == "燙髮":
        required = ("perm_detail", "perm_bleached_history", "restriction")
        return all(slots.get(field) for field in required)

    if direction == "護髮":
        required = ("treatment_detail", "treatment_combo", "restriction")
        return all(slots.get(field) for field in required)

    if direction == "剪髮":
        required = ("cut_detail", "restriction")
        return all(slots.get(field) for field in required)

    return False


def _detect_direction(text):
    normalized_text = _normalize_task_free_text(text)
    if _has_any_phrase(normalized_text, ("染髮", "補染", "漂髮", "髮色")):
        return "染髮"
    if _has_any_phrase(normalized_text, ("燙髮", "捲度", "髮根燙", "燙瀏海")):
        return "燙髮"
    if _has_any_phrase(normalized_text, ("護髮", "頭皮護理", "修護")):
        return "護髮"
    if _has_any_phrase(normalized_text, ("剪髮", "瀏海修剪", "修瀏海")):
        return "剪髮"
    return None


def _has_budget_info(text):
    if _has_any_phrase(text, ("預算", "價位", "以下", "以上")):
        return True
    return re.search(r"\d{3,5}", text) is not None


def _has_any_phrase(text, phrases):
    lowered = (text or "").lower()
    return any((phrase or "").lower() in lowered for phrase in phrases)


def _sanitize_template_reply(reply):
    content = (reply or "").strip()
    if not content:
        return content
    if any(pattern in content for pattern in TEMPLATE_REPLY_PATTERNS):
        return "我需要再確認一個條件，才能準確推薦。請先告訴我你的預算價位區間。"
    return content


def _guard_task_reply_if_not_ready(reply, ready, input_mode, history, message):
    content = _sanitize_template_reply(reply)
    if ready:
        return content

    if input_mode == "text":
        return _next_task_free_text_question(_conversation_text(history, message))

    if _contains_service_name(content):
        return _next_task_free_text_question(_conversation_text(history, message))
    return content or _next_task_free_text_question(_conversation_text(history, message))


def _contains_service_name(text):
    content = (text or "").strip()
    if not content:
        return False
    return any(service_name in content for service_name in SERVICE_HINTS.keys())


def _next_task_free_text_question(conversation_text):
    text = _normalize_task_free_text(conversation_text)
    slots = _extract_task_free_text_slots(text)
    direction = slots.get("direction")
    if direction is None:
        return "你這次主要想做哪一類：染髮、燙髮、護髮還是剪髮？"

    if direction == "染髮":
        if not slots.get("dye_detail"):
            return "你這次染髮比較接近全頭染、補染，還是漂髮設計染？"
        if not slots.get("target_color"):
            return "你想染後的顏色比較接近自然深色、一般棕色，還是高明度特殊色？"
        if not slots.get("current_base"):
            return "你目前的髮色底色是自然黑髮、已染深色/中深色，還是已染淺色/已漂過？"
        if not slots.get("bleach_accept"):
            return "若達到目標色可能需要漂髮，你可以接受嗎？"
        if not slots.get("brand_priority"):
            return "你這次更重視染後髮質修護，還是顏色表現與CP值？"
        if not slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800、1801-2400、2401以上。"
        if not slots.get("restriction"):
            return "你是否還有時間或價格上的限制？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    if direction == "燙髮":
        if not slots.get("perm_detail"):
            return "你想做整體燙髮、髮根燙，還是燙瀏海？"
        if not slots.get("perm_bleached_history"):
            return "你有漂過頭髮嗎？"
        if not slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800、1801-2400、2401以上。"
        if not slots.get("restriction"):
            return "你是否還有時間或價格上的限制？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    if direction == "護髮":
        if not slots.get("treatment_detail"):
            return "你這次比較想做護髮修護，還是頭皮護理？"
        if not slots.get("treatment_combo"):
            return "這次會搭配染燙一起做，還是單做護髮？"
        if not slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800。"
        if not slots.get("restriction"):
            return "你是否還有時間或價格上的限制？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    if direction == "剪髮":
        if not slots.get("cut_detail"):
            return "你這次是全頭剪髮，還是瀏海修剪？"
        if not slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800。"
        if not slots.get("restriction"):
            return "你是否還有時間上的限制？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    return "我需要再確認一個條件，才能準確推薦。你目前最在意的是預算、時間，還是髮況限制？"


def _normalize_task_free_text(text):
    normalized = (text or "").strip()
    if not normalized:
        return normalized

    lowered = normalized.lower()
    for raw, canonical in FREE_TEXT_NORMALIZE_MAP.items():
        lowered = lowered.replace(raw.lower(), canonical)

    return lowered


def _extract_task_free_text_slots(text):
    normalized = _normalize_task_free_text(text)
    slots = {"budget_range": _detect_budget_range(normalized)}

    for slot_key, candidates in TASK_SLOT_KEYWORDS.items():
        slots[slot_key] = _detect_slot_value(normalized, candidates)

    return slots


def _detect_slot_value(text, candidates):
    for canonical, keywords in candidates.items():
        if _has_any_phrase(text, keywords):
            return canonical
    return None


def _detect_budget_range(text):
    if not _has_budget_info(text):
        return None

    if _has_any_phrase(text, ("1200以下", "1200 以下", "千二以下")):
        return "1200以下"
    if _has_any_phrase(text, ("1201-1800", "1201 到 1800", "1201~1800")):
        return "1201-1800"
    if _has_any_phrase(text, ("1801-2400", "1801 到 2400", "1801~2400")):
        return "1801-2400"
    if _has_any_phrase(text, ("2401以上", "2401 以上", "2500以上", "三千以下")):
        return "2401以上"

    return "已提供預算"


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
