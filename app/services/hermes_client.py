"""Chatbot gateway for ZOSS.

This version keeps the public get_chatbot_reply interface but removes the old
mixed controller/AI-led task logic. Task-led button and task-led free-text now
share one deterministic slot pipeline:
history/message -> slots -> next prompt or catalog-based recommendation.
"""

import json
import os
import re
import urllib.error
import urllib.request

from app.services.button_flow import (
    TASK_SLOT_ENUMS,
    UNCERTAIN,
    extract_task_slots_from_history,
    get_task_guided_prompt,
    is_task_ready,
    merge_slots,
    next_prompt_key,
)
from app.services.prompt_builder import build_task_slot_parser_instruction
from app.services.service_catalog import (
    SERVICE_CATEGORIES,
    SERVICE_HINTS,
    SERVICE_OPTIONS,
    get_service_by_name,
    recommend_service_from_slots,
)

MAX_BUTTON_OPTIONS = 5
BUDGET_NO_PREFERENCE = "預算不確定"
ONSITE_EVALUATION_NOTE = "實際可行性、藥劑選擇與髮況風險仍需以現場髮型師評估為準。"

KEYWORD_MAP = {
    "direction": {
        "染髮": ("染髮", "染頭髮", "染发", "換髮色", "換顏色", "上色", "髮色"),
        "燙髮": ("燙髮", "燙頭髮", "燙捲", "捲度", "髮根燙", "瀏海燙"),
        "護髮": ("護髮", "修護", "護理", "保養", "毛躁", "打結"),
    },
    "dye_detail": {
        "全頭染": ("全頭染", "整頭染", "整頭換色", "全染", "全部染"),
        "補染": ("補染", "補髮根", "髮根補色", "補布丁", "布丁頭"),
        "漂髮設計染": ("漂髮設計染", "漂髮", "漂色", "漂染", "特殊色", "耳圈染", "挑染"),
    },
    "target_color": {
        "自然深色": ("自然黑", "黑茶", "自然深色", "深色", "深咖", "低調"),
        "一般棕色": ("棕色", "咖啡", "茶色", "可可", "奶茶棕", "巧克力"),
        "高明度特殊色": ("高明度", "特殊色", "金色", "亞麻", "銀色", "灰色", "白金", "粉色", "藍色", "紫色", "橘色", "紅色"),
    },
    "current_base": {
        "自然黑髮": ("自然黑髮", "黑髮", "原生髮", "沒染過", "沒有染過"),
        "已染深色/中深色": ("染過深色", "中深色", "深棕", "咖啡色底", "暗色"),
        "已染淺色/已漂過": ("已染淺色", "已漂過", "漂過", "淺色底", "金髮", "金色頭髮", "目前很淺"),
    },
    "bleach_accept": {
        "可接受漂髮": ("可以漂", "可漂", "接受漂", "能漂", "願意漂"),
        "希望不漂髮": ("不想漂", "不要漂", "不漂", "不希望漂", "不能漂"),
    },
    "brand_priority": {
        "重視染後髮質修護": ("髮質", "修護", "不要太乾", "怕傷髮", "柔順"),
        "重視顏色表現與CP值": ("顏色表現", "顯色", "cp", "划算", "價格", "預算"),
        "兩者都重視": ("都重視", "都重要", "兩個都", "髮質和顏色"),
    },
    "perm_detail": {
        "整體燙髮": ("整體燙", "全頭燙", "燙全頭", "燙捲", "整頭燙"),
        "髮根燙": ("髮根燙", "燙髮根", "頭頂塌", "扁塌", "蓬鬆"),
        "燙瀏海": ("燙瀏海", "瀏海燙", "整理瀏海"),
    },
    "perm_blocker": {
        "曾經漂過頭髮": ("漂過", "有漂", "曾經漂"),
        "目前懷孕": ("懷孕", "孕婦"),
        "髮質嚴重受損或容易斷裂": ("嚴重受損", "斷裂", "容易斷", "爛掉"),
        "以上皆無": ("以上皆無", "都沒有", "沒有這些", "無"),
    },
    "perm_preference": {
        "平衡預算，完成基本燙髮造型": ("平衡預算", "基本", "預算優先", "便宜", "價格"),
        "重視燙後髮質、柔順度與修護感": ("燙後髮質", "修護", "柔順", "質感", "髮質優先"),
    },
    "treatment_detail": {
        "受損修護": ("受損", "染燙受損", "髮尾乾", "髮尾毛裂", "斷裂", "深層修護"),
        "柔順抗毛躁": ("柔順", "毛躁", "打結", "觸感", "自然捲"),
        "日常保養": ("日常保養", "基礎保養", "光澤", "入門", "維持"),
    },
}


