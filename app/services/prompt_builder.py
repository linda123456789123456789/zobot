import re
from functools import lru_cache
from pathlib import Path

from app.services.service_catalog import SERVICE_OPTIONS

TASK_TURN_LIMIT = 8
TOPIC_TURN_LIMIT = 10
TASK_BUTTON_TURN_LIMIT = 8
TASK_BUTTON_HARD_LIMIT = 12
RECENT_QUESTION_WINDOW = 6
PROMPT_ROOT = Path(__file__).resolve().parents[2] / "ZOSS_AI"
AGENTS_PROMPT_FILE = "Agents.md"
SERVICES_PROMPT_FILE = "Services.md"
TASK_STYLE_PROMPT_FILE = "task_led_system_prompt.md"
TOPIC_STYLE_PROMPT_FILE = "topic_led_system_prompt.md"


def build_system_prompt(input_mode, conversation_style):
    if not _prompt_files_ready():
        return _fallback_system_prompt(input_mode, conversation_style)

    service_list = "\n".join(f"- {name}" for name in SERVICE_OPTIONS.keys())
    style_label = "task-led" if conversation_style == "task" else "topic-led"
    return (
        "你是 ZOSS 美髮服務選擇 AI。請用自然、簡潔、具體的繁體中文回覆。\n"
        f"規則來源：{AGENTS_PROMPT_FILE} + {SERVICES_PROMPT_FILE} + {_style_prompt_filename(conversation_style)}\n\n"
        "硬性規則（不可違反）：\n"
        "1. 服務方案不可自行生成，不可杜撰名稱、套餐、價格。\n"
        "2. final_output.recommended_service 只能從下方白名單挑 1 個。\n"
        "3. 每輪只問 1 個主要問題；不得重複問語意相同的問題。\n"
        "4. 若本輪問到預算，必須要求使用者確認價位區間，不可只問有無預算。\n"
        "5. 資訊足夠或達回合上限時，必須輸出最終推薦（is_final=true）。\n\n"
        "合法服務白名單：\n"
        f"{service_list}\n\n"
        "執行參數：\n"
        f"- 互動模式：{_input_mode_instruction(input_mode)}\n"
        f"- 對話風格：{_conversation_style_instruction(conversation_style)}\n"
        f"- 目前策略：{style_label}\n"
        f"{_style_operating_rules(conversation_style)}\n\n"
        "防重問規則：\n"
        "- 先讀完整歷史再問下一題。\n"
        "- 若上一輪已問過「變化方向 / 變化程度 / 髮質顧慮 / 預算時間」其中任一題軸，下一輪需換題軸。\n"
        "- 使用者回答「不確定」時，改問更容易判斷的替代題，不可原題重問。\n\n"
        "平台相容提醒：\n"
        "- button 模式請回 2 到 4 個選項，系統會自動補上「我不確定」。\n"
        "- button 模式下，reply 必須是可直接對應這些選項的單一問題。\n"
        "- button 模式下，reply 不可引入按鈕以外的第三方向。\n"
        "- 最終推薦後不要再追問。\n"
    )


def build_model_instruction(input_mode, conversation_style, system_prompt, history=None):
    loop_guard = _loop_guard_instruction(history)
    turn_guard = _turn_instruction(input_mode, conversation_style, history)
    return (
        f"{system_prompt}\n"
        f"{loop_guard}"
        f"{turn_guard}\n"
        "請回傳純 JSON，不要 markdown，不要加 JSON 以外文字。\n\n"
        f"{_json_schema_instruction(input_mode)}\n"
        f"{_button_json_instruction(input_mode, conversation_style)}"
        "final_output.recommended_service 必須完全等於服務白名單中的名稱。"
    )


def get_turn_limit(input_mode, conversation_style):
    if input_mode == "button" and conversation_style == "task":
        return TASK_BUTTON_TURN_LIMIT
    if conversation_style == "task":
        return TASK_TURN_LIMIT
    return TOPIC_TURN_LIMIT


def _style_prompt_filename(conversation_style):
    if conversation_style == "task":
        return TASK_STYLE_PROMPT_FILE
    return TOPIC_STYLE_PROMPT_FILE


@lru_cache(maxsize=16)
def _prompt_file_exists(filename):
    path = PROMPT_ROOT / filename
    return path.exists()


