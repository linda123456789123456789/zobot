"""Prompt builder for ZOSS chatbot.

The deterministic task-led flow is controlled by button_flow/hermes_client.
Prompts only constrain model output for free-text parsing and topic-led fallback.
"""

from functools import lru_cache
from pathlib import Path

from app.services.service_catalog import SERVICE_OPTIONS

TASK_TURN_LIMIT = 15
TOPIC_TURN_LIMIT = 15
TASK_BUTTON_TURN_LIMIT = 15
TASK_BUTTON_HARD_LIMIT = 12
RECENT_QUESTION_WINDOW = 6

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "ZOSS_AI"
AGENTS_PROMPT_FILE = "Agents.md"
SERVICES_PROMPT_FILE = "Services.md"
TASK_STYLE_PROMPT_FILE = "task_led_system_prompt.md"
TOPIC_STYLE_PROMPT_FILE = "topic_led_system_prompt.md"


def build_system_prompt(input_mode, conversation_style):
    service_list = "\n".join(f"- {name}" for name in SERVICE_OPTIONS.keys())
    return (
        "你是 ZOSS 美髮服務選擇 AI。請用自然、簡潔、具體的繁體中文回覆。\n\n"
        "硬性規則：\n"
        "1. 不可杜撰服務名稱、套餐或價格。\n"
        "2. final_output.recommended_service 必須從服務白名單挑選。\n"
        "3. 每輪只問一個主要問題。\n"
        "4. 資訊足夠時必須收斂成單一推薦。\n"
        "5. 涉及染、燙、漂等化學服務時，需提醒實際仍以現場髮型師評估為準。\n\n"
        f"合法服務白名單：\n{service_list}\n\n"
        f"互動模式：{_input_mode_instruction(input_mode)}\n"
        f"對話風格：{_conversation_style_instruction(conversation_style)}\n"
        f"{_style_operating_rules(input_mode, conversation_style)}"
    )


def build_model_instruction(input_mode, conversation_style, system_prompt, history=None):
    return (
        f"{system_prompt}\n\n"
        f"{_turn_instruction(input_mode, conversation_style, history)}\n"
        "請回傳純 JSON，不要 markdown，不要加 JSON 以外文字。\n"
        f"{_json_schema_instruction(input_mode, conversation_style)}\n"
        "final_output.recommended_service 必須完全等於服務白名單中的名稱。"
    )


def build_task_slot_parser_instruction(system_prompt, current_slots=None):
    return (
        f"{system_prompt}\n\n"
        "你現在只負責 task-led free-text 的 slot parsing，不負責決定主流程，也不負責產生最終推薦。\n"
        "請根據完整對話與使用者最新輸入，抽取使用者已明確表達的 slots。\n"
        "不可猜測使用者沒有說出的資訊。\n"
        "如果使用者問支線問題，side_reply 用 1 到 2 句回答；主流程下一題由後端決定。\n"
        f"目前已知 slots：{current_slots or {}}\n"
        "只能輸出 JSON object，schema：\n"
        "{\n"
        '  "answered_slots": {},\n'
        '  "turn_type": "answer_slot | answer_multiple_slots | side_question | uncertain | irrelevant",\n'
        '  "side_reply": null\n'
        "}\n"
    )


def get_turn_limit(input_mode, conversation_style):
    if input_mode == "button" and conversation_style == "task":
        return TASK_BUTTON_TURN_LIMIT
    if conversation_style == "task":
        return TASK_TURN_LIMIT
    return TOPIC_TURN_LIMIT


def _input_mode_instruction(input_mode):
    if input_mode == "button":
        return "使用者透過按鈕回覆。按鈕流程由後端 controller 控制。"
    return "使用者自由輸入。模型只協助理解語意，主流程仍由後端 controller 控制。"


def _conversation_style_instruction(conversation_style):
    if conversation_style == "task":
        return "task-led：目標是補齊服務選擇所需資訊，快速形成可執行建議。"
    return "topic-led：目標是先協助使用者理解需求脈絡，再形成建議。"


def _style_operating_rules(input_mode, conversation_style):
    if conversation_style == "task" and input_mode == "button":
        return (
            "task-led × button：\n"
            "- 固定任務流程：服務方向 -> 服務細項 -> 必要條件 -> 限制檢核 -> 推薦。\n"
            "- 使用者選不確定時，改問更容易判斷的替代題，再回到主流程。\n"
            "- 不做長篇探索，不詢問感受期待或自我形象。\n"
        )
    if conversation_style == "task":
        return (
            "task-led × free-text：\n"
            "- 自由輸入只改變資訊取得方式，不改變 task-led 主流程。\n"
            "- 從使用者一句話中抽取所有已明確提供的資訊。\n"
            "- 使用者問支線問題時，先簡短回答，再由後端回到下一個必要資訊。\n"
        )
    return (
        "topic-led：\n"
        "- 先釐清使用者想了解的主題，再逐步形成服務建議。\n"
        "- 可以比較服務差異，但不能杜撰不存在的方案。\n"
    )


def _json_schema_instruction(input_mode, conversation_style):
    return (
        "JSON schema：\n"
        "{\n"
        '  "reply": "給使用者看的繁體中文回覆",\n'
        '  "buttons": [],\n'
        '  "is_final": false,\n'
        '  "final_output": null\n'
        "}\n"
        "final_output schema：\n"
        "{\n"
        '  "recommended_service": "白名單服務名稱",\n'
        '  "reason": "推薦理由",\n'
        '  "next_step": "下一步"\n'
        "}\n"
    )


def _turn_instruction(input_mode, conversation_style, history=None):
    turn_count = len([m for m in (history or []) if isinstance(m, dict) and m.get("role") == "user"])
    limit = get_turn_limit(input_mode, conversation_style)
    return f"目前使用者回合數：{turn_count}。上限：{limit}。"


@lru_cache(maxsize=16)
def _prompt_file_exists(filename):
    return (PROMPT_ROOT / filename).exists()