def get_chatbot_reply(input_mode, conversation_style, message, history, system_prompt):
    if conversation_style == "task":
        if input_mode == "button":
            return _get_task_button_reply(message, history)
        return _get_task_text_reply(message, history, system_prompt)

    return _get_topic_reply(input_mode, conversation_style, message, history, system_prompt)


def _get_task_button_reply(message, history):
    effective_history = _history_with_latest_user_message(history, message)
    slots = extract_task_slots_from_history(effective_history)
    if is_task_ready(slots):
        return _final_response(slots, source="task_button_controller_final")

    prompt = get_task_guided_prompt(effective_history)
    if prompt:
        return {
            "reply": prompt["question"],
            "buttons": _trim_buttons(prompt["buttons"]),
            "source": "task_button_controller",
            "is_final": False,
            "final_output": None,
            "debug_slots": slots if _debug_enabled() else None,
        }

    return _final_response(slots, source="task_button_controller_final")


def _get_task_text_reply(message, history, system_prompt):
    latest_message = str(message or "").strip()
    base_slots = _task_text_slots_from_history(history)

    parser_slots, side_reply = _parse_task_text_with_model_if_available(
        latest_message=latest_message,
        history=history,
        system_prompt=system_prompt,
        current_slots=base_slots,
    )
    rule_slots = _parse_task_text_by_rules(latest_message)
    slots = merge_slots(base_slots, rule_slots)
    slots = merge_slots(slots, parser_slots)

    if is_task_ready(slots):
        return _final_response(slots, source="task_text_controller_final")

    next_key = next_prompt_key(slots)
    question = _text_question_for_prompt_key(next_key)
    if side_reply:
        reply = f"{side_reply} {question}"
    else:
        reply = question

    return {
        "reply": reply,
        "buttons": [],
        "source": "task_text_controller",
        "is_final": False,
        "final_output": None,
        "debug_slots": slots if _debug_enabled() else None,
    }


def _final_response(slots, source):
    final_output = recommend_service_from_slots(slots)
    return {
        "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
        "buttons": [],
        "source": source,
        "is_final": True,
        "final_output": final_output,
        "debug_slots": slots if _debug_enabled() else None,
    }



def _task_text_slots_from_history(history):
    slots = extract_task_slots_from_history(history)
    for item in _messages(history):
        if item.get("role") == "user":
            slots = merge_slots(slots, _parse_task_text_by_rules(item.get("content", "")))
    return slots


def _parse_task_text_by_rules(message):
    text = _normalize_text(message)
    slots = {}

    budget = _extract_budget_range(text)
    if budget:
        slots["budget_range"] = budget

    for slot, value_map in KEYWORD_MAP.items():
        for value, keywords in value_map.items():
            if any(_normalize_text(keyword) in text for keyword in keywords):
                slots.setdefault(slot, value)

    # Broad direction fallback for natural phrasing such as "想整頭染奶茶棕".
    if "direction" not in slots:
        if "染" in text and "燙" not in text:
            slots["direction"] = "染髮"
        elif "燙" in text:
            slots["direction"] = "燙髮"
        elif any(token in text for token in ("護", "修護", "保養", "毛躁", "打結")):
            slots["direction"] = "護髮"

    # Correct common over-fill: "漂過" in current-base context should not automatically mean perm blocker
    # unless the direction is perm or the user is answering a perm blocker question.
    if slots.get("direction") == "染髮" and slots.get("perm_blocker") == "曾經漂過頭髮":
        slots.pop("perm_blocker", None)

    return slots


def _parse_task_text_with_model_if_available(latest_message, history, system_prompt, current_slots):
    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    if provider not in {"openai", "gemini", "ollama"}:
        return {}, None

    prompt = build_task_slot_parser_instruction(system_prompt, current_slots=current_slots)
    raw = _call_json_model(provider, prompt, latest_message, history)
    if not raw:
        return {}, None

    parsed = _parse_json_object(raw)
    if not isinstance(parsed, dict):
        return {}, None

    answered = parsed.get("answered_slots") or {}
    valid_slots = {}
    for key, value in answered.items():
        if value is None or value == "":
            continue
        if key in TASK_SLOT_ENUMS and value in TASK_SLOT_ENUMS[key]:
            valid_slots[key] = value

    side_reply = parsed.get("side_reply")
    if side_reply is not None:
        side_reply = str(side_reply).strip()[:120]
    return valid_slots, side_reply


def _call_json_model(provider, prompt, latest_message, history):
    if provider == "openai":
        return _call_openai_json(prompt, latest_message, history)
    if provider == "gemini":
        return _call_gemini_json(prompt, latest_message, history)
    if provider == "ollama":
        return _call_ollama_json(prompt, latest_message, history)
    return None