def _prompt_files_ready():
    return (
        _prompt_file_exists(AGENTS_PROMPT_FILE)
        and _prompt_file_exists(SERVICES_PROMPT_FILE)
        and _prompt_file_exists(TASK_STYLE_PROMPT_FILE)
        and _prompt_file_exists(TOPIC_STYLE_PROMPT_FILE)
    )


def _fallback_system_prompt(input_mode, conversation_style):
    service_list = "\n".join(f"- {name}" for name in SERVICE_OPTIONS.keys())
    return (
        "你是 ZOBOT，一位自然、簡潔、具體的美髮諮詢助理。"
        "請像正在和顧客對話，不要像問卷或客服公告。\n\n"
        "你只能根據下列店家服務提供建議，不要編造不存在的服務；"
        "final_output.recommended_service 必須從白名單挑選：\n"
        f"{service_list}\n\n"
        f"互動模式：{_input_mode_instruction(input_mode)}\n"
        f"對話風格：{_conversation_style_instruction(conversation_style)}\n"
        f"{_style_operating_rules(conversation_style)}\n\n"
        "共通規則：\n"
        "- 根據完整對話上下文決定下一步，不要只看最後一句。\n"
        "- 每一輪只做一件事：先承接使用者，再問一個新資訊點。\n"
        "- 不得重複詢問語意相同的問題；若資訊不足，請換一個更好回答的角度。\n"
        "- 使用者選「我不確定」時，請降低假設，改問更容易判斷的問題，不要強行推薦。\n"
        "- 使用者明確拒絕或不可接受的條件屬於硬限制（hard constraints），最終推薦不可違反。\n"
        "- 不要替使用者完成預約或服務選擇；最後選擇只能由頁面左側服務卡片完成。\n"
        "- 資訊足夠時，必須收斂並給一個 final_output；不要無限延伸對話。\n"
        "- final_output.reason 必須同時說明：使用者需求 + 服務特色如何對應 + 主要取捨後果，且至少包含一個因果句。\n"
        "- 涉及染/燙/漂等化學服務時，reason 或 next_step 必須加上「實際仍以現場髮型師評估為準」。\n"
        "- 一律使用繁體中文。\n"
    )


def _input_mode_instruction(input_mode):
    if input_mode == "button":
        return (
            "使用者透過按鈕回覆。reply 要簡短明確，"
            "並在資訊不足時提供 2 到 4 個符合上下文的按鈕選項。"
        )

    return "使用者自由輸入。請自然追問、摘要與收斂建議。"


def _conversation_style_instruction(conversation_style):
    if conversation_style == "task":
        return "task-led：目標是快速完成服務選擇，補齊必要資訊後盡快給可執行建議。"
    return "topic-led：目標是先幫使用者釐清需求，再整合成服務建議。"


def _style_operating_rules(conversation_style):
    if conversation_style == "task":
        return (
            "task-led（任務導向，快收斂）：\n"
            "- 目標：快速完成一項可預約服務方案，不做需求探索。\n"
            "- 任務流程：服務方向 -> 服務細項 -> 必要條件 -> 限制檢核 -> 推薦。\n"
            "- 每次最多問一個問題；每次回覆控制在 80 字內。\n"
            "- 採完成制：資訊足夠就推薦；資訊不足就追問缺口，不做固定 5 輪硬結束。\n"
            "- 追問輪數通常約 6 到 8 輪；若使用者多次不確定，可延伸到 10 輪內。\n"
            "- 在資訊尚未齊全前，不可列出具體方案名稱（例如日本資生堂染髮）。\n"
            "- 涉及預算時必須使用價位區間題（例如 1200以下/1201-1800/1801-2400/2401以上）。\n"
            "- 推薦格式固定為：推薦服務、推薦理由、注意事項。\n"
            "- 推薦理由必須用「根據你選擇的條件」說明，不可用風格探索語言。\n"
            "- 推薦理由應包含一段比較語句，說明為何選此方案而非另一個常見替代方案。\n"
            "- 若出現需求衝突（例如想高明度但不漂髮），優先遵守顧客明確限制，再說明效果差異與可行替代。\n"
            "- 禁止：詢問改變原因、感受期待、自我形象、長篇顧問比較。"
        )

    return (
        "topic-led（主題導向，先釐清）：\n"
        "- 目標：先釐清需求脈絡，再形成建議，不急著分類服務。\n"
        "- 問題順序：動機/情境 -> 偏好權衡 -> 顧慮來源 -> 推薦。\n"
        "- 問句型態：開放式或比較式。\n"
        "- 禁止：前兩輪直接問預算、預約時段、指定設計師。\n"
        "- 收斂門檻：釐清至少 3 個面向（動機、偏好、顧慮、維護）後，整合為單一推薦。"
    )


def _button_json_instruction(input_mode, conversation_style):
    if input_mode != "button":
        return ""

    style_hint = (
        "- task-led 按鈕要偏封閉與決策導向，例如「自然色」「明顯變化」。\n"
        "- task-led 在蒐集階段（is_final=false）禁止提供任何具體服務名稱按鈕。\n"
        if conversation_style == "task"
        else "- topic-led 按鈕要偏探索與比較導向，例如「重視低維護」「重視變化感」。\n"
    )
    return (
        "這是按鈕模式。當 is_final 為 false 時：\n"
        "- buttons 請提供 2 到 4 個選項，系統會自動補上「我不確定」。\n"
        "- 選項必須同一題軸、互斥可判斷，不要固定模板，不要每輪都一樣。\n"
        "- reply 必須圍繞這些選項提問，且可讓使用者直接從選項作答。\n"
        "- reply 中不得引入按鈕外的新方向（第三選項、額外問題或新服務）。\n"
        "- 若本輪題軸是預算，buttons 必須是價位區間，不可只給「預算範圍」這種抽象選項。\n"
        "- 建議 reply 使用這種句型：「請選擇最接近你的情況。」\n"
        "- 如果是 topic-led，可先做一句需求詮釋，再接選項題；但問題仍須對應當輪按鈕。\n"
        "- 如果是 task-led，直接用決策題提問，不要先給長段建議。\n"
        f"{style_hint}"
        "- 若使用者剛選「我不確定」，選項要更寬鬆、容易判斷。\n"
        "- 每個選項盡量 4 到 12 個中文字。\n"
        "- 不要在 buttons 中放「我不確定」。\n"
        "當 is_final 為 true 時，不要回傳 buttons。\n"
    )


def _json_schema_instruction(input_mode):
    button_field = '  "buttons": ["選項一", "選項二", "選項三"],\n' if input_mode == "button" else ""
    allowed_services = ", ".join(SERVICE_OPTIONS.keys())
    button_mapping_rule = (
        "button 模式額外規則：reply 必須是一個可被 buttons 直接回答的單一問題。\n"
        if input_mode == "button"
        else ""
    )
    return (
        f"recommended_service 合法值：{allowed_services}\n"
        f"{button_mapping_rule}"
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
        '    "recommended_service": "白名單中的其中一項服務名稱",\n'
        '    "reason": "根據使用者需求與服務特色的具體原因",\n'
        '    "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。"\n'
        "  }\n"
        "}\n"
        "當 is_final=true 時，final_output 不可為 null，且必須只推薦一個方案。\n"
    )


def _turn_instruction(input_mode, conversation_style, history):
    current_turn = _count_user_turns(history)
    phase_instruction = _phase_instruction(input_mode, conversation_style, current_turn)
    if input_mode == "button" and conversation_style == "task":
        if current_turn < TASK_BUTTON_HARD_LIMIT:
            return (
                f"{phase_instruction}"
                "結束條件：僅在必要資訊已齊全時輸出 is_final=true；否則持續追問缺口。\n"
            )
        return (
            f"{phase_instruction}"
            f"目前已達第 {current_turn} 輪（安全上限 {TASK_BUTTON_HARD_LIMIT}）。\n"
            "若仍有缺漏，請基於現有資訊做保守推薦並清楚標示注意事項。\n"
            "is_final 必須是 true，不要回傳 buttons。\n"
        )

    turn_limit = get_turn_limit(input_mode, conversation_style)
    if current_turn < turn_limit:
        return phase_instruction

    return (
        f"{phase_instruction}"
        f"目前使用者已回答第 {current_turn} 輪，已達此情境上限。\n"
        "這一輪必須停止追問，請根據目前完整對話整理 final_output。\n"
        "如果資訊仍不完整，請基於最明確的需求給出保守建議，並在 reason 說明依據。\n"
        "is_final 必須是 true，不要回傳 buttons。\n"
    )