def _call_openai_json(prompt, latest_message, history):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "messages": _chat_messages(prompt, latest_message, history),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    return _post_json_and_extract_text(endpoint, payload, {"Authorization": f"Bearer {api_key}"})


def _call_gemini_json(prompt, latest_message, history):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    text = "\n".join([prompt, _history_text(history), f"使用者最新輸入：{latest_message}"])
    payload = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"},
    }
    return _post_json_and_extract_text(endpoint, payload, {"x-goog-api-key": api_key})


def _call_ollama_json(prompt, latest_message, history):
    endpoint = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
    model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    payload = {
        "model": model,
        "messages": _chat_messages(prompt, latest_message, history),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    return _post_json_and_extract_text(endpoint, payload, {})


def _post_json_and_extract_text(endpoint, payload, headers):
    request_headers = {"Content-Type": "application/json", **headers}
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    if "choices" in data:
        return data["choices"][0].get("message", {}).get("content", "")
    if "candidates" in data:
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)
    if "message" in data:
        return data.get("message", {}).get("content", "")
    if "response" in data:
        return data.get("response", "")
    return None


def _topic_reply(input_mode, conversation_style, message, history, system_prompt):
    text = str(message or "").strip()
    lower = _normalize_text(text)
    candidates = []
    for service_name, details in SERVICE_HINTS.items():
        score = 0
        for keyword in details.get("keywords", []):
            if _normalize_text(keyword) in lower:
                score += 2
        if details.get("category") and details["category"] in text:
            score += 1
        if score:
            candidates.append((score, service_name))
    candidates.sort(reverse=True)

    if len([m for m in _messages(history) if m.get("role") == "user"]) >= 4 and candidates:
        service_name = candidates[0][1]
        service = get_service_by_name(service_name) or {}
        return {
            "reply": "我已根據目前討論整理出一個參考建議，請查看下方摘要。",
            "buttons": [],
            "source": "topic_controller_final",
            "is_final": True,
            "final_output": {
                "recommended_service": service_name,
                "reason": f"你目前討論的重點與「{service_name}」較接近。{service.get('description', '')}",
                "next_step": "可再依現場髮況與設計師評估確認是否適合。",
            },
        }

    return {
        "reply": "你可以先描述目前髮況、想改變的地方，或想比較的服務差異。",
        "buttons": ["染燙護差異", "依照髮況選擇", "價格與效果比較"] if input_mode == "button" else [],
        "source": "topic_controller",
        "is_final": False,
        "final_output": None,
    }


def _get_topic_reply(input_mode, conversation_style, message, history, system_prompt):
    return _topic_reply(input_mode, conversation_style, message, history, system_prompt)


def _text_question_for_prompt_key(prompt_key):
    from app.services.button_flow import TASK_PROMPTS

    if not prompt_key:
        return "我已取得足夠資訊，可以整理推薦。"
    prompt = TASK_PROMPTS.get(prompt_key) or {}
    question = prompt.get("question", "")
    # Free-text should not sound like button-only UI.
    return question.replace("請選擇", "請告訴我").replace("你可接受", "你是否可接受")


def _extract_budget_range(text):
    if any(keyword in text for keyword in ("不限", "都可以", "都可", "沒有限制", "不確定預算", "預算不確定")):
        return "預算不確定"

    numbers = [int(num) for num in re.findall(r"\d{3,5}", text.replace(",", ""))]
    if not numbers:
        return None
    amount = max(numbers)
    if amount <= 1200:
        return "1200 以下"
    if amount <= 1800:
        return "1201-1800"
    if amount <= 2400:
        return "1801-2400"
    return "2401 以上"


def _parse_json_object(text):
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def _chat_messages(prompt, latest_message, history):
    messages = [{"role": "system", "content": prompt}]
    for item in _messages(history)[-10:]:
        role = item.get("role")
        if role in {"user", "assistant"}:
            messages.append({"role": role, "content": str(item.get("content", ""))})
    messages.append({"role": "user", "content": latest_message})
    return messages


def _history_text(history):
    lines = []
    for item in _messages(history)[-10:]:
        role = item.get("role", "")
        content = item.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _history_with_latest_user_message(history, message):
    result = list(_messages(history))
    latest = str(message or "").strip()
    if latest:
        if not result or result[-1].get("role") != "user" or str(result[-1].get("content")) != latest:
            result.append({"role": "user", "content": latest})
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
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            result.append({"role": item[0], "content": item[1]})
    return result


def _normalize_text(text):
    return str(text or "").strip().lower().replace(" ", "")


def _trim_buttons(buttons):
    result = []
    for button in buttons or []:
        if button not in result:
            result.append(button)
    return result[:MAX_BUTTON_OPTIONS]


def _debug_enabled():
    return os.getenv("CHATBOT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