def _task_button_step_instruction(current_turn):
    if current_turn <= 1:
        return (
            "task+button Step 1：詢問服務方向。"
            "選項可用：染髮、護髮、燙髮。\n"
            "若使用者選不確定，下一輪改問分類題（改變髮色 / 改變髮型 / 改善髮質）。\n"
        )
    if current_turn == 2:
        return (
            "task+button Step 2：根據已判斷的服務方向詢問服務細項。"
            "例如染髮可問全頭染/補染/漂髮設計染。\n"
        )
    if current_turn == 3:
        return (
            "task+button Step 3：詢問必要條件（依方向分支）。\n"
            "- 染髮：目標色系 / 目前底色 /（必要時）可否漂髮 / 預算。\n"
            "- 燙髮：是否漂過 / 是否懷孕 / 預算。\n"
            "- 護髮：先問髮絲需求細項（受損修護/柔順抗毛躁/日常保養），再問預算。\n"
        )
    if current_turn == 4:
        return (
            "task+button Step 4：做限制檢核。"
            "若涉及染/燙/漂，必查懷孕、曾漂想燙、嚴重受損等限制並標記現場評估。\n"
        )
    return (
        "task+button Step 5：檢查必填欄位是否已完整。\n"
        "若完整就推薦；若未完整就只追問缺漏欄位，不可改問無關題。\n"
    )


def _phase_instruction(input_mode, conversation_style, current_turn):
    if input_mode == "button" and conversation_style == "task":
        return _task_button_step_instruction(current_turn)

    if conversation_style == "task":
        if current_turn <= 2:
            return (
                "本輪 task-led 要求：先確認服務方向（染髮/補染/漂髮/燙髮/護髮）。"
                "只問一個能直接推進決策的封閉式問題。\n"
            )
        if current_turn <= 3:
            return (
                "本輪 task-led 要求：確認服務細項。"
                "若使用者不確定，改用情境分類協助判斷。\n"
            )
        if current_turn <= 4:
            return (
                "本輪 task-led 要求：確認必要條件與限制檢核（預算/時間/髮況/懷孕/漂髮相關）。"
                "避免回頭重問已回答的項目。\n"
            )
        return (
            "本輪 task-led 要求：若核心資訊已足夠，直接輸出單一推薦；"
            "除非仍缺關鍵執行條件，否則不要再追問。\n"
        )

    if current_turn <= 3:
        return (
            "本輪 topic-led 要求：先承接使用者語意，再問一個開放或比較問題，"
            "幫助釐清動機、偏好或顧慮。\n"
        )
    if current_turn <= 5:
        return (
            "本輪 topic-led 要求：把前面釐清到的重點做一句摘要，"
            "再問一個收斂問題，逐步形成方向。\n"
        )
    return "本輪 topic-led 要求：若已釐清三個面向，應優先整合為單一推薦，不要延伸新話題。\n"


def _loop_guard_instruction(history):
    questions = _extract_recent_assistant_questions(history)
    if not questions:
        return ""
    bullet_list = "\n".join(f"- {question}" for question in questions)
    return (
        "防繞圈檢查（先執行）：\n"
        "以下問題已在前文問過，下一題不得語意重複：\n"
        f"{bullet_list}\n"
        "若仍資訊不足，請改問下一個尚未覆蓋的資訊點。\n"
    )


def _extract_recent_assistant_questions(history):
    if not isinstance(history, list):
        return []

    collected = []
    seen = set()
    for item in reversed(history[-14:]):
        if item.get("role") != "assistant":
            continue
        content = (item.get("content") or "").strip()
        if not content:
            continue
        for line in content.splitlines():
            sentence = line.strip(" \t-")
            if not sentence:
                continue
            if "？" not in sentence and "?" not in sentence and not sentence.endswith(("嗎", "呢", "還是")):
                continue
            normalized = _normalize_question(sentence)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            collected.append(sentence)
            if len(collected) >= RECENT_QUESTION_WINDOW:
                return list(reversed(collected))

    return list(reversed(collected))


def _normalize_question(text):
    normalized = re.sub(r"\s+", "", text)
    normalized = re.sub(r"[?？!！,，。:：;；「」『』（）()]", "", normalized)
    return normalized


def _count_user_turns(history):
    if not isinstance(history, list):
        return 1

    user_turns = [item for item in history if item.get("role") == "user"]
    return len(user_turns) + 1
