import json
import os
import re
from functools import lru_cache
import urllib.error
import urllib.request

from app.services.button_flow import get_task_guided_prompt
from app.services.prompt_builder import build_model_instruction, get_turn_limit
from app.services.service_catalog import RECOMMENDATION_RULES, SERVICE_CATEGORIES, SERVICE_HINTS


MAX_BUTTON_OPTIONS = 5
UNCERTAIN_BUTTON_LABEL = "我不確定"
BUDGET_NO_PREFERENCE = "預算不確定"
TEMPLATE_REPLY_PATTERNS = (
    "自然、簡潔的下一句回覆",
    "自然, 簡潔的下一句回覆",
)
ONSITE_EVALUATION_NOTE = "實際可行性、藥劑選擇與髮況風險仍需以現場髮型師評估為準。"


def _debug_enabled():
    return os.getenv("CHATBOT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_log(event, **fields):
    if not _debug_enabled():
        return
    details = ", ".join(f"{key}={value}" for key, value in fields.items())
    print(f"[ZOBOT_DEBUG] {event}" + (f" | {details}" if details else ""), flush=True)
FREE_TEXT_NORMALIZE_MAP = {
    "染頭髮": "染髮",
    "染发": "染髮",
    "染法": "染髮",
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
    "漂色": "漂髮設計染",
    "漂染": "漂髮設計染",
    "是，主要在頭皮三公分內": "補染",
    "是主要在頭皮三公分內": "補染",
    "不是，超過三公分或接近全頭": "全頭染",
    "不是超過三公分或接近全頭": "全頭染",
    "全染": "全頭染",
    "整體燙": "整體燙髮",
    "燙全頭": "整體燙髮",
    "燙頭髮": "燙髮",
    "護理": "護髮",
    "做護髮": "護髮",
    "護髮修護": "受損修護",
    "頭皮護理": "日常保養",
}

TASK_SLOT_KEYWORDS = {
    "direction": {
        "染髮": ("染髮", "染髮", "染发", "上色", "換髮色", "換顏色", "髮色"),
        "燙髮": ("燙髮", "燙头髮", "燙捲", "捲度", "燙"),
        "護髮": ("護髮", "修護", "護理", "保養"),
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
            "特殊色",
        ),
    },
    "current_base": {
        "自然黑髮": ("自然黑髮", "黑髮", "原生髮", "沒染過"),
        "已染深色/中深色": ("已染深色", "染過深色", "中深色", "咖啡色底", "深棕底"),
        "已染淺色/已漂過": (
            "已染淺色",
            "已漂過",
            "漂過",
            "淺色底",
            "金色底",
            "金色髮色",
            "金色頭髮",
            "金髮",
            "目前是金色",
        ),
    },
    "bleach_accept": {
        "可接受漂髮": ("可接受漂髮", "可以漂", "可漂", "接受漂", "能漂", "可以接受漂髮"),
        "希望不漂髮": ("希望不漂髮", "不想漂", "不要漂", "不漂", "不行", "不可以"),
    },
    "brand_priority": {
        "重視染後髮質修護": ("重視染後髮質修護", "髮質修護", "比較護髮", "髮質優先"),
        "重視顏色表現與CP值": ("重視顏色表現與CP值", "顏色表現", "cp值", "價格優先", "預算優先"),
        "兩者都重視": ("兩者都重視", "都想要", "兩個都想要", "都重要"),
    },
    "tradeoff_priority": {
        "以預算為優先": ("以預算為優先", "以價位為優先", "價位優先", "預算優先", "以預算為主", "以價格為主"),
        "以效果為優先": ("以效果為優先", "以染後護理為優先", "以染後護髮為優先", "護理優先", "護髮優先", "髮質優先", "染後修護優先", "以護理為主", "效果優先"),
        "我不確定": ("我不確定", "不確定"),
    },
    "perm_detail": {
        "整體燙髮": ("整體燙髮", "全頭燙", "燙全頭", "燙捲", "整頭燙"),
        "髮根燙": ("髮根燙", "燙髮根", "髮根蓬鬆", "頭頂扁塌"),
        "燙瀏海": ("燙瀏海", "瀏海燙"),
    },
    "perm_blocker": {
        "曾經漂過頭髮": ("曾經漂過頭髮", "有漂過", "漂過", "曾漂過", "漂髮過"),
        "目前懷孕": ("目前懷孕", "懷孕中", "孕婦"),
        "髮質嚴重受損或容易斷裂": ("髮質嚴重受損", "容易斷裂", "嚴重受損", "斷裂"),
        "以上皆無": ("以上皆無", "都沒有", "無", "沒有"),
    },
    "perm_preference": {
        "平衡預算，完成基本燙髮造型": ("平衡預算", "基本燙髮造型", "預算優先", "先求有造型"),
        "重視燙後髮質、柔順度與修護感": (
            "重視燙後髮質",
            "柔順度",
            "修護感",
            "質感優先",
            "髮質優先",
            "重視髮質",
            "重視髮質修護",
            "在意髮質",
            "我在意髮質",
            "髮質很重要",
            "重視修護",
            "修護優先",
        ),
        "不確定": ("不確定", "不確定，請用預算判斷"),
    },
    "treatment_detail": {
        "受損修護": ("受損修護", "護髮修護", "深層修護", "染燙受損", "髮尾毛裂", "髮尾乾燥", "受損"),
        "柔順抗毛躁": ("柔順抗毛躁", "柔順", "毛躁", "打結", "觸感"),
        "日常保養": ("日常保養", "入門護髮", "基礎修護", "光澤", "保養"),
    },
}
TASK_SLOT_ENUMS = {
    "direction": ("染髮", "燙髮", "護髮"),
    "dye_detail": ("全頭染", "補染", "漂髮設計染"),
    "target_color": ("自然深色", "一般棕色", "高明度特殊色"),
    "current_base": ("自然黑髮", "已染深色/中深色", "已染淺色/已漂過"),
    "bleach_accept": ("可接受漂髮", "希望不漂髮"),
    "brand_priority": ("重視染後髮質修護", "重視顏色表現與CP值", "兩者都重視"),
    "tradeoff_priority": ("以預算為優先", "以效果為優先", "我不確定"),
    "perm_detail": ("整體燙髮", "髮根燙", "燙瀏海"),
    "perm_blocker": ("曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂", "以上皆無"),
    "perm_preference": ("平衡預算，完成基本燙髮造型", "重視燙後髮質、柔順度與修護感", "不確定"),
    "treatment_detail": ("受損修護", "柔順抗毛躁", "日常保養"),
}
PERM_HARD_BLOCKERS = {"曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂"}


# Step 11: semantic slot schemas.
# These schemas are used only as a bounded fallback for the current FSM slot.
# They do not decide flow, fill other slots, or recommend services.
SEMANTIC_SLOT_SCHEMAS = {
    "dye_detail": {
        "allowed_values": TASK_SLOT_ENUMS["dye_detail"],
        "slot_description": "判斷使用者這次染髮需求是全頭染、補染，或需要漂髮/設計染。",
        "examples": {
            "全頭染": ("整顆頭都要換色", "想整體換一個髮色", "全部重新染", "不是只補髮根"),
            "補染": ("只補新長出來的髮根", "布丁頭想處理", "只補頭頂長出來的地方", "只補根部"),
            "漂髮設計染": ("想做耳圈染", "想挑染", "想做特殊色設計", "需要漂的造型染"),
        },
        "reject_rule": "若訊息只是在問價格、品牌、髮質、預算或顏色深淺，不可分類為 dye_detail。",
    },
    "target_color": {
        "allowed_values": TASK_SLOT_ENUMS["target_color"],
        "slot_description": "判斷使用者想要的目標髮色屬於自然深色、一般棕色，或高明度特殊色。",
        "examples": {
            "自然深色": ("自然黑茶", "深咖啡", "低調一點", "看起來像沒染但有質感", "黑茶色"),
            "一般棕色": ("可可色", "巧克力色", "奶茶咖", "霧棕", "茶棕", "焦糖棕"),
            "高明度特殊色": ("米金色", "淺亞麻", "灰霧色", "粉棕偏粉", "藍黑偏藍", "紫灰", "銀灰"),
        },
        "reject_rule": "若訊息描述的是目前底色而非想染成的顏色，不可分類為 target_color。",
    },
    "current_base": {
        "allowed_values": TASK_SLOT_ENUMS["current_base"],
        "slot_description": "判斷使用者目前髮色/底色是自然黑髮、已染深色/中深色，或已染淺色/已漂過。",
        "examples": {
            "自然黑髮": ("沒有染過", "原本髮色", "自然黑", "沒漂也沒染"),
            "已染深色/中深色": ("之前染過咖啡", "現在偏深棕", "有染過深色", "目前是暗色系"),
            "已染淺色/已漂過": ("之前漂過", "現在很淺", "退成金色", "漂過一次", "目前髮尾很亮"),
        },
        "reject_rule": "若訊息描述的是想染成的目標顏色而非目前底色，不可分類為 current_base。",
    },
    "bleach_accept": {
        "allowed_values": TASK_SLOT_ENUMS["bleach_accept"],
        "slot_description": "判斷使用者是否接受漂髮。",
        "examples": {
            "可接受漂髮": ("可以為了顏色漂", "願意漂一次", "需要的話可以漂", "能接受漂髮"),
            "希望不漂髮": ("不想傷頭髮所以不要漂", "盡量不要漂", "不能漂", "不希望漂", "不要漂比較好"),
        },
        "reject_rule": "若訊息只是在描述曾經漂過或目前底色，不可分類為 bleach_accept。",
    },
    "brand_priority": {
        "allowed_values": TASK_SLOT_ENUMS["brand_priority"],
        "slot_description": "判斷使用者選染髮方案時更重視染後髮質修護、顏色表現/CP值，或兩者都重視。",
        "examples": {
            "重視染後髮質修護": ("希望染完不要太乾", "怕髮質變差", "比較在意護髮感", "頭髮已經受損想保守"),
            "重視顏色表現與CP值": ("想顏色明顯一點", "希望划算", "預算有限但想有效果", "比較在意顯色"),
            "兩者都重視": ("髮質和顏色都想顧", "兩個都在意", "希望不要太傷也要好看", "都重要"),
        },
        "reject_rule": "若訊息只是在回答顏色、底色、是否漂髮或預算數字，不可分類為 brand_priority。",
    },
}

SEMANTIC_SLOT_KEYS = set(SEMANTIC_SLOT_SCHEMAS.keys())



def _service_price_bounds():
    bounds = {}
    for category in SERVICE_CATEGORIES:
        for service in category.get("services", []):
            name = service.get("name")
            price_text = str(service.get("price") or "")
            if not name:
                continue
            numbers = [int(token) for token in re.findall(r"\d{3,5}", price_text.replace(",", ""))]
            if not numbers:
                bounds[name] = {"min": 0, "max": 999999}
                continue
            bounds[name] = {"min": min(numbers), "max": max(numbers)}
    return bounds


SERVICE_PRICE_BOUNDS = _service_price_bounds()


def get_chatbot_reply(input_mode, conversation_style, message, history, system_prompt):
    # Step 1: task-led + free-text is controller-led.
    # The controller owns the main slot-collection flow, while AI is still used
    # only by bounded helpers such as semantic slot classification.
    if input_mode == "text" and conversation_style == "task":
        return _get_task_text_controller_reply(message, history)

    if _is_task_button_mode(input_mode, conversation_style):
        deterministic_response = _build_task_button_ready_response(history, message)
        if deterministic_response:
            return deterministic_response

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



def _get_task_text_controller_reply(message, history):
    """Controller-led task + free-text response.

    Step 2:
    - FSM controls the main slot-collection flow.
    - User side questions are treated as interrupts and do not fill slots.
    - Semantic AI classification remains available only inside slot parsing.
    """
    latest_message = str(message or "").strip()
    slots_before = _task_free_text_slots_from_history(history, "")
    current_slot = _current_task_slot_from_slots(slots_before)
    normalized_message = _normalize_task_free_text(latest_message)
    intent = _detect_task_interrupt_intent(normalized_message, current_slot, slots_before)

    if intent.get("type") != "answer_slot":
        reply = _build_task_interrupt_reply(
            message=latest_message,
            history=history,
            slots=slots_before,
            current_slot=current_slot,
            intent=intent,
        )
        _debug_log(
            "task_text_controller_interrupt",
            intent=intent,
            current_slot=current_slot,
            reply_preview=(reply or "")[:120],
        )
        return {
            "reply": reply,
            "buttons": [],
            "source": "task_text_controller_interrupt",
            "is_final": False,
            "final_output": None,
        }

    slots_after = _task_free_text_slots_from_history(history, latest_message)
    task_ready = _is_task_free_text_ready_from_slots(slots_after)
    _debug_log(
        "task_text_controller_answer",
        current_slot=current_slot,
        task_ready=task_ready,
        slots=slots_after,
    )

    if task_ready:
        final_output = _build_task_text_final_output_from_slots(slots_after)
        if final_output:
            return {
                "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                "buttons": [],
                "source": "task_text_controller_final",
                "is_final": True,
                "final_output": final_output,
            }

    conversation_text = _conversation_text(history, latest_message)
    reply = _next_task_free_text_question(conversation_text, latest_message, slots=slots_after)
    return {
        "reply": reply,
        "buttons": [],
        "source": "task_text_controller",
        "is_final": False,
        "final_output": None,
    }


def _current_task_slot_from_slots(slots):
    slots = dict(slots or _empty_task_slots())
    required_slot = _next_required_slot_for_slots(slots, _slots_to_normalized_text(slots))
    if required_slot == "budget_adjustment":
        return "tradeoff_priority"
    return required_slot or "recommend"


def _detect_task_interrupt_intent(message, current_slot, slots):
    """Step 3: classify whether the latest user text is a slot answer or side branch.

    This is intentionally bounded. It does not decide the next task slot and it
    does not recommend a final service. It only prevents free-text questions from
    being committed as slot values.
    """
    text = _normalize_task_free_text(message)
    slots = dict(slots or _empty_task_slots())
    if not text:
        return {"type": "answer_slot", "reason": "empty_or_no_text"}

    if current_slot == "recommend":
        return {"type": "answer_slot", "reason": "already_ready"}

    if _is_uncertain_reply_text(text):
        if current_slot in {"budget_range", "tradeoff_priority", "perm_preference"}:
            return {"type": "answer_slot", "reason": "uncertain_allowed_for_current_slot"}
        return {"type": "uncertain", "reason": "user_uncertain"}

    if _has_any_phrase(text, ("差異", "差別", "差在哪", "有什麼不同", "有甚麼不同", "不同在哪", "比較")):
        return {"type": "ask_difference", "reason": "difference_question"}

    if _has_any_phrase(text, ("什麼意思", "甚麼意思", "意思是", "不懂", "這是什麼", "這是甚麼")):
        return {"type": "ask_meaning", "reason": "meaning_question"}

    if _is_advice_or_choice_question(text):
        return {"type": "ask_recommendation", "reason": "advice_or_choice_question"}

    if _has_any_phrase(text, ("可以嗎", "可不可以", "能不能", "做得到", "做得到嗎", "需要嗎", "要不要", "一定要", "一定需要", "會不會")):
        if _has_any_phrase(text, ("傷", "傷髮", "髮質", "受損", "壞", "斷", "毛躁", "乾")):
            return {"type": "ask_risk", "reason": "risk_question"}
        return {"type": "ask_feasibility", "reason": "feasibility_question"}

    if _has_any_phrase(text, ("多少錢", "價錢", "價格", "價位", "預算", "貴", "便宜", "費用")):
        # A pure numeric budget answer should remain a slot answer.
        if current_slot == "budget_range" and _detect_budget_range(text):
            return {"type": "answer_slot", "reason": "budget_answer"}
        return {"type": "ask_price", "reason": "price_question"}

    if "?" in text or "？" in text:
        return {"type": "ask_question", "reason": "question_mark"}

    return {"type": "answer_slot", "reason": "default"}


def _build_task_interrupt_reply(message, history, slots, current_slot, intent):
    slots = dict(slots or _empty_task_slots())
    conversation_text = _conversation_text(history, message)
    main_question = _next_task_free_text_question(conversation_text, message, slots=slots)
    interrupt_type = (intent or {}).get("type")

    branch_reply = ""
    if interrupt_type == "uncertain":
        branch_reply = _uncertain_explanation_for_current_slot(conversation_text, slots=slots)
    elif interrupt_type == "ask_recommendation":
        branch_reply = _advice_confirmation_reply_for_current_slot(slots, message)
        if branch_reply:
            return branch_reply
        branch_reply = _task_followup_explanation(conversation_text, message, slots=slots)
    elif interrupt_type in {"ask_difference", "ask_meaning", "ask_feasibility", "ask_risk", "ask_price", "ask_question"}:
        branch_reply = _task_followup_explanation(conversation_text, message, slots=slots)
        if not branch_reply:
            branch_reply = _interrupt_fallback_explanation(current_slot, slots, interrupt_type)

    if not branch_reply:
        branch_reply = _interrupt_fallback_explanation(current_slot, slots, interrupt_type)

    if main_question and main_question not in branch_reply and "這樣對嗎" not in branch_reply:
        return f"{branch_reply}\n\n{main_question}"
    return branch_reply or main_question


def _interrupt_fallback_explanation(current_slot, slots, interrupt_type):
    slots = dict(slots or _empty_task_slots())
    direction = slots.get("direction")

    if current_slot == "dye_detail":
        return "全頭染是整體換色；補染主要是處理新生髮根或局部色差。"
    if current_slot == "target_color":
        return "自然深色偏低調，一般棕色偏日常換色，高明度特殊色通常更明顯，也可能需要更多前置處理。"
    if current_slot == "current_base":
        return "目前底色會影響染後顯色程度。自然黑髮通常較難直接變亮；染過或漂過會影響後續可行性。"
    if current_slot == "bleach_accept":
        return "是否需要漂髮會看目標色和目前底色。高明度、灰感、銀色、粉色或特殊色通常較可能需要漂髮。"
    if current_slot == "brand_priority":
        return "修護優先會偏向降低染後乾澀與毛躁；顏色表現與CP值優先會偏向顯色效率與預算平衡。"
    if current_slot == "perm_detail":
        return "整體燙髮是改變整體捲度；髮根燙主要改善頭頂扁塌；燙瀏海是局部調整瀏海線條。"
    if current_slot == "perm_blocker":
        return "這題是安全限制確認。漂過、懷孕或髮質嚴重受損都可能不適合直接燙髮。"
    if current_slot == "perm_preference":
        return "平衡預算偏向先完成基本燙髮造型；重視燙後髮質與修護感則偏向降低燙後髮況負擔。"
    if current_slot == "treatment_detail":
        return "受損修護偏向染燙後乾裂與分岔；柔順抗毛躁偏向改善打結、毛躁與觸感；日常保養偏向維持光澤。"
    if current_slot == "budget_range":
        return "預算會影響可推薦的服務範圍；如果不確定，也可以直接說不確定。"
    if current_slot == "tradeoff_priority":
        return "預算優先會傾向較保守的方案；效果優先會傾向更接近目標，但可能需要提高預算或接受更多處理。"

    if direction:
        return "我會先回答你的問題，再回到目前的服務選擇流程。"
    return "我會先釐清你的問題，再回到主要服務選擇流程。"

def _build_task_button_ready_response(history, message):
    effective_history = _history_with_latest_user_message(history, message)
    if get_task_guided_prompt(effective_history) is not None:
        return None

    conversation_text = _conversation_text(effective_history, message)
    if _history_has_budget_uncertain(effective_history):
        conversation_text = f"{conversation_text} {BUDGET_NO_PREFERENCE}".strip()
    final_output = _build_task_text_final_output(conversation_text) or _build_default_final_output(conversation_text)
    if not final_output:
        return None

    return {
        "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
        "buttons": [],
        "source": "rule",
        "is_final": True,
        "final_output": final_output,
    }


def _history_with_latest_user_message(history, message):
    base_history = history if isinstance(history, list) else []
    latest_message = (message or "").strip()
    if not latest_message:
        return list(base_history)

    if base_history:
        last_item = base_history[-1] if isinstance(base_history[-1], dict) else {}
        if (
            last_item.get("role") == "user"
            and str(last_item.get("content") or "").strip() == latest_message
        ):
            return list(base_history)

    appended = list(base_history)
    appended.append({"role": "user", "content": latest_message})
    return appended


def _history_has_budget_uncertain(history):
    if not isinstance(history, list):
        return False
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue
        user_text = str(item.get("content") or "").strip()
        if user_text not in {UNCERTAIN_BUTTON_LABEL, "不確定"}:
            continue
        if index <= 0:
            continue
        previous = history[index - 1] if isinstance(history[index - 1], dict) else {}
        if previous.get("role") != "assistant":
            continue
        assistant_text = str(previous.get("content") or "")
        if "預算" in assistant_text or "價位" in assistant_text:
            return True
    return False


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
    final_output = None
    if conversation_style == "task" and allow_inferred_recommendation:
        if input_mode == "text":
            slots = _task_free_text_slots_from_history(history, message)
            final_output = _build_task_text_final_output_from_slots(slots)
        else:
            final_output = _build_task_text_final_output(conversation_text)
    if not final_output:
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
    # Task-led free-text should not enter the general Gemini reply path.
    # It is handled by _get_task_text_controller_reply() at the public entry.
    if input_mode == "text" and conversation_style == "task":
        return _get_task_text_controller_reply(message, history)

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
    # Task-led free-text should not enter the general Ollama reply path.
    # It is handled by _get_task_text_controller_reply() at the public entry.
    if input_mode == "text" and conversation_style == "task":
        return _get_task_text_controller_reply(message, history)

    model = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    endpoint = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat").strip()
    resolved_endpoint = _resolve_ollama_endpoint(endpoint)
    use_openai_compat = _is_openai_compat_endpoint(endpoint)
    prompt = build_model_instruction(
        input_mode,
        conversation_style,
        system_prompt,
        history=history,
    )
    if use_openai_compat:
        payload = {
            "model": model,
            "messages": _build_ollama_messages(prompt, message, history),
            "stream": False,
            "temperature": 0.4,
        }
    else:
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
        resolved_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        _debug_log("ollama_request_failed", input_mode=input_mode, conversation_style=conversation_style)
        return _ai_error_reply("目前本機 AI 無法回覆，請確認 Ollama 是否已啟動。")

    text = _extract_ollama_text(response_data)
    parsed = _parse_model_json(text)
    if not parsed:
        print(f"[OLLAMA_PARSE_DEBUG] text={text}", flush=True)
        print(f"[OLLAMA_PARSE_DEBUG] parsed={parsed}", flush=True)
        _debug_log(
            "ollama_json_parse_failed",
            input_mode=input_mode,
            conversation_style=conversation_style,
            raw_preview=(text or "")[:180],
        )
        # Step 1: In task-led mode, do not let non-JSON Ollama text control the dialogue.
        # Task-led flow must be controlled by the deterministic controller/FSM guard.
        # The model may fail to return JSON, but its natural-language text should not be
        # displayed as the next bot reply because that reintroduces LLM-driven flow.
        if conversation_style == "task":
            controller_response = {
                "reply": "",
                "buttons": [],
                "source": "ollama_json_parse_failed_controller",
                "is_final": False,
                "final_output": None,
            }
            return _force_final_at_turn_limit(
                controller_response,
                input_mode=input_mode,
                conversation_style=conversation_style,
                message=message,
                history=history,
            )

        natural_reply = _sanitize_template_reply(str(text or "").strip())
        if natural_reply:
            fallback_response = {
                "reply": natural_reply,
                "buttons": [],
                "source": "ollama_fallback_text",
                "is_final": False,
                "final_output": None,
            }
            return _force_final_at_turn_limit(
                fallback_response,
                input_mode=input_mode,
                conversation_style=conversation_style,
                message=message,
                history=history,
            )
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
        pass

    try:
        return response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _is_openai_compat_endpoint(endpoint):
    normalized = str(endpoint or "").strip().lower()
    if not normalized:
        return False
    return normalized.endswith("/v1") or "/v1/" in normalized


def _resolve_ollama_endpoint(endpoint):
    normalized = str(endpoint or "").strip()
    if not normalized:
        return "http://localhost:11434/api/chat"
    if normalized.lower().endswith("/v1"):
        return normalized.rstrip("/") + "/chat/completions"
    return normalized


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
    task_text_mode = input_mode == "text" and conversation_style == "task"
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
        guarded_is_final = bool(model_response.get("is_final")) and bool(task_ready)
        _debug_log(
            "task_mode_guard",
            input_mode=input_mode,
            task_ready=task_ready,
            is_final=guarded_is_final,
            reply_preview=(model_response.get("reply") or "")[:120],
        )

    if model_response["is_final"]:
        if task_mode and not task_ready:
            if task_text_mode:
                conversation_text = _conversation_text(history, message)
                slots = _task_free_text_slots_from_history(history, message)
                reply = _next_task_free_text_question(conversation_text, message, slots=slots)
            else:
                reply = _next_task_free_text_question(_conversation_text(history, message), message)
            return {
                "reply": reply,
                "buttons": model_response.get("buttons") or [],
                "source": model_response.get("source"),
                "is_final": False,
                "final_output": None,
            }
        if task_text_mode and task_ready:
            conversation_text = _conversation_text(history, message)
            slots = _task_free_text_slots_from_history(history, message)
            final_output = _build_task_text_final_output_from_slots(slots)
            if final_output:
                return {
                    "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                    "buttons": [],
                    "source": model_response.get("source"),
                    "is_final": True,
                    "final_output": final_output,
                }
            return {
                "reply": _next_task_free_text_question(conversation_text, message),
                "buttons": [],
                "source": model_response.get("source"),
                "is_final": False,
                "final_output": None,
            }
        if task_button_mode and task_ready:
            conversation_text = _conversation_text(history, message)
            final_output = _build_task_text_final_output(conversation_text)
            if final_output:
                return {
                    "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                    "buttons": [],
                    "source": model_response.get("source"),
                    "is_final": True,
                    "final_output": final_output,
                }
            return {
                "reply": _next_task_free_text_question(conversation_text, message),
                "buttons": model_response.get("buttons") or [],
                "source": model_response.get("source"),
                "is_final": False,
                "final_output": None,
            }
        return model_response

    user_turn_count = _count_user_turns(history)
    conversation_text = _conversation_text(history, message)

    if task_text_mode:
        if task_ready:
            slots = _task_free_text_slots_from_history(history, message)
            final_output = _build_task_text_final_output_from_slots(slots)
            if final_output:
                return {
                    "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                    "buttons": [],
                    "source": model_response.get("source"),
                    "is_final": True,
                    "final_output": final_output,
                }
            return {
                "reply": _next_task_free_text_question(conversation_text, message),
                "buttons": [],
                "source": model_response.get("source"),
                "is_final": False,
                "final_output": None,
            }

    if task_button_mode:
        if task_ready:
            final_output = _build_task_text_final_output(conversation_text) or _build_default_final_output(conversation_text)
            return {
                "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
                "buttons": [],
                "source": model_response.get("source"),
                "is_final": True,
                "final_output": final_output,
            }

        if user_turn_count < 15:
            return model_response

        final_output = _build_task_text_final_output(conversation_text) or _build_default_final_output(conversation_text)
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
        "next_step": f"請參考此建議，並從左側服務內容中選擇你最想預約的方案。{ONSITE_EVALUATION_NOTE}",
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

    if input_mode == "text":
        slots = _task_free_text_slots_from_history(history, message)
        return _is_task_free_text_ready_from_slots(slots)

    conversation_text = _conversation_text(history, message)
    return _is_task_free_text_ready(conversation_text)


def _is_task_button_ready(input_mode, conversation_style, history):
    if not _is_task_button_mode(input_mode, conversation_style):
        return False
    return get_task_guided_prompt(history) is None




def _empty_task_slots():
    slots = {"budget_range": None}
    for slot_key in TASK_SLOT_ENUMS:
        slots[slot_key] = None
    return slots


def _task_user_messages(history, message):
    messages = []
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict) and item.get("role") == "user":
                content = str(item.get("content") or "").strip()
                if content:
                    messages.append(content)

    latest = str(message or "").strip()
    if latest and (not messages or messages[-1] != latest):
        messages.append(latest)
    return messages


def _task_turn_items(history, message):
    """Return ordered user/assistant turns for deterministic FSM replay.

    Step 2+3 reconstructs persistent task state from chat history. Assistant
    confirmation questions are needed so that a later "是的/對" can commit the
    pending slot instead of causing a repeated confirmation loop.
    """
    turns = []
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            if role not in {"user", "assistant"}:
                continue
            content = str(item.get("content") or "").strip()
            if content:
                turns.append({"role": role, "content": content})

    latest = str(message or "").strip()
    if latest:
        if not turns or turns[-1].get("role") != "user" or turns[-1].get("content") != latest:
            turns.append({"role": "user", "content": latest})
    return turns


def _slots_to_normalized_text(slots):
    if not isinstance(slots, dict):
        return ""
    parts = []
    for key in (
        "direction",
        "dye_detail",
        "target_color",
        "current_base",
        "bleach_accept",
        "brand_priority",
        "perm_detail",
        "perm_blocker",
        "perm_preference",
        "treatment_detail",
        "budget_range",
        "tradeoff_priority",
    ):
        value = slots.get(key)
        if value:
            parts.append(str(value))
    return _normalize_task_free_text(" ".join(parts))


def _task_free_text_slots_from_history(history, message):
    """Replay a persistent task FSM state from history.

    This is Step 2 + Step 3:
    - Step 2: keep a real FSM-shaped state: slots/current_slot/pending_confirmation.
    - Step 3: when the previous assistant turn asked for confirmation, commit or
      clear that pending value based on the user's affirmative/negative reply.

    The function intentionally does NOT run full-conversation slot extraction.
    Each user message is interpreted only against the current required slot.
    """
    state = _initial_task_fsm_state()

    for turn in _task_turn_items(history, message):
        role = turn.get("role")
        content = str(turn.get("content") or "")
        normalized_message = _normalize_task_free_text(content)

        if role == "assistant":
            pending = _pending_confirmation_from_assistant(content)
            if pending:
                slot = pending.get("slot")
                value = pending.get("value")
                if slot and value and not state["slots"].get(slot):
                    state["pending_confirmation"] = pending
                    state["current_slot"] = slot
                    _debug_log("task_fsm_pending_set", pending=pending)
            continue

        if role != "user" or not normalized_message:
            continue

        if _apply_pending_confirmation_response(state, normalized_message):
            _advance_task_fsm_state(state)
            continue

        # If the user explicitly rejects the pending interpretation, keep the
        # same current_slot and parse this latest message as a replacement answer
        # only when it contains one.
        if state.get("pending_confirmation") and _is_negative_reply_text(normalized_message):
            _debug_log("task_fsm_pending_rejected", pending=state.get("pending_confirmation"))
            state["pending_confirmation"] = None

        current_slot = state.get("current_slot")
        if current_slot == "budget_adjustment":
            current_slot = "tradeoff_priority"
        intent = _detect_task_interrupt_intent(normalized_message, current_slot, state.get("slots"))
        if intent.get("type") != "answer_slot":
            _debug_log(
                "task_fsm_interrupt_skipped",
                current_slot=current_slot,
                intent=intent,
                message=normalized_message,
            )
            continue

        _consume_latest_message_for_task_fsm(state, normalized_message)
        _advance_task_fsm_state(state)

    _debug_log(
        "task_fsm_state",
        slots=state.get("slots"),
        current_slot=state.get("current_slot"),
        pending_confirmation=state.get("pending_confirmation"),
    )
    return state["slots"]


def _initial_task_fsm_state():
    return {
        "slots": _empty_task_slots(),
        "current_slot": "direction",
        "pending_confirmation": None,
    }


def _advance_task_fsm_state(state):
    slots = state.get("slots") or {}
    context_text = _slots_to_normalized_text(slots)
    required_slot = _next_required_slot_for_slots(slots, context_text)
    if required_slot == "budget_adjustment":
        required_slot = "tradeoff_priority"
    state["current_slot"] = required_slot or "recommend"


def _consume_latest_message_for_task_fsm(state, normalized_message):
    """Consume ONLY the latest user message for the current FSM slot.

    Step 4: no full-conversation slot extraction and no multi-slot harvesting
    from one message. The parser may only fill the currently active slot.
    """
    slots = state.get("slots") or {}
    current_slot = state.get("current_slot")

    if not current_slot or current_slot == "recommend":
        state["slots"] = slots
        return

    if current_slot == "budget_adjustment":
        current_slot = "tradeoff_priority"

    value = _extract_value_for_current_task_slot(
        current_slot,
        normalized_message,
        slots,
    )
    if value is None:
        state["slots"] = slots
        return

    # Step 6: if the user is asking for advice / clarification rather than
    # directly choosing an option, do not commit the inferred value yet.
    # Let the reply explain the likely direction and ask for confirmation.
    if _should_hold_inferred_answer_for_clarification(current_slot, normalized_message, value, slots):
        state["slots"] = slots
        _debug_log(
            "task_fsm_inferred_answer_held",
            current_slot=current_slot,
            inferred_value=value,
        )
        return

    slots[current_slot] = value
    if current_slot == "direction":
        _clear_cross_direction_slots(slots)

    state["slots"] = slots
    _debug_log("task_fsm_current_slot_parsed", current_slot=current_slot, value=value)

    # Step 7: allow one user sentence to fill later consecutive slots only
    # when the later values are explicitly present in that same message.
    # This fixes cases such as "我想要整頭染成金色":
    # dye_detail=全頭染, then target_color=高明度特殊色.
    _consume_safe_consecutive_task_slots(
        state,
        normalized_message,
        just_filled_slot=current_slot,
    )



def _consume_safe_consecutive_task_slots(state, normalized_message, just_filled_slot=None):
    """Fill explicit later slots from the same user message.

    Step 7 keeps the Step 4 safety rule: no global extraction and no guessing.
    It only moves forward through the official FSM order, and only when the
    same latest message explicitly contains the next slot's value.

    Example:
    current_slot=dye_detail, message="我想要整頭染成金色"
    -> fill dye_detail=全頭染
    -> safely continue to target_color=高明度特殊色
    -> stop before current_base because no base is explicitly present.

    It must not infer budget, brand priority, or bleach acceptance from a
    message unless those values are explicitly stated.
    """
    slots = state.get("slots") or {}
    text = _normalize_task_free_text(normalized_message)

    # Do not auto-continue when the user is asking for clarification/advice.
    if _is_followup_question(text) or _is_advice_or_choice_question(text):
        state["slots"] = slots
        return

    # A short contextual answer like "前者" or "可以" belongs only to the active
    # question. It should not be reused to fill following slots.
    if _is_short_contextual_reply(text):
        state["slots"] = slots
        return

    max_steps = 4
    for _ in range(max_steps):
        context_text = _slots_to_normalized_text(slots)
        next_slot = _next_required_slot_for_slots(slots, context_text)
        if next_slot == "budget_adjustment":
            next_slot = "tradeoff_priority"
        if not next_slot or next_slot == "recommend":
            break
        if next_slot == just_filled_slot:
            break

        value = _extract_explicit_value_for_consecutive_slot(next_slot, text, slots)
        if value is None:
            break

        slots[next_slot] = value
        if next_slot == "direction":
            _clear_cross_direction_slots(slots)

        _debug_log(
            "task_fsm_safe_consecutive_slot_parsed",
            current_slot=next_slot,
            value=value,
        )

    state["slots"] = slots


def _is_short_contextual_reply(text):
    compact = re.sub(r"\s+", "", _normalize_task_free_text(text).lower())
    if not compact:
        return False
    short_tokens = {
        "前者", "後者", "第一個", "第二個", "第三個", "第四個",
        "第1個", "第2個", "第3個", "第4個",
        "1", "2", "3", "4", "一", "二", "三", "四",
        "可以", "可", "好", "ok", "okay", "不行", "不要", "不想",
        "是", "是的", "對", "對的", "沒錯", "不對", "不是",
    }
    return compact in short_tokens


def _extract_explicit_value_for_consecutive_slot(slot_key, normalized_message, current_slots):
    """Extract only explicit values for Step 7 consecutive parsing.

    This intentionally avoids broad preference inference. For example,
    "我的頭髮很毛躁，你會建議我用哪個" should not auto-fill brand_priority
    here because Step 6 handles it with explanation + confirmation.
    """
    text = _normalize_task_free_text(normalized_message)

    if slot_key == "direction":
        return _detect_direction(text)

    if slot_key == "dye_detail":
        candidates = TASK_SLOT_KEYWORDS.get("dye_detail")
        return _detect_slot_value(text, candidates) if candidates else None

    if slot_key == "target_color":
        candidates = TASK_SLOT_KEYWORDS.get("target_color")
        return _detect_slot_value(text, candidates) if candidates else None

    if slot_key == "current_base":
        candidates = TASK_SLOT_KEYWORDS.get("current_base")
        return _detect_slot_value(text, candidates) if candidates else None

    if slot_key == "bleach_accept":
        # Only accept explicit bleach wording in a longer multi-slot message.
        if _has_any_phrase(text, ("不想漂", "不想要漂", "不要漂", "不漂", "不能漂", "不可以漂", "不接受漂", "希望不漂")):
            return "希望不漂髮"
        if _has_any_phrase(text, ("可以漂", "可漂", "接受漂", "能漂", "願意漂", "可以接受漂", "接受漂髮")):
            return "可接受漂髮"
        return None

    if slot_key == "brand_priority":
        if _has_any_phrase(text, ("重視染後髮質修護", "髮質修護優先", "髮質優先", "修護優先", "重視修護")):
            return "重視染後髮質修護"
        if _has_any_phrase(text, ("重視顏色表現與cp值", "重視顏色表現", "顏色表現優先", "cp值優先", "顯色優先")):
            return "重視顏色表現與CP值"
        if _has_any_phrase(text, ("兩者都重視", "兩個都重視", "兩個都想要", "都重要")):
            return "兩者都重視"
        return None

    if slot_key == "budget_range":
        return _detect_budget_range(text)

    if slot_key == "tradeoff_priority":
        if _has_any_phrase(text, ("以預算為優先", "預算優先", "價格優先", "便宜優先")):
            return "以預算為優先"
        if _has_any_phrase(text, ("以效果為優先", "效果優先", "顯色優先", "修護優先")):
            return "以效果為優先"
        if _is_uncertain_reply_text(text):
            return "我不確定"
        return None

    if slot_key in {"perm_detail", "perm_blocker", "perm_preference", "treatment_detail"}:
        candidates = TASK_SLOT_KEYWORDS.get(slot_key)
        value = _detect_slot_value(text, candidates) if candidates else None
        if slot_key == "perm_blocker" and not value and _has_any_phrase(text, ("以上皆無", "都沒有", "沒有", "無")):
            return "以上皆無"
        return value

    return None


def _semantic_parse_current_slot(slot_key, user_message, current_slots):
    """Bounded AI semantic fallback for the current FSM slot.

    Step B:
    - First try an actual AI classifier constrained by the current slot schema.
    - AI may only choose one value from allowed_values, or return null.
    - AI must not decide flow, fill other slots, or recommend services.
    - If AI is unavailable, invalid, or low-confidence, fall back to the
      previous rule-based semantic parser.
    """
    if slot_key not in SEMANTIC_SLOT_SCHEMAS:
        return _semantic_none("slot_not_supported")

    text = _normalize_task_free_text(user_message)
    if not text:
        return _semantic_none("empty_message")

    if _semantic_rejects_slot(slot_key, text):
        return _semantic_none("rejected_by_slot_rule")

    ai_result = _call_semantic_slot_ai_classifier(
        slot_key=slot_key,
        user_message=text,
        current_slots=current_slots,
    )
    if ai_result.get("value") and ai_result.get("confidence") in {"high", "medium"}:
        _debug_log(
            "semantic_slot_ai_classifier_result",
            slot_key=slot_key,
            value=ai_result.get("value"),
            confidence=ai_result.get("confidence"),
            reason=ai_result.get("reason"),
        )
        return ai_result

    rule_result = _rule_semantic_parse_current_slot(slot_key, text, current_slots)
    if rule_result.get("value"):
        _debug_log(
            "semantic_slot_rule_fallback_result",
            slot_key=slot_key,
            value=rule_result.get("value"),
            confidence=rule_result.get("confidence"),
            reason=rule_result.get("reason"),
            ai_reason=ai_result.get("reason"),
        )
        return rule_result

    return ai_result if ai_result.get("reason") else _semantic_none("no_semantic_match")


def _call_semantic_slot_ai_classifier(slot_key, user_message, current_slots):
    """Call the configured AI provider as a bounded slot classifier.

    This function is intentionally separate from the normal chatbot reply
    generation path. It sends only the current slot schema, latest user message,
    and already-filled slots. It does not send full history.
    """
    schema = SEMANTIC_SLOT_SCHEMAS.get(slot_key)
    if not schema:
        return _semantic_none("slot_not_supported")

    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    if provider not in {"ollama", "gemini"}:
        return _semantic_none("semantic_ai_provider_disabled")

    prompt = _build_semantic_slot_classifier_prompt(
        slot_key=slot_key,
        user_message=user_message,
        current_slots=current_slots,
        schema=schema,
    )

    if provider == "ollama":
        return _call_ollama_semantic_slot_classifier(prompt, schema)

    if provider == "gemini":
        return _call_gemini_semantic_slot_classifier(prompt, schema)

    return _semantic_none("semantic_ai_provider_unsupported")


def _build_semantic_slot_classifier_prompt(slot_key, user_message, current_slots, schema):
    safe_slots = {}
    if isinstance(current_slots, dict):
        for key, value in current_slots.items():
            if value:
                safe_slots[key] = value

    allowed_values = list(schema.get("allowed_values") or ())
    examples = schema.get("examples") or {}

    return (
        "你是 ZOSS 美髮諮詢系統的 slot classifier。你的任務只是在目前 slot 的 allowed_values 中分類使用者最新一句話。\n"
        "你不能決定下一題、不能補其他 slot、不能推薦服務、不能輸出自然語言。\n\n"
        f"current_slot: {slot_key}\n"
        f"slot_description: {schema.get('slot_description')}\n"
        f"allowed_values: {json.dumps(allowed_values, ensure_ascii=False)}\n"
        f"examples: {json.dumps(examples, ensure_ascii=False)}\n"
        f"reject_rule: {schema.get('reject_rule')}\n"
        f"already_filled_slots: {json.dumps(safe_slots, ensure_ascii=False)}\n"
        f"user_message: {user_message}\n\n"
        "輸出規則：\n"
        "1. value 必須是 allowed_values 裡的其中一個字串，或 null。\n"
        "2. confidence 只能是 high、medium、low、none。\n"
        "3. 如果使用者訊息明確對應某一類，confidence=high。\n"
        "4. 如果需要推論但合理，confidence=medium。\n"
        "5. 如果訊息屬於其他 slot、資訊不足、或違反 reject_rule，value=null 且 confidence=none。\n"
        "6. reason 用一句繁體中文說明分類依據，不要超過 40 字。\n"
        "7. 只輸出 JSON，不要 markdown，不要額外文字。\n\n"
        "JSON 格式：\n"
        "{\"value\": null, \"confidence\": \"none\", \"reason\": \"\"}"
    )


def _call_ollama_semantic_slot_classifier(prompt, schema):
    model = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    endpoint = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat").strip()
    resolved_endpoint = _resolve_ollama_endpoint(endpoint)
    use_openai_compat = _is_openai_compat_endpoint(endpoint)

    if use_openai_compat:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你只能輸出 JSON。不要輸出任何解釋、markdown 或多餘文字。",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你只能輸出 JSON。不要輸出任何解釋、markdown 或多餘文字。",
                },
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }

    request = urllib.request.Request(
        resolved_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        _debug_log("semantic_ollama_request_failed", error=str(error)[:160])
        return _semantic_none("semantic_ollama_request_failed")

    raw_text = _extract_ollama_text(response_data)
    parsed = _parse_model_json(raw_text)
    return _normalize_semantic_ai_result(parsed, schema, raw_text)


def _call_gemini_semantic_slot_classifier(prompt, schema):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _semantic_none("semantic_gemini_api_key_missing")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
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
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        _debug_log("semantic_gemini_request_failed", error=str(error)[:160])
        return _semantic_none("semantic_gemini_request_failed")

    raw_text = _extract_gemini_text(response_data)
    parsed = _parse_model_json(raw_text)
    return _normalize_semantic_ai_result(parsed, schema, raw_text)


def _normalize_semantic_ai_result(parsed, schema, raw_text=""):
    if not isinstance(parsed, dict):
        _debug_log("semantic_ai_json_parse_failed", raw_preview=str(raw_text or "")[:180])
        return _semantic_none("semantic_ai_json_parse_failed")

    allowed_values = set(schema.get("allowed_values") or ())
    raw_value = parsed.get("value")
    value = str(raw_value).strip() if raw_value is not None else None
    if value in {"", "null", "None", "none"}:
        value = None

    confidence = str(parsed.get("confidence") or "none").strip().lower()
    if confidence not in {"high", "medium", "low", "none"}:
        confidence = "none"

    reason = str(parsed.get("reason") or "").strip()

    if value and value not in allowed_values:
        normalized_value = _normalize_semantic_ai_value(value, allowed_values)
        if normalized_value:
            value = normalized_value
        else:
            return _semantic_none("semantic_ai_value_not_allowed")

    if not value:
        return {"value": None, "confidence": "none", "reason": reason or "semantic_ai_no_value"}

    if confidence in {"low", "none"}:
        return {"value": None, "confidence": confidence, "reason": reason or "semantic_ai_low_confidence"}

    return {"value": value, "confidence": confidence, "reason": reason}


def _normalize_semantic_ai_value(value, allowed_values):
    normalized = _normalize_task_free_text(value)
    for allowed in allowed_values:
        if normalized == _normalize_task_free_text(allowed):
            return allowed

    # Handle common partial outputs while still keeping the value bounded.
    for allowed in allowed_values:
        allowed_norm = _normalize_task_free_text(allowed)
        if normalized and (normalized in allowed_norm or allowed_norm in normalized):
            return allowed

    return None


def _rule_semantic_parse_current_slot(slot_key, user_message, current_slots):
    """Previous rule-based semantic parser used as a safe fallback."""
    del current_slots
    if slot_key not in SEMANTIC_SLOT_SCHEMAS:
        return _semantic_none("slot_not_supported")

    text = _normalize_task_free_text(user_message)
    if not text:
        return _semantic_none("empty_message")

    if _semantic_rejects_slot(slot_key, text):
        return _semantic_none("rejected_by_slot_rule")

    candidates = _semantic_candidates_for_slot(slot_key, text)
    if not candidates:
        return _semantic_none("no_semantic_match")

    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and candidates[1]["score"] == best["score"]:
        return _semantic_none("ambiguous_semantic_match")

    allowed_values = SEMANTIC_SLOT_SCHEMAS[slot_key]["allowed_values"]
    if best["value"] not in allowed_values:
        return _semantic_none("value_not_allowed")

    confidence = "high" if best["score"] >= 3 else "medium"
    return {
        "value": best["value"],
        "confidence": confidence,
        "reason": best["reason"],
    }


def _semantic_none(reason=""):
    return {"value": None, "confidence": "none", "reason": reason}


def _semantic_rejects_slot(slot_key, text):
    """Reject messages that clearly belong to another slot.

    This prevents the semantic fallback from turning any vague answer into a
    slot value after the deterministic keyword parser fails.
    """
    compact = re.sub(r"\s+", "", _normalize_task_free_text(text).lower())

    if slot_key == "dye_detail":
        return bool(_detect_budget_range(text)) or _has_any_phrase(
            text,
            ("預算", "價位", "多少錢", "修護", "髮質", "品牌", "資生堂", "哥德式")
        )

    if slot_key == "target_color":
        return _has_any_phrase(text, ("目前", "現在", "原本", "底色", "退成", "之前", "染過", "漂過"))

    if slot_key == "current_base":
        return _has_any_phrase(text, ("想染", "想要染", "染成", "希望染", "目標", "想變成", "我要染"))

    if slot_key == "bleach_accept":
        # "漂過" is current_base / perm_blocker evidence, not acceptance.
        if _has_any_phrase(text, ("漂過", "曾經漂", "之前漂", "已經漂")):
            return True
        return bool(_detect_budget_range(text))

    if slot_key == "brand_priority":
        if bool(_detect_budget_range(text)):
            return True
        color_only = _semantic_color_only_text(compact)
        if color_only:
            return True

    return False


def _semantic_color_only_text(compact_text):
    if not compact_text:
        return False
    color_tokens = (
        "黑", "黑茶", "深咖", "咖啡", "棕", "可可", "巧克力", "奶茶",
        "金", "亞麻", "灰", "銀", "粉", "藍", "紫", "橘", "紅"
    )
    intent_tokens = ("髮質", "修護", "護髮", "顯色", "cp", "價格", "預算", "划算", "效果", "都")
    return any(token in compact_text for token in color_tokens) and not any(token in compact_text for token in intent_tokens)


def _semantic_candidates_for_slot(slot_key, text):
    if slot_key == "dye_detail":
        return _semantic_dye_detail_candidates(text)
    if slot_key == "target_color":
        return _semantic_target_color_candidates(text)
    if slot_key == "current_base":
        return _semantic_current_base_candidates(text)
    if slot_key == "bleach_accept":
        return _semantic_bleach_accept_candidates(text)
    if slot_key == "brand_priority":
        return _semantic_brand_priority_candidates(text)
    return []


def _semantic_candidate(value, score, reason):
    return {"value": value, "score": score, "reason": reason}


def _semantic_dye_detail_candidates(text):
    candidates = []
    if _has_any_phrase(text, ("整顆頭", "整個頭", "全部頭髮", "全部都染", "全部重新染", "整體換色", "不是補髮根", "不是只補")):
        candidates.append(_semantic_candidate("全頭染", 3, "語意表示整體換色，不是只處理髮根。"))
    if _has_any_phrase(text, ("新長出來", "長出來的地方", "根部", "只補根", "只補髮根", "頭頂長出來", "布丁")):
        candidates.append(_semantic_candidate("補染", 3, "語意表示只處理新生髮或髮根區域。"))
    if _has_any_phrase(text, ("耳圈", "挑染", "線條染", "區塊染", "特殊設計", "設計染", "局部漂", "局部特殊色")):
        candidates.append(_semantic_candidate("漂髮設計染", 3, "語意表示需要設計染、局部漂或特殊色效果。"))
    return candidates


def _semantic_target_color_candidates(text):
    candidates = []
    if _has_any_phrase(text, ("黑茶", "自然茶", "低調", "看不太出來有染", "像沒染", "自然一點", "深咖啡", "深棕黑")):
        candidates.append(_semantic_candidate("自然深色", 3, "語意接近自然、低調或深色系目標髮色。"))
    if _has_any_phrase(text, ("可可", "巧克力", "焦糖", "霧棕", "茶棕", "奶茶咖", "咖色", "咖啡色系", "棕色系")):
        candidates.append(_semantic_candidate("一般棕色", 3, "語意接近棕色、咖啡色或奶茶棕色系。"))
    if _has_any_phrase(text, ("米金", "淺亞麻", "亞麻", "銀灰", "灰霧", "霧灰", "紫灰", "藍灰", "粉棕", "玫瑰", "很淺", "亮一點", "特殊一點")):
        candidates.append(_semantic_candidate("高明度特殊色", 3, "語意接近高明度、灰感、粉紫藍或特殊色。"))
    return candidates


def _semantic_current_base_candidates(text):
    candidates = []
    if _has_any_phrase(text, ("沒染過", "沒有染過", "原本髮色", "原生髮", "自然黑", "沒漂沒染", "從來沒染")):
        candidates.append(_semantic_candidate("自然黑髮", 3, "語意表示目前是未染未漂的自然髮色。"))
    if _has_any_phrase(text, ("之前染咖啡", "染過咖啡", "目前偏深", "現在偏深", "深棕", "暗棕", "深咖", "暗色系", "黑棕")):
        candidates.append(_semantic_candidate("已染深色/中深色", 3, "語意表示目前已有中深色或深色染髮底。"))
    if _has_any_phrase(text, ("退成金", "退色很淺", "現在很淺", "髮尾很亮", "之前有漂", "漂過一次", "漂過兩次", "淺底", "金底")):
        candidates.append(_semantic_candidate("已染淺色/已漂過", 3, "語意表示目前是淺色底或曾經漂過。"))
    return candidates


def _semantic_bleach_accept_candidates(text):
    candidates = []
    if _has_any_phrase(text, ("需要的話可以", "為了顏色可以", "可以為了效果", "願意漂", "能接受漂", "可以漂一次", "可以小漂")):
        candidates.append(_semantic_candidate("可接受漂髮", 3, "語意表示若效果需要，使用者可以接受漂髮。"))
    if _has_any_phrase(text, ("盡量不要漂", "最好不要漂", "不要傷頭髮", "怕漂壞", "不希望漂", "不考慮漂", "不想傷髮質", "不要漂比較好")):
        candidates.append(_semantic_candidate("希望不漂髮", 3, "語意表示使用者傾向避免漂髮。"))
    return candidates


def _semantic_brand_priority_candidates(text):
    candidates = []
    if _has_any_phrase(text, ("染完不要太乾", "不要太傷", "怕傷髮質", "髮質不要變差", "想保護髮質", "護髮感", "頭髮已經受損", "希望柔順")):
        candidates.append(_semantic_candidate("重視染後髮質修護", 3, "語意表示使用者優先在意染後髮質與修護感。"))
    if _has_any_phrase(text, ("顏色明顯", "想要顯色", "顯色度", "看得出來有染", "划算", "cp高", "cp 高", "不要太貴", "預算有限", "便宜一點")):
        candidates.append(_semantic_candidate("重視顏色表現與CP值", 3, "語意表示使用者優先在意顯色、效果或預算表現。"))
    if _has_any_phrase(text, ("都想顧", "都在意", "都重要", "不要太傷也要好看", "顏色和髮質都", "髮質和顏色都", "兩個都")):
        candidates.append(_semantic_candidate("兩者都重視", 3, "語意表示使用者同時重視髮質與顏色/CP值。"))
    return candidates


def _apply_pending_confirmation_response(state, normalized_message):
    pending = state.get("pending_confirmation")
    if not pending:
        return False

    slot = pending.get("slot")
    value = pending.get("value")
    if not slot or not value:
        state["pending_confirmation"] = None
        return False

    if _is_affirmative_reply_text(normalized_message):
        state["slots"][slot] = value
        state["pending_confirmation"] = None
        _debug_log("task_fsm_pending_committed", slot=slot, value=value)
        return True

    if _is_negative_reply_text(normalized_message):
        state["pending_confirmation"] = None
        state["current_slot"] = slot
        _debug_log("task_fsm_pending_cleared", slot=slot, value=value)
        return False

    return False


def _pending_confirmation_from_assistant(assistant_text):
    text = str(assistant_text or "").strip()
    if not text:
        return None

    patterns = (
        (r"我先理解成你目前底色是「([^」]+)」，這樣對嗎", "current_base"),
        (r"你目前底色比較像「([^」]+)」，這樣對嗎", "current_base"),
        (r"我先理解成你這次是(全頭染|補染)，這樣對嗎", "dye_detail"),
        (r"我先理解成你這次是(整體燙髮)，這樣對嗎", "perm_detail"),
        (r"我先理解成你想做(髮根燙|燙瀏海)，這樣對嗎", "perm_detail"),
        (r"我先理解成你是(重視燙後髮質與修護感)，這樣對嗎", "perm_preference"),
        (r"我先理解成你偏向(先平衡預算完成基本造型)，這樣對嗎", "perm_preference"),
        (r"我先理解成你這次偏好是「([^」]+)」，這樣對嗎", "brand_priority"),
        (r"我先理解成你想以「([^」]+)」為主，這樣對嗎", "tradeoff_priority"),
        (r"我先理解成你這次想改善的是「([^」]+)」，這樣對嗎", "treatment_detail"),
    )

    for pattern, slot in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw_value = match.group(1).strip()
        value = _normalize_pending_confirmation_value(slot, raw_value)
        if value:
            return {"slot": slot, "value": value}

    return None


def _normalize_pending_confirmation_value(slot_key, raw_value):
    value = str(raw_value or "").strip()
    if not value:
        return None

    if slot_key == "dye_detail":
        if "全頭" in value:
            return "全頭染"
        if "補染" in value:
            return "補染"

    if slot_key == "current_base":
        normalized = _normalize_llm_slot_value("current_base", value)
        if normalized in TASK_SLOT_ENUMS["current_base"]:
            return normalized

    if slot_key == "perm_detail":
        if "整體" in value:
            return "整體燙髮"
        if "髮根" in value:
            return "髮根燙"
        if "瀏海" in value:
            return "燙瀏海"

    if slot_key == "perm_preference":
        if "修護" in value or "髮質" in value:
            return "重視燙後髮質、柔順度與修護感"
        if "預算" in value or "基本" in value:
            return "平衡預算，完成基本燙髮造型"

    if slot_key == "brand_priority":
        if value in TASK_SLOT_ENUMS["brand_priority"]:
            return value
        if "修護" in value or "髮質" in value:
            return "重視染後髮質修護"
        if "顏色" in value or "CP" in value.upper() or "cp" in value:
            return "重視顏色表現與CP值"

    if slot_key == "tradeoff_priority":
        if "預算" in value or "價格" in value:
            return "以預算為優先"
        if "效果" in value or "髮質" in value or "修護" in value:
            return "以效果為優先"

    allowed = TASK_SLOT_ENUMS.get(slot_key)
    if allowed and value in allowed:
        return value
    return None


def _extract_contextual_short_answer_for_slot(slot_key, normalized_message):
    """Interpret short answers using the active FSM slot.

    Step 5: the user often answers with "可以", "前者", "第二個",
    or "都可以" because the assistant question already supplies the context.
    This helper maps those short answers only for the current slot and never
    fills unrelated slots.
    """
    text = _normalize_task_free_text(normalized_message)
    compact = re.sub(r"\\s+", "", text.lower())
    if not compact:
        return None

    first_tokens = ("前者", "第一個", "第1個", "1", "一", "選一", "選1", "第一項", "第一")
    second_tokens = ("後者", "第二個", "第2個", "2", "二", "選二", "選2", "第二項", "第二")
    third_tokens = ("第三個", "第3個", "3", "三", "選三", "選3", "第三項", "第三")
    fourth_tokens = ("第四個", "第4個", "4", "四", "選四", "選4", "第四項", "第四", "最後一個")

    def has_token(tokens):
        return compact in tokens or any(token in compact for token in tokens if len(token) > 1)

    if slot_key == "bleach_accept":
        if _is_contextual_negative_answer(text):
            return "希望不漂髮"
        if _is_contextual_affirmative_answer(text):
            return "可接受漂髮"

    if slot_key == "dye_detail":
        if has_token(first_tokens) or _has_any_phrase(text, ("整頭", "全頭", "全部", "整個", "整體", "換色", "重新染", "全染")):
            return "全頭染"
        if has_token(second_tokens) or _has_any_phrase(text, ("補染", "補髮根", "髮根", "布丁", "局部", "新生髮")):
            return "補染"
        if has_token(third_tokens) or _has_any_phrase(text, ("漂髮設計染", "漂染", "漂髮", "特殊色", "挑染", "耳圈")):
            return "漂髮設計染"

    if slot_key == "target_color":
        if has_token(first_tokens):
            return "自然深色"
        if has_token(second_tokens):
            return "一般棕色"
        if has_token(third_tokens):
            return "高明度特殊色"

    if slot_key == "current_base":
        if has_token(first_tokens):
            return "自然黑髮"
        if has_token(second_tokens):
            return "已染深色/中深色"
        if has_token(third_tokens):
            return "已染淺色/已漂過"

    if slot_key == "brand_priority":
        if (
            has_token(first_tokens)
            or _has_any_phrase(text, ("修護", "髮質", "護髮", "毛躁", "乾燥", "受損", "柔順", "打結", "分岔", "分叉"))
        ):
            return "重視染後髮質修護"
        if (
            has_token(second_tokens)
            or _has_any_phrase(text, ("顏色", "顯色", "cp", "cp值", "cp 值", "價格", "預算", "便宜", "划算", "效果"))
        ):
            return "重視顏色表現與CP值"
        if _is_uncertain_reply_text(text) or _has_any_phrase(text, ("兩個都", "都重視", "都可以", "都想要")):
            return "兩者都重視"

    if slot_key == "tradeoff_priority":
        if has_token(first_tokens) or _has_any_phrase(text, ("預算", "價格", "便宜", "省錢", "cp", "cp值", "cp 值")):
            return "以預算為優先"
        if has_token(second_tokens) or _has_any_phrase(text, ("效果", "顯色", "髮質", "修護", "護理")):
            return "以效果為優先"
        if _is_uncertain_reply_text(text):
            return "我不確定"

    if slot_key == "perm_detail":
        if has_token(first_tokens) or _has_any_phrase(text, ("整體", "全頭", "燙捲", "整頭")):
            return "整體燙髮"
        if has_token(second_tokens) or _has_any_phrase(text, ("髮根", "頭頂", "蓬鬆")):
            return "髮根燙"
        if has_token(third_tokens) or _has_any_phrase(text, ("瀏海", "劉海")):
            return "燙瀏海"

    if slot_key == "perm_blocker":
        if has_token(first_tokens) or _has_any_phrase(text, ("漂過", "有漂", "曾漂")):
            return "曾經漂過頭髮"
        if has_token(second_tokens) or _has_any_phrase(text, ("懷孕", "孕婦")):
            return "目前懷孕"
        if has_token(third_tokens) or _has_any_phrase(text, ("嚴重受損", "斷裂", "容易斷")):
            return "髮質嚴重受損或容易斷裂"
        if has_token(fourth_tokens) or _has_any_phrase(text, ("以上皆無", "都沒有", "沒有", "無")):
            return "以上皆無"

    if slot_key == "perm_preference":
        if has_token(first_tokens) or _has_any_phrase(text, ("預算", "基本", "平衡", "便宜", "造型")):
            return "平衡預算，完成基本燙髮造型"
        if has_token(second_tokens) or _has_any_phrase(text, ("髮質", "柔順", "修護", "質感", "受損")):
            return "重視燙後髮質、柔順度與修護感"
        if _is_uncertain_reply_text(text):
            return "不確定"

    if slot_key == "treatment_detail":
        if has_token(first_tokens) or _has_any_phrase(text, ("受損", "修護", "染燙", "乾裂", "分叉", "分岔")):
            return "受損修護"
        if has_token(second_tokens) or _has_any_phrase(text, ("柔順", "毛躁", "打結", "觸感", "服貼")):
            return "柔順抗毛躁"
        if has_token(third_tokens) or _has_any_phrase(text, ("日常", "保養", "入門", "光澤", "基礎")):
            return "日常保養"

    return None


def _is_contextual_affirmative_answer(text):
    normalized = _normalize_task_free_text(text)
    compact = re.sub(r"\\s+", "", normalized.lower())
    if _is_affirmative_reply_text(normalized):
        return True
    return compact in {
        "可以接受",
        "能接受",
        "可接受",
        "接受",
        "可以",
        "可",
        "能",
        "好",
        "好啊",
        "ok",
        "okay",
        "沒問題",
        "行",
        "可以的",
        "願意",
    }


def _is_contextual_negative_answer(text):
    normalized = _normalize_task_free_text(text)
    compact = re.sub(r"\\s+", "", normalized.lower())
    if _is_negative_reply_text(normalized):
        return True
    return compact in {
        "不要",
        "不想",
        "不想要",
        "不行",
        "不能",
        "不可以",
        "不接受",
        "不願意",
        "先不要",
        "還是不要",
        "沒辦法",
    }


def _is_advice_or_choice_question(text):
    normalized = _normalize_task_free_text(text)
    return _has_any_phrase(
        normalized,
        (
            "你會建議",
            "會建議",
            "建議我",
            "你推薦",
            "推薦我",
            "哪個比較適合",
            "哪個適合",
            "選哪個",
            "選哪一個",
            "怎麼選",
            "該選哪個",
            "應該選哪個",
            "幫我選",
            "幫我判斷",
        ),
    )


def _should_hold_inferred_answer_for_clarification(slot_key, normalized_message, inferred_value, current_slots):
    """Return True when a value was inferred from a question, not chosen directly.

    Step 6 separates clarification / advice seeking from direct slot answers.
    Example: at brand_priority, "我的頭髮很毛躁，你會建議我選哪個" contains
    evidence for 修護, but the user is asking the system to advise rather than
    committing a preference. We explain and ask confirmation instead of
    advancing to final immediately.
    """
    del current_slots
    if not inferred_value:
        return False
    if slot_key not in {"brand_priority", "tradeoff_priority", "perm_preference", "treatment_detail"}:
        return False
    return _is_advice_or_choice_question(normalized_message)


def _advice_confirmation_reply_for_current_slot(slots, user_message):
    message = _normalize_task_free_text(user_message)
    slots = dict(slots or _empty_task_slots())
    direction = slots.get("direction")

    if direction == "染髮" and not slots.get("brand_priority"):
        suggested = _extract_value_for_current_task_slot("brand_priority", message, slots)
        if suggested == "重視染後髮質修護":
            return (
                "如果你的頭髮偏毛躁、乾燥或受損，通常會比較建議優先看染後髮質修護，"
                "因為這個方向會比較重視染後觸感與髮況負擔。\n\n"
                "我先理解成你這次偏好是「重視染後髮質修護」，這樣對嗎？"
            )
        if suggested == "重視顏色表現與CP值":
            return (
                "如果你更在意顏色是否明顯、顯色效率或預算表現，通常會比較偏向顏色表現與CP值。\n\n"
                "我先理解成你這次偏好是「重視顏色表現與CP值」，這樣對嗎？"
            )
        if suggested == "兩者都重視":
            return (
                "如果你兩邊都在意，我會先把它當成兩者都重視，再用後面的預算條件幫你收斂。\n\n"
                "我先理解成你這次偏好是「兩者都重視」，這樣對嗎？"
            )

    if direction == "燙髮" and not slots.get("perm_preference"):
        suggested = _extract_value_for_current_task_slot("perm_preference", message, slots)
        if suggested == "重視燙後髮質、柔順度與修護感":
            return (
                "如果你在意毛躁、受損或燙後觸感，通常會比較建議優先看燙後髮質與修護感。\n\n"
                "我先理解成你是重視燙後髮質與修護感，這樣對嗎？"
            )
        if suggested == "平衡預算，完成基本燙髮造型":
            return (
                "如果你主要想先完成基本造型並控制預算，通常會比較偏向平衡預算的方向。\n\n"
                "我先理解成你偏向先平衡預算完成基本造型，這樣對嗎？"
            )

    if direction == "護髮" and not slots.get("treatment_detail"):
        suggested = _extract_value_for_current_task_slot("treatment_detail", message, slots)
        if suggested == "柔順抗毛躁":
            return (
                "如果你的主要困擾是毛躁、打結或不夠服貼，通常會比較建議先看柔順抗毛躁。\n\n"
                "我先理解成你這次想改善的是「柔順抗毛躁」，這樣對嗎？"
            )
        if suggested == "受損修護":
            return (
                "如果你的主要困擾是染燙受損、乾裂或分岔，通常會比較建議先看受損修護。\n\n"
                "我先理解成你這次想改善的是「受損修護」，這樣對嗎？"
            )

    return ""


def _extract_value_for_current_task_slot(slot_key, normalized_message, current_slots):
    contextual_value = _extract_contextual_short_answer_for_slot(slot_key, normalized_message)
    if contextual_value is not None:
        return contextual_value

    if slot_key == "direction":
        return _detect_direction(normalized_message)

    if slot_key == "budget_range":
        budget = _detect_budget_range(normalized_message)
        if budget:
            return budget
        if _is_uncertain_reply_text(normalized_message):
            return BUDGET_NO_PREFERENCE
        return None

    if slot_key == "budget_adjustment":
        return _extract_value_for_current_task_slot("tradeoff_priority", normalized_message, current_slots)

    if slot_key == "brand_priority":
        if _has_any_phrase(
            normalized_message,
            (
                "毛躁",
                "乾",
                "乾燥",
                "受損",
                "髮質",
                "修護",
                "護髮",
                "柔順",
                "打結",
                "分岔",
                "分叉",
            ),
        ):
            return "重視染後髮質修護"
        if _has_any_phrase(
            normalized_message,
            (
                "顯色",
                "顏色",
                "cp",
                "cp值",
                "cp 值",
                "便宜",
                "價格",
                "預算",
                "划算",
                "效果",
            ),
        ):
            return "重視顏色表現與CP值"
        if _is_uncertain_reply_text(normalized_message):
            return "兩者都重視"

    if slot_key == "tradeoff_priority":
        if _has_any_phrase(normalized_message, ("效果", "顯色", "髮質", "修護", "護理")):
            return "以效果為優先"
        if _has_any_phrase(normalized_message, ("預算", "價格", "便宜", "省錢", "cp", "cp值", "cp 值")):
            return "以預算為優先"
        if _is_uncertain_reply_text(normalized_message):
            return "我不確定"

    if slot_key == "bleach_accept":
        if _has_any_phrase(normalized_message, ("不想漂", "不想要漂", "不要漂", "不漂", "不能漂", "不可以漂", "不接受漂")):
            return "希望不漂髮"
        if _has_any_phrase(normalized_message, ("可以漂", "可漂", "接受漂", "能漂", "願意漂", "可以接受漂")):
            return "可接受漂髮"
        return None

    candidates = TASK_SLOT_KEYWORDS.get(slot_key)
    if candidates:
        value = _detect_slot_value(normalized_message, candidates)
        if value:
            return value

    # Step 12: deterministic keyword parser first; bounded semantic parser second.
    # Semantic fallback is restricted to the current slot and only commits high-confidence values.
    semantic_result = _semantic_parse_current_slot(slot_key, normalized_message, current_slots)
    if semantic_result.get("confidence") == "high" and semantic_result.get("value"):
        _debug_log(
            "task_fsm_semantic_slot_parsed",
            current_slot=slot_key,
            value=semantic_result.get("value"),
            reason=semantic_result.get("reason"),
        )
        return semantic_result.get("value")

    if slot_key == "perm_blocker" and _has_any_phrase(normalized_message, ("沒有", "都沒有", "無", "以上皆無")):
        return "以上皆無"

    return None


def _is_task_free_text_ready_from_slots(slots):
    if not isinstance(slots, dict):
        return False
    direction = slots.get("direction")
    if direction is None:
        return False

    context_text = _slots_to_normalized_text(slots)

    if direction == "染髮":
        detail = _normalized_dye_detail(slots.get("dye_detail"))
        if not detail:
            return False
        if detail == "補染":
            return True
        if detail != "全頭染":
            return False
        if not slots.get("target_color") or not slots.get("current_base"):
            return False
        if _needs_bleach_for_slots(slots) and not slots.get("bleach_accept"):
            return False
        if _is_bleach_design_direct_ready(slots):
            return True
        if not slots.get("brand_priority"):
            return False
        candidates = _candidate_services_for_task_slots(slots)
        if len(candidates) <= 1:
            return True
        if not slots.get("budget_range"):
            return False
        if _needs_tradeoff_priority(slots, context_text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, context_text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(candidates) > 0

    if direction == "燙髮":
        if not slots.get("perm_detail") or not slots.get("perm_blocker"):
            return False
        if slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
            return True
        if slots.get("perm_detail") in {"髮根燙", "燙瀏海"}:
            return True
        if not slots.get("perm_preference") or not slots.get("budget_range"):
            return False
        if slots.get("perm_preference") in {
            "平衡預算，完成基本燙髮造型",
            "重視燙後髮質、柔順度與修護感",
        }:
            return True
        if _needs_tradeoff_priority(slots, context_text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, context_text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(_candidate_services_for_task_slots(slots)) > 0

    if direction == "護髮":
        if not slots.get("treatment_detail") or not slots.get("budget_range"):
            return False
        if _needs_tradeoff_priority(slots, context_text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, context_text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(_candidate_services_for_task_slots(slots)) > 0

    return False

def _is_task_free_text_ready(conversation_text):
    text = _normalize_task_free_text(conversation_text)
    if not text:
        return False

    raw_slots = _extract_task_slots(text)
    slots = _slots_with_confirmed_values(raw_slots)
    direction = slots.get("direction")
    if direction is None:
        return False

    if direction == "染髮":
        detail = _normalized_dye_detail(slots.get("dye_detail"))
        if not detail:
            return False
        if detail == "補染":
            return True
        if detail != "全頭染":
            return False
        required = ("target_color", "current_base")
        if not all(slots.get(field) for field in required):
            return False
        if _needs_bleach_for_slots(slots):
            if not slots.get("bleach_accept"):
                return False
        if not slots.get("brand_priority"):
            return False
        candidates = _candidate_services_for_task_slots(slots)
        if len(candidates) <= 1:
            return True
        if not slots.get("budget_range"):
            return False
        if _needs_tradeoff_priority(slots, text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(_candidate_services_for_task_slots(slots)) > 0

    if direction == "燙髮":
        required = ("perm_detail", "perm_blocker")
        if not all(slots.get(field) for field in required):
            return False
        if slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
            return True
        if slots.get("perm_detail") in {"髮根燙", "燙瀏海"}:
            return True
        if not slots.get("perm_preference"):
            return False
        if not slots.get("budget_range"):
            return False
        if slots.get("perm_preference") in {
            "平衡預算，完成基本燙髮造型",
            "重視燙後髮質、柔順度與修護感",
        }:
            return True
        if _needs_tradeoff_priority(slots, text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(_candidate_services_for_task_slots(slots)) > 0

    if direction == "護髮":
        if not slots.get("budget_range"):
            return False
        required = ("treatment_detail",)
        if not all(slots.get(field) for field in required):
            return False
        if _needs_tradeoff_priority(slots, text):
            return bool(slots.get("tradeoff_priority"))
        if _has_budget_compatible_candidates(slots, text):
            return True
        return slots.get("tradeoff_priority") == "以效果為優先" and len(_candidate_services_for_task_slots(slots)) > 0

    return False


def _detect_direction(text):
    normalized_text = _normalize_task_free_text(text)
    if _has_any_phrase(normalized_text, ("染髮", "補染", "漂髮", "髮色")):
        return "染髮"
    if _has_any_phrase(normalized_text, ("燙髮", "捲度", "髮根燙", "燙瀏海")):
        return "燙髮"
    if _has_any_phrase(normalized_text, ("護髮", "修護")):
        return "護髮"
    return None


def _has_budget_info(text):
    if _has_any_phrase(text, ("預算", "價位")):
        return True
    return re.search(r"\d{3,5}", text) is not None


def _has_any_phrase(text, phrases):
    lowered = (text or "").lower()
    return any((phrase or "").lower() in lowered for phrase in phrases)


def _is_affirmative_reply_text(text):
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    tokens = ("是", "對", "沒錯", "正確", "嗯", "好", "可以", "對的")
    if lowered in tokens or any(lowered.startswith(f"{token}，") for token in tokens):
        return True
    return lowered.startswith(("是的", "對啊", "對喔", "沒錯啊", "可以啊"))


def _is_negative_reply_text(text):
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    tokens = ("不是", "不對", "不太對", "不正確", "不是喔", "不是哦", "no")
    return lowered in tokens or any(lowered.startswith(f"{token}，") for token in tokens)


def _sanitize_template_reply(reply):
    content = (reply or "").strip()
    if not content:
        return content
    if any(pattern in content for pattern in TEMPLATE_REPLY_PATTERNS):
        return "我需要再確認一個條件，才能準確推薦。請先告訴我你的預算價位區間。"
    return content


def _is_difference_question(text):
    normalized = _normalize_task_free_text(text)
    return _has_any_phrase(
        normalized,
        ("差別", "差在哪", "差異", "不同", "怎麼選", "比較", "有什麼差"),
    )


def _is_followup_question(text):
    normalized = _normalize_task_free_text(text)
    return _has_any_phrase(
        normalized,
        (
            "?",
            "？",
            "嗎",
            "為什麼",
            "怎麼",
            "需要",
            "要不要",
            "可以嗎",
            "會不會",
            "一定要漂",
            "要漂髮嗎",
            "需要漂髮嗎",
            "漂髮嗎",
            "風險",
            "差別",
            "差在哪",
            "什麼意思",
            "甚麼意思",
            "建議",
            "推薦",
            "選哪個",
            "選哪一個",
            "選哪種",
            "哪個比較適合",
            "哪個適合",
            "該選哪個",
        ),
    )


def _task_followup_explanation(conversation_text, user_message, slots=None):
    text = _normalize_task_free_text(conversation_text)
    message = _normalize_task_free_text(user_message)
    slots = dict(slots or _empty_task_slots())
    direction = slots.get("direction")
    if direction == "燙髮":
        if _has_any_phrase(message, ("差別", "差在哪", "不同", "比較")):
            if not _slot_value_for_flow(slots, "perm_detail"):
                return "整體燙髮是改變整體捲度；髮根燙主要增加頭頂蓬鬆；燙瀏海則是局部修飾臉型。"
        return ""
    if direction != "染髮":
        advice_reply = _advice_confirmation_reply_for_current_slot(slots, message)
        if advice_reply:
            return advice_reply
        return ""

    advice_reply = _advice_confirmation_reply_for_current_slot(slots, message)
    if advice_reply:
        return advice_reply

    if _has_any_phrase(message, ("差別", "差在哪", "不同", "比較")):
        return _difference_explanation_for_next_slot(conversation_text, slots=slots)

    if _has_any_phrase(message, ("需要漂", "要不要漂", "漂髮嗎", "要漂髮嗎", "一定要漂", "一定需要漂", "會不會漂", "能不能不漂")):
        target = slots.get("target_color")
        current = slots.get("current_base")
        color_hint = _extract_target_color_hint(text) or "目標色"
        if target == "高明度特殊色":
            if current == "已染淺色/已漂過":
                return f"以你目前底色來看，仍可能需要補漂或校色，會依{color_hint}的目標明度決定。"
            if current == "已染深色/中深色":
                return f"以你目前底色來看，多數情況會需要先漂，才能穩定做出{color_hint}。"
            if current == "自然黑髮":
                return f"若目標是{color_hint}，通常需要先漂才能顯色，否則可能偏暗或偏灰。"
        return "是否需要漂髮會看目前底色與目標明度，現場設計師會再評估可行性與髮況風險。"

    if _has_any_phrase(message, ("什麼意思", "甚麼意思")):
        if _has_any_phrase(text, ("預算可能和條件不一致", "提高預算", "調整服務需求")):
            return "這句話的意思是：以你目前條件，落在該預算內的可行方案可能不足，所以需要提高預算或調整需求。"
        if _has_any_phrase(text, ("重視染後髮質修護", "顏色表現與cp值", "顏色表現與cp")):
            return "簡單說：修護優先偏向髮質與溫和度；顏色與CP值優先偏向顯色與預算效率。"

    return ""


def _difference_explanation_for_next_slot(conversation_text, slots=None):
    text = _normalize_task_free_text(conversation_text)
    slots = dict(slots or _empty_task_slots())
    direction = slots.get("direction")

    if direction == "染髮":
        detail = _normalized_dye_detail(slots.get("dye_detail"))
        if not slots.get("dye_detail") or detail not in {"全頭染", "補染"}:
            return "全頭染是整頭換色；補染主要針對新生髮根或局部色差。"
        if detail == "全頭染" and not slots.get("target_color"):
            return "自然深色通常較低調、維護門檻較低；高明度特殊色更顯色，常需要更多前置處理。"
        if detail == "全頭染" and not slots.get("current_base"):
            return "目前底色會直接影響可達到的明度、是否需要漂髮，以及最終持色表現。"
        if detail == "全頭染" and _needs_bleach_for_slots(slots) and not slots.get("bleach_accept"):
            return "可接受漂髮通常顏色選擇更多；不漂髮會改走更保守、髮質負擔較低的方向。"
        if detail == "全頭染" and not slots.get("brand_priority"):
            return "重視髮質修護會偏向較溫和與修護導向；重視顏色表現與CP值則偏向顯色與預算效率。"
        if not slots.get("budget_range"):
            return "預算會影響可優先比對的方案範圍，先確認可更快收斂到可預約方案。"

    if direction == "燙髮":
        if not slots.get("perm_detail"):
            return "整體燙髮是改變整體捲度；髮根燙主攻頭頂蓬鬆；燙瀏海是局部微調。"
        if not slots.get("perm_blocker"):
            return "這題是安全檢查：若有漂髮、懷孕或嚴重受損，通常要先走保守評估。"
        if slots.get("perm_detail") == "整體燙髮" and not slots.get("perm_preference"):
            return "平衡預算偏向先完成造型；重視修護感會偏向燙後髮質與觸感。"
        if not slots.get("budget_range"):
            return "預算能幫我們在可行方案裡快速收斂，不會推薦到不符合價位的服務。"

    if direction == "護髮":
        if not slots.get("treatment_detail"):
            return "受損修護偏重結構修補；柔順抗毛躁偏重觸感與服貼；日常保養偏入門維持。"
        if not slots.get("budget_range"):
            return "預算能幫我們在護髮方案中更快對齊可預約選項。"

    return ""



def _uncertain_explanation_for_current_slot(conversation_text, slots=None):
    """Explain the active task-led choice when the user says they are unsure.

    This prevents the controller from simply repeating the same question after
    "我不確定", while still keeping the FSM state unchanged.
    """
    text = _normalize_task_free_text(conversation_text)
    slots = dict(slots or _empty_task_slots())
    direction = slots.get("direction")
    required_slot = _next_required_slot_for_slots(slots, text)
    if required_slot == "budget_adjustment":
        required_slot = "tradeoff_priority"

    if direction == "染髮":
        if required_slot == "dye_detail":
            return "全頭染是整頭換色，適合想明顯改變整體髮色；補染主要是處理新生髮根或局部色差，適合原本已有髮色、只想把髮根補齊。"
        if required_slot == "target_color":
            return "自然深色偏低調、通常較好維護；一般棕色是日常改變髮色；高明度特殊色像金色、粉色、灰色，通常需要更多前置處理。"
        if required_slot == "current_base":
            return "目前底色會影響染後能不能顯色。自然黑髮通常最難直接變亮；已染深色會受原本染劑影響；已染淺色或漂過通常比較容易做出明亮色。"
        if required_slot == "bleach_accept":
            return "如果目標是金色、灰色、粉色這類高明度色，接受漂髮通常能更接近目標；不漂髮則會走比較保守、較暗的顏色方向。"
        if required_slot == "brand_priority":
            return "重視染後髮質修護，會偏向降低染後乾澀與毛躁；重視顏色表現與CP值，會偏向顯色效率與預算平衡。"

    if direction == "燙髮":
        if required_slot == "perm_detail":
            return "整體燙髮是改變整體捲度；髮根燙主要改善頭頂扁塌；燙瀏海是局部調整瀏海線條。"
        if required_slot == "perm_blocker":
            return "這題是安全限制檢查。漂過、懷孕或髮質嚴重受損都可能不適合直接燙髮。"
        if required_slot == "perm_preference":
            return "平衡預算偏向先完成基本燙髮造型；重視燙後髮質與修護感，會偏向較在意燙後柔順度與髮況負擔。"

    if direction == "護髮":
        if required_slot == "treatment_detail":
            return "受損修護偏向染燙後乾裂與分岔；柔順抗毛躁偏向改善打結、毛躁與觸感；日常保養偏向一般維持光澤。"

    if required_slot == "budget_range":
        return "預算會影響可推薦的服務範圍。若沒有明確上限，也可以回答不確定，我會先用可行性與效果來收斂。"
    if required_slot == "tradeoff_priority":
        return "預算優先會傾向保守、可負擔的方案；效果優先會傾向更接近目標，但可能需要提高預算或接受更多處理。"
    return ""



def _guard_task_reply_if_not_ready(reply, ready, input_mode, history, message):
    content = _sanitize_template_reply(reply)
    if ready:
        return content

    if input_mode == "text":
        conversation_text = _conversation_text(history, message)
        slots = _task_free_text_slots_from_history(history, message)
        previous_slots = _task_free_text_slots_from_history(history, "")
        next_question = _next_task_free_text_question(conversation_text, message, slots=slots)

        # If the user says "我不確定 / 不知道 / 不確定要選哪種" and this turn
        # did not fill the current slot, do not repeat the exact same question.
        # Explain the current decision axis, then ask the same slot again.
        if _is_uncertain_reply_text(_normalize_task_free_text(message)) and not _task_slots_progressed(previous_slots, slots):
            explanation = _uncertain_explanation_for_current_slot(conversation_text, slots=slots)
            if explanation:
                if next_question and next_question not in explanation:
                    return f"{explanation}\n\n{next_question}"
                return explanation

        if _is_followup_question(message):
            explanation = _task_followup_explanation(conversation_text, message, slots=slots)
            ai_reply = content.strip()
            if _looks_like_recommendation_text(ai_reply):
                ai_reply = ""
            base_reply = ai_reply or explanation
            if base_reply:
                if "這樣對嗎" in base_reply:
                    return base_reply
                if next_question and next_question not in base_reply:
                    return f"{base_reply}\n\n{next_question}"
                return base_reply
        return next_question

    if _contains_service_name(content):
        return _next_task_free_text_question(_conversation_text(history, message), message)
    return content or _next_task_free_text_question(_conversation_text(history, message), message)


def _contains_service_name(text):
    content = (text or "").strip()
    if not content:
        return False
    return any(service_name in content for service_name in SERVICE_HINTS.keys())


def _looks_like_recommendation_text(text):
    content = (text or "").strip()
    if not content:
        return False
    if _has_any_phrase(content, ("推薦服務", "推薦理由", "注意事項", "請參考此建議")):
        return True
    return _contains_service_name(content) and _has_any_phrase(content, ("推薦", "建議"))


def _extract_target_color_hint(normalized_text):
    content = (normalized_text or "").lower()
    if not content:
        return ""
    color_tokens = (
        "藍色", "藍", "粉色", "粉紅", "銀色", "銀", "金色", "金", "紫色", "紫",
        "橘色", "橘", "紅色", "紅", "灰色", "灰", "黑色", "黑", "棕色", "棕",
    )
    for token in color_tokens:
        if token in content:
            return token
    return ""


def _next_task_free_text_question(conversation_text, latest_user_message="", slots=None):
    text = _normalize_task_free_text(conversation_text)
    slots = dict(slots or _empty_task_slots())
    flow_slots = _slots_with_confirmed_values(slots)
    direction = flow_slots.get("direction")

    required_slot = _next_required_slot_for_slots(slots, text)
    if required_slot and required_slot in _pending_slots_set(slots):
        confirmation = _pending_slot_confirmation_question(required_slot, slots)
        if confirmation:
            return confirmation

    if direction is None:
        return "你這次主要想做哪一類：染髮、燙髮，還是護髮？"

    if direction == "染髮":
        if not flow_slots.get("dye_detail"):
            return "你這次染髮比較接近全頭染，還是補染？"
        detail = _normalized_dye_detail(flow_slots.get("dye_detail"))
        if detail == "補染":
            return "收到，我會根據你的條件整理最適合的服務方案。"
        if detail != "全頭染":
            return "你這次染髮比較接近全頭染，還是補染？"
        if not flow_slots.get("target_color"):
            return "你想染後的顏色比較接近自然深色、一般棕色，還是高明度特殊色？"
        if not flow_slots.get("current_base"):
            candidate_base = _infer_current_base_candidate_from_text(text)
            if candidate_base and _is_affirmative_reply_text(latest_user_message):
                flow_slots["current_base"] = candidate_base
            elif candidate_base and not _is_negative_reply_text(latest_user_message):
                return f"你目前底色比較像「{candidate_base}」，這樣對嗎？"
            else:
                return "你目前的髮色底色是自然黑髮、已染深色/中深色，還是已染淺色/已漂過？"
        if _needs_bleach_for_slots(flow_slots) and not flow_slots.get("bleach_accept"):
            return "若達到目標色可能需要漂髮，你可以接受嗎？"
        if _is_bleach_design_direct_ready(flow_slots):
            return "收到，我會根據你的條件整理最適合的服務方案。"
        if not flow_slots.get("brand_priority"):
            return "你這次更重視染後髮質修護，還是顏色表現與CP值？"
        candidates = _candidate_services_for_task_slots(flow_slots)
        if len(candidates) <= 1:
            return "收到，我會根據你的條件整理最適合的服務方案。"
        if not flow_slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800、1801-2400、2401以上。"
        if _needs_tradeoff_priority(flow_slots, text) and not flow_slots.get("tradeoff_priority"):
            return "看起來預算與效果偏好有取捨，你想優先哪一個：預算，還是效果？"
        if not _has_budget_compatible_candidates(flow_slots, text):
            return "目前預算可能和條件不一致，你想提高預算，還是調整服務需求？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    if direction == "燙髮":
        if not flow_slots.get("perm_detail"):
            return "你想做整體燙髮、髮根燙，還是燙瀏海？"
        if not flow_slots.get("perm_blocker"):
            return "是否有不可燙條件：曾經漂過頭髮、目前懷孕、髮質嚴重受損或容易斷裂、以上皆無？"
        if flow_slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
            return "你的條件已命中不可操作限制，這次會先提供保守建議。"
        if flow_slots.get("perm_detail") in {"髮根燙", "燙瀏海"}:
            return "收到，我會根據你的條件整理最適合的服務方案。"
        if not flow_slots.get("perm_preference"):
            return "若是整體燙髮，你偏向平衡預算完成基本造型，還是重視燙後髮質與修護感？"
        if flow_slots.get("perm_preference") == "不確定" and not flow_slots.get("budget_range"):
            return "若你還不確定，預算大約落在哪一段？例如 1200以下、1201-1800、1801-2400、2401以上。"
        if not flow_slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800、1801-2400、2401以上。"
        if flow_slots.get("perm_preference") != "不確定":
            return "收到，我會根據你的條件整理最適合的服務方案。"
        if _needs_tradeoff_priority(flow_slots, text) and not flow_slots.get("tradeoff_priority"):
            return "看起來預算與效果偏好有取捨，你想優先哪一個：預算，還是效果？"
        if not _has_budget_compatible_candidates(flow_slots, text):
            return "目前預算可能和條件不一致，你想提高預算，還是調整服務需求？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    if direction == "護髮":
        if not flow_slots.get("treatment_detail"):
            return "你這次最想改善哪種髮絲狀況：受損修護、柔順抗毛躁，還是日常保養？"
        if not flow_slots.get("budget_range"):
            return "你的預算價位區間大約在哪裡？例如 1200以下、1201-1800。"
        if _needs_tradeoff_priority(flow_slots, text) and not flow_slots.get("tradeoff_priority"):
            return "看起來預算與效果偏好有取捨，你想優先哪一個：預算，還是效果？"
        if not _has_budget_compatible_candidates(flow_slots, text):
            return "目前預算可能和條件不一致，你想提高預算，還是調整服務需求？"
        return "收到，我會根據你的條件整理最適合的服務方案。"

    return "我需要再確認一個條件，才能準確推薦。你目前最在意的是預算、時間，還是髮況限制？"


def _pending_slot_confirmation_question(slot_key, slots):
    value = (slots or {}).get(slot_key)
    if not value:
        return ""
    if slot_key == "dye_detail":
        if value == "全頭染":
            return "我先理解成你這次是全頭染，這樣對嗎？"
        if value == "補染":
            return "我先理解成你這次是補染，這樣對嗎？"
    if slot_key == "perm_detail":
        if value == "整體燙髮":
            return "我先理解成你這次是整體燙髮，這樣對嗎？"
        if value == "髮根燙":
            return "我先理解成你想做髮根燙，這樣對嗎？"
        if value == "燙瀏海":
            return "我先理解成你想做燙瀏海，這樣對嗎？"
    if slot_key == "current_base":
        return f"我先理解成你目前底色是「{value}」，這樣對嗎？"
    if slot_key == "perm_preference":
        if value == "重視燙後髮質、柔順度與修護感":
            return "我先理解成你是重視燙後髮質與修護感，這樣對嗎？"
        if value == "平衡預算，完成基本燙髮造型":
            return "我先理解成你偏向先平衡預算完成基本造型，這樣對嗎？"
    if slot_key == "brand_priority":
        return f"我先理解成你這次偏好是「{value}」，這樣對嗎？"
    if slot_key == "tradeoff_priority":
        return f"我先理解成你想以「{value.replace('以', '').replace('為優先', '')}」為主，這樣對嗎？"
    return ""


def _next_required_slot_for_slots(slots, normalized_text):
    flow_slots = _slots_with_confirmed_values(slots)
    direction = (flow_slots or {}).get("direction")
    if not direction:
        return "direction"

    if direction == "染髮":
        detail = _normalized_dye_detail((flow_slots or {}).get("dye_detail"))
        if not detail:
            return "dye_detail"
        if detail == "補染":
            return None
        if detail != "全頭染":
            return "dye_detail"
        if not (flow_slots or {}).get("target_color"):
            return "target_color"
        if not (flow_slots or {}).get("current_base"):
            return "current_base"
        if _needs_bleach_for_slots(flow_slots) and not (flow_slots or {}).get("bleach_accept"):
            return "bleach_accept"
        if _is_bleach_design_direct_ready(flow_slots):
            return None
        if not (flow_slots or {}).get("brand_priority"):
            return "brand_priority"
        candidates = _candidate_services_for_task_slots(flow_slots)
        if len(candidates) <= 1:
            return None
        if not (flow_slots or {}).get("budget_range"):
            return "budget_range"
        if _needs_tradeoff_priority(flow_slots, normalized_text) and not (flow_slots or {}).get("tradeoff_priority"):
            return "tradeoff_priority"
        if not _has_budget_compatible_candidates(flow_slots, normalized_text):
            return "budget_adjustment"
        return None

    if direction == "燙髮":
        if not (flow_slots or {}).get("perm_detail"):
            return "perm_detail"
        if not (flow_slots or {}).get("perm_blocker"):
            return "perm_blocker"
        if (flow_slots or {}).get("perm_blocker") in PERM_HARD_BLOCKERS:
            return None
        if (flow_slots or {}).get("perm_detail") in {"髮根燙", "燙瀏海"}:
            return None
        if not (flow_slots or {}).get("perm_preference"):
            return "perm_preference"
        if not (flow_slots or {}).get("budget_range"):
            return "budget_range"
        if (flow_slots or {}).get("perm_preference") != "不確定":
            return None
        if _needs_tradeoff_priority(flow_slots, normalized_text) and not (flow_slots or {}).get("tradeoff_priority"):
            return "tradeoff_priority"
        if not _has_budget_compatible_candidates(flow_slots, normalized_text):
            return "budget_adjustment"
        return None

    if direction == "護髮":
        if not (flow_slots or {}).get("treatment_detail"):
            return "treatment_detail"
        if not (flow_slots or {}).get("budget_range"):
            return "budget_range"
        if _needs_tradeoff_priority(flow_slots, normalized_text) and not (flow_slots or {}).get("tradeoff_priority"):
            return "tradeoff_priority"
        if not _has_budget_compatible_candidates(flow_slots, normalized_text):
            return "budget_adjustment"
        return None

    return None


def _is_uncertain_reply_text(normalized_text):
    return _has_any_phrase(
        normalized_text,
        (
            "都可以",
            "我不確定",
            "不確定",
            "不知道",
            "不清楚",
            "不確定要選哪個",
            "不確定要選哪種",
            "不知道要選哪個",
            "不知道要選哪種",
            "看你建議",
            "都行",
            "隨便",
            "沒差",
            "都想要",
        ),
    )


def _task_slots_progressed(previous_slots, current_slots):
    if not isinstance(previous_slots, dict) or not isinstance(current_slots, dict):
        return False
    for key in TASK_SLOT_ENUMS:
        if previous_slots.get(key) != current_slots.get(key):
            return True
    if previous_slots.get("budget_range") != current_slots.get("budget_range"):
        return True
    return False



def _clear_cross_direction_slots(slots):
    direction = (slots or {}).get("direction")
    if direction == "染髮":
        slots["perm_detail"] = None
        slots["perm_blocker"] = None
        slots["perm_preference"] = None
        slots["treatment_detail"] = None
    elif direction == "燙髮":
        slots["dye_detail"] = None
        slots["target_color"] = None
        slots["current_base"] = None
        slots["bleach_accept"] = None
        slots["brand_priority"] = None
        slots["treatment_detail"] = None
    elif direction == "護髮":
        slots["dye_detail"] = None
        slots["target_color"] = None
        slots["current_base"] = None
        slots["bleach_accept"] = None
        slots["brand_priority"] = None
        slots["perm_detail"] = None
        slots["perm_blocker"] = None
        slots["perm_preference"] = None


def _normalize_task_free_text(text):
    normalized = (text or "").strip()
    if not normalized:
        return normalized

    lowered = normalized.lower()
    for raw, canonical in FREE_TEXT_NORMALIZE_MAP.items():
        lowered = lowered.replace(raw.lower(), canonical)

    return lowered


def _extract_task_free_text_slots_rule(text):
    normalized = _normalize_task_free_text(text)
    slots = {"budget_range": _detect_budget_range(normalized)}

    for slot_key, candidates in TASK_SLOT_KEYWORDS.items():
        slots[slot_key] = _detect_slot_value(normalized, candidates)

    return slots


def _extract_task_slots(text):
    """Legacy helper retained for non-FSM callers.

    Step 4 removes LLM/global slot extraction from task-led free-text flow.
    This fallback is rule-only and should not be used to drive task FSM state.
    """
    return _extract_task_free_text_slots_rule(_normalize_task_free_text(text))


def _bridge_cross_domain_preference_for_perm(merged_slots, rule_slots, normalized_text):
    direction = (merged_slots or {}).get("direction")
    if direction != "燙髮":
        return
    if (merged_slots or {}).get("perm_preference"):
        return

    explicit_perm = (rule_slots or {}).get("perm_preference")
    if explicit_perm in TASK_SLOT_ENUMS.get("perm_preference", ()):
        merged_slots["perm_preference"] = explicit_perm
        return

    if _has_any_phrase(
        normalized_text,
        (
            "重視髮質",
            "重視髮質修護",
            "在意髮質",
            "我在意髮質",
            "髮質很重要",
            "重視修護",
            "修護優先",
            "重視燙後髮質",
        ),
    ):
        merged_slots["perm_preference"] = "重視燙後髮質、柔順度與修護感"
        return

    if _has_any_phrase(
        normalized_text,
        (
            "平衡預算",
            "預算優先",
            "價格優先",
            "cp值",
            "cp 值",
        ),
    ):
        merged_slots["perm_preference"] = "平衡預算，完成基本燙髮造型"


def _extract_task_slots_with_llm(normalized_text):
    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    if provider != "ollama":
        _debug_log("slot_extract_llm_skipped", provider=provider)
        return None

    model = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    endpoint = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat").strip()
    resolved_endpoint = _resolve_ollama_endpoint(endpoint)
    use_openai_compat = _is_openai_compat_endpoint(endpoint)
    schema_text = (
        "direction: 染髮|燙髮|護髮|null\n"
        "dye_detail: 全頭染|補染|漂髮設計染|null\n"
        "target_color: 自然深色|一般棕色|高明度特殊色|null\n"
        "current_base: 自然黑髮|已染深色/中深色|已染淺色/已漂過|null\n"
        "bleach_accept: 可接受漂髮|希望不漂髮|null\n"
        "brand_priority: 重視染後髮質修護|重視顏色表現與CP值|兩者都重視|null\n"
        "tradeoff_priority: 以預算為優先|以效果為優先|我不確定|null\n"
        "perm_detail: 整體燙髮|髮根燙|燙瀏海|null\n"
        "perm_blocker: 曾經漂過頭髮|目前懷孕|髮質嚴重受損或容易斷裂|以上皆無|null\n"
        "perm_preference: 平衡預算，完成基本燙髮造型|重視燙後髮質、柔順度與修護感|不確定|null\n"
        "treatment_detail: 受損修護|柔順抗毛躁|日常保養|null\n"
        "budget_range: 1200以下|1201-1800|1801-2400|2401以上|已提供預算|null"
    )
    system_prompt = (
        "你是欄位抽取器。只回傳 JSON。"
        "將使用者語句映射到既定欄位，沒提到就填 null。"
    )
    user_prompt = f"輸入文本：{normalized_text}\n\n請依照這個 schema 回傳 JSON：\n{schema_text}"
    if use_openai_compat:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 220,
            },
        }

    request = urllib.request.Request(
        resolved_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        _debug_log("slot_extract_llm_request_failed")
        return None

    text = _extract_ollama_text(response_data)
    parsed = _parse_model_json(text)
    if not isinstance(parsed, dict):
        _debug_log("slot_extract_llm_parse_failed", raw_preview=(text or "")[:160])
        return None

    validated = _validate_task_slot_payload(parsed)
    _debug_log("slot_extract_llm_success", parsed=parsed, validated=validated)
    return validated


def _validate_task_slot_payload(parsed):
    validated = {}
    for slot_key, allowed_values in TASK_SLOT_ENUMS.items():
        value = _normalize_llm_slot_value(slot_key, parsed.get(slot_key))
        if isinstance(value, str) and value in allowed_values:
            validated[slot_key] = value
        else:
            validated[slot_key] = None

    budget = parsed.get("budget_range")
    if isinstance(budget, str) and budget in {"1200以下", "1201-1800", "1801-2400", "2401以上", "已提供預算", BUDGET_NO_PREFERENCE}:
        validated["budget_range"] = budget
    else:
        validated["budget_range"] = None

    return validated


def _normalize_llm_slot_value(slot_key, value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    lowered = text.lower()
    if not text:
        return value

    if slot_key == "dye_detail":
        if "補染" in text:
            return "補染"
        if "全頭" in text or "整頭" in text:
            return "全頭染"
        if "漂" in text and "染" in text:
            return "漂髮設計染"

    if slot_key == "target_color":
        if any(token in text for token in ("粉", "金", "銀", "灰", "白金", "紫", "藍", "橘", "紅", "特殊")):
            return "高明度特殊色"
        if any(token in text for token in ("棕", "咖啡", "茶色", "可可")):
            return "一般棕色"
        if any(token in text for token in ("黑", "深色", "自然深")):
            return "自然深色"

    if slot_key == "current_base":
        if any(token in text for token in ("自然黑", "黑髮", "原生", "沒染過", "天生黑")):
            return "自然黑髮"
        if any(token in text for token in ("棕", "咖啡", "茶色", "可可", "深棕", "中深", "已染深色")):
            return "已染深色/中深色"
        if any(token in text for token in ("金", "銀", "淺色", "漂過", "已漂", "白金", "奶金")):
            return "已染淺色/已漂過"

    if slot_key == "bleach_accept":
        if any(token in lowered for token in ("不想漂", "不要漂", "不漂", "不考慮漂", "先不要漂", "不能漂")):
            return "希望不漂髮"
        if any(token in lowered for token in ("可以漂", "可漂", "接受漂", "能漂", "可接受漂", "ok漂")):
            return "可接受漂髮"

    return value


def _detect_slot_value(text, candidates):
    for canonical in candidates.keys():
        if canonical and canonical in text:
            return canonical
    for canonical, keywords in candidates.items():
        if _has_any_phrase(text, keywords):
            return canonical
    return None


def _detect_budget_range(text):
    if not _has_budget_info(text):
        return None

    if _has_any_phrase(
        text,
        (
            "預算不確定",
            "價位不確定",
            "預算我不確定",
            "我不確定預算",
            "預算都可以",
            "價位都可以",
            "預算可彈性",
            "預算都可",
            "價位都可",
            "預算可以",
        ),
    ):
        return BUDGET_NO_PREFERENCE

    if _has_any_phrase(text, ("1200以下", "1200 以下", "千二以下")):
        return "1200以下"
    if _has_any_phrase(text, ("1201-1800", "1201 到 1800", "1201~1800")):
        return "1201-1800"
    if _has_any_phrase(text, ("1801-2400", "1801 到 2400", "1801~2400")):
        return "1801-2400"
    if _has_any_phrase(text, ("2401以上", "2401 以上", "2500以上")):
        return "2401以上"

    constraint = _parse_budget_constraint(text)
    if not constraint:
        return "已提供預算"

    min_budget = constraint.get("min")
    max_budget = constraint.get("max")
    if max_budget is not None and max_budget <= 1200:
        return "1200以下"
    if min_budget is not None and max_budget is not None and min_budget >= 1201 and max_budget <= 1800:
        return "1201-1800"
    if min_budget is not None and max_budget is not None and min_budget >= 1801 and max_budget <= 2400:
        return "1801-2400"
    if min_budget is not None and min_budget >= 2401:
        return "2401以上"

    return "已提供預算"


def _parse_budget_constraint(text):
    content = (text or "").replace(",", "")
    if not content:
        return None

    range_match = re.search(r"(\d{3,5})\s*[-~～到至]\s*(\d{3,5})", content)
    if range_match:
        left = int(range_match.group(1))
        right = int(range_match.group(2))
        return {"min": min(left, right), "max": max(left, right)}

    under_match = re.search(r"(\d{3,5})\s*(以下|以內|以内|內)", content)
    if under_match:
        return {"min": 0, "max": int(under_match.group(1))}

    over_match = re.search(r"(\d{3,5})\s*(以上|起)", content)
    if over_match:
        return {"min": int(over_match.group(1)), "max": None}

    # Single-number hints like "2000左右/大概2000/2000塊"
    single_match = re.search(r"(\d{3,5})\s*(元|塊|块)?\s*(左右|大概|約|约)?", content)
    if single_match:
        amount = int(single_match.group(1))
        return {"min": amount, "max": amount}

    return None


def _is_specific_budget_bucket(value):
    token = str(value or "")
    return token in {"1201-1800", "1801-2400"} or ("1200" in token and "-" not in token) or ("2401" in token and "-" not in token)


def _budget_constraint_from_budget_range(budget_range, normalized_text):
    token = str(budget_range or "")
    if token == BUDGET_NO_PREFERENCE:
        return None
    if token == "1201-1800":
        return {"min": 1201, "max": 1800}
    if token == "1801-2400":
        return {"min": 1801, "max": 2400}
    if "1200" in token and "-" not in token:
        return {"min": None, "max": 1200}
    if "2401" in token and "-" not in token:
        return {"min": 2401, "max": None}

    parsed = _parse_budget_constraint(normalized_text)
    if not parsed:
        return None
    return {"min": parsed.get("min"), "max": parsed.get("max")}


def _slot_evidence_level(slot_key, value, normalized_text):
    """Return one of: explicit, derived, none."""
    if not value:
        return "none"

    if slot_key == "bleach_accept":
        # Must be explicit user stance; question intent is not acceptance.
        return "explicit" if _infer_bleach_accept_from_text(normalized_text) == value else "none"

    if slot_key == "budget_range":
        return "explicit" if _detect_budget_range(normalized_text) == value else "none"

    if slot_key == "perm_blocker":
        return "explicit" if _slot_value_supported_by_user_text(slot_key, value, normalized_text) else "none"

    if slot_key == "current_base":
        inferred = _infer_current_base_candidate_from_text(normalized_text)
        if inferred == value or _slot_value_supported_by_user_text(slot_key, value, normalized_text):
            return "explicit"
        return "derived"

    if _slot_value_supported_by_user_text(slot_key, value, normalized_text):
        return "explicit"

    if slot_key in {
        "direction",
        "dye_detail",
        "target_color",
        "brand_priority",
        "tradeoff_priority",
        "perm_detail",
        "perm_preference",
        "treatment_detail",
    }:
        return "derived"

    return "none"


def _slot_requires_confirmation(slot_key):
    return slot_key in {
        "dye_detail",
        "perm_detail",
        "current_base",
        "perm_preference",
        "brand_priority",
        "tradeoff_priority",
    }


def _pending_slots_set(slots):
    if not isinstance(slots, dict):
        return set()
    pending = slots.get("_pending_slots")
    if not isinstance(pending, (list, tuple, set)):
        return set()
    return {item for item in pending if isinstance(item, str)}


def _slot_value_for_flow(slots, slot_key):
    if slot_key in _pending_slots_set(slots):
        return None
    return (slots or {}).get(slot_key)


def _slots_with_confirmed_values(slots):
    if not isinstance(slots, dict):
        return {}
    result = dict(slots)
    for slot_key in _pending_slots_set(slots):
        result[slot_key] = None
    return result


def _slot_value_supported_by_user_text(slot_key, value, normalized_text):
    if not value:
        return False
    content = (normalized_text or "").lower()
    if not content:
        return False
    if value.lower() in content:
        return True
    phrases = TASK_SLOT_KEYWORDS.get(slot_key, {}).get(value, ())
    return any((phrase or "").lower() in content for phrase in phrases)


def _is_bleach_question_text(normalized_text):
    content = (normalized_text or "").lower()
    if not content:
        return False
    return _has_any_phrase(
        content,
        ("要漂嗎", "需要漂嗎", "會漂嗎", "會不會漂", "要不要漂", "漂髮嗎", "能不能不漂", "需不需要漂"),
    )


def _infer_bleach_accept_from_text(normalized_text):
    content = (normalized_text or "").lower()
    if not content:
        return None

    # explicit rejection has highest priority
    if _has_any_phrase(
        content,
        (
            "不想漂",
            "不要漂",
            "不想要漂髮",
            "我還是不想要漂髮",
            "先不要漂",
            "不考慮漂",
            "不能漂",
            "不可以漂",
        ),
    ):
        return "希望不漂髮"

    # explicit acceptance
    if _has_any_phrase(
        content,
        ("可接受漂髮", "可以漂", "可漂", "接受漂", "能漂", "ok 漂", "可以接受漂髮"),
    ):
        return "可接受漂髮"

    # question intent should not be treated as acceptance
    if _is_bleach_question_text(content):
        return None

    return None


def _infer_current_base_candidate_from_text(normalized_text):
    content = (normalized_text or "").lower()
    if not content:
        return None

    # Prioritize explicit "current-state" phrases to avoid confusing target color with base color.
    if not _has_any_phrase(content, ("目前", "現在", "底色", "原本", "本來", "我目前", "我現在")):
        return None

    if _has_any_phrase(
        content,
        ("已漂過", "漂過", "金髮", "金色頭髮", "淺色底", "淺金", "奶金", "白金", "銀髮"),
    ):
        return "已染淺色/已漂過"

    if _has_any_phrase(
        content,
        ("可可棕", "棕色", "棕髮", "咖啡色", "茶色", "深棕", "中深色", "已染深色"),
    ):
        return "已染深色/中深色"

    if _has_any_phrase(content, ("自然黑髮", "黑髮", "原生髮", "沒染過", "天生黑")):
        return "自然黑髮"

    return None


def _infer_direction_from_slot_bundle(slot_bundle):
    if not isinstance(slot_bundle, dict):
        return None
    if slot_bundle.get("dye_detail") or slot_bundle.get("target_color") or slot_bundle.get("current_base") or slot_bundle.get("bleach_accept") or slot_bundle.get("brand_priority"):
        return "染髮"
    if slot_bundle.get("perm_detail") or slot_bundle.get("perm_blocker") or slot_bundle.get("perm_preference"):
        return "燙髮"
    if slot_bundle.get("treatment_detail"):
        return "護髮"
    return None


def _llm_current_base_confidence(value, normalized_text):
    content = (normalized_text or "").lower()
    if not value or not content:
        return "low"

    signal_map = {
        "自然黑髮": (
            "自然黑髮",
            "原生黑髮",
            "天生黑髮",
            "沒染過",
            "黑髮",
            "自然髮色黑",
        ),
        "已染深色/中深色": (
            "已染深色",
            "染過深色",
            "中深色",
            "深色",
            "深棕",
            "咖啡色底",
        ),
        "已染淺色/已漂過": (
            "已染淺色",
            "淺色底",
            "漂過",
            "已漂",
            "金髮",
            "金色頭髮",
            "金色髮",
            "淺金",
            "漂金",
            "退色很淺",
        ),
    }
    if _has_any_phrase(content, signal_map.get(value, ())):
        return "high"
    return "low"


def _allow_llm_current_base_in_context(merged_slots, llm_slots, normalized_text):
    merged_direction = (merged_slots or {}).get("direction")
    llm_direction = (llm_slots or {}).get("direction")
    if merged_direction == "染髮" or llm_direction == "染髮":
        return True
    return _has_any_phrase(
        normalized_text,
        ("目前", "現在", "底色", "髮色", "我是", "我目前是", "我現在是"),
    )


def _llm_target_color_confidence(value, normalized_text):
    content = (normalized_text or "").lower()
    if not value or not content:
        return "low"

    signal_map = {
        "自然深色": (
            "自然深色",
            "自然黑",
            "深色",
            "黑色",
            "深咖",
        ),
        "一般棕色": (
            "棕色",
            "咖啡色",
            "可可棕",
            "茶色",
            "奶茶棕",
            "栗子棕",
            "棕",
        ),
        "高明度特殊色": (
            "高明度",
            "特殊色",
            "金色",
            "金髮",
            "金发",
            "銀色",
            "灰色",
            "白金",
            "粉色",
            "藍色",
            "紫色",
            "橘色",
            "紅色",
            "霧金",
            "亞麻金",
            "奶金",
        ),
    }
    if _has_any_phrase(content, signal_map.get(value, ())):
        return "high"
    return "low"


def _budget_value_supported_by_user_text(value, normalized_text):
    if not value:
        return False
    if value == BUDGET_NO_PREFERENCE:
        return _has_any_phrase(
            normalized_text,
            (
                "預算不確定",
                "價位不確定",
                "預算我不確定",
                "我不確定預算",
                "預算都可以",
                "價位都可以",
                "預算可彈性",
                "預算都可",
                "價位都可",
                "預算可以",
            ),
        )
    detected = _detect_budget_range(normalized_text)
    if detected == value:
        return True
    if _is_specific_budget_bucket(value):
        return False
    return _has_budget_info(normalized_text)


def _service_price_overlaps_budget(service_bounds, budget_constraint):
    service_min = service_bounds.get("min")
    service_max = service_bounds.get("max")
    if service_min is None or service_max is None:
        return False

    budget_min = budget_constraint.get("min")
    budget_max = budget_constraint.get("max")

    if budget_min is not None and service_max < budget_min:
        return False
    if budget_max is not None and service_min > budget_max:
        return False
    return True


def _filter_services_by_budget(service_names, budget_range, normalized_text):
    constraint = _budget_constraint_from_budget_range(budget_range, normalized_text)
    if not constraint:
        return []

    matched = []
    for service_name in service_names:
        bounds = SERVICE_PRICE_BOUNDS.get(service_name)
        if not bounds:
            continue
        if _service_price_overlaps_budget(bounds, constraint):
            matched.append(service_name)
    return matched


def _service_names_by_category_index(index):
    if index < 0 or index >= len(SERVICE_CATEGORIES):
        return []
    return [service.get("name") for service in SERVICE_CATEGORIES[index].get("services", []) if service.get("name")]


def _rank_treatment_services_by_preference(slots, treatment_services):
    if not treatment_services:
        return []

    scores = {service_name: 0 for service_name in treatment_services}
    detail = slots.get("treatment_detail")
    detail_values = TASK_SLOT_ENUMS.get("treatment_detail", ())

    if len(detail_values) >= 3:
        # Soft preference: the selected concern is weighted highest, but others keep a chance.
        if detail == detail_values[0]:  # 受損修護
            bonus_map = {0: 3, 1: 2, 2: 1}
        elif detail == detail_values[1]:  # 柔順抗毛躁
            bonus_map = {1: 3, 0: 2, 2: 2}
        elif detail == detail_values[2]:  # 日常保養
            bonus_map = {2: 3, 1: 2, 0: 1}
        else:
            bonus_map = {}

        for index, bonus in bonus_map.items():
            if index < len(treatment_services):
                scores[treatment_services[index]] += bonus

    stable_order = {name: index for index, name in enumerate(treatment_services)}
    return sorted(treatment_services, key=lambda name: (-scores.get(name, 0), stable_order.get(name, 999)))


def _normalized_dye_detail(detail):
    if detail == "漂髮設計染":
        return "全頭染"
    return detail



def _is_bleach_design_direct_ready(slots):
    """Return True when bleach acceptance already determines the dye service.

    For high-brightness/special-color full-head dye, accepting bleach directly
    maps to the bleach design dye path, so the task-led flow should not ask
    brand_priority/budget questions that only distinguish non-bleach dye options.
    """
    if not isinstance(slots, dict):
        return False
    return (
        slots.get("direction") == "染髮"
        and _normalized_dye_detail(slots.get("dye_detail")) == "全頭染"
        and slots.get("target_color") == "高明度特殊色"
        and slots.get("bleach_accept") == "可接受漂髮"
        and _needs_bleach_for_slots(slots)
    )

def _needs_bleach_for_slots(slots):
    target = slots.get("target_color")
    current = slots.get("current_base")
    if not target or not current:
        return False
    if target == "高明度特殊色":
        return True
    if target == "一般棕色" and current == "自然黑髮":
        return True
    return False


def _is_budget_no_preference_value(budget_range, normalized_text=""):
    token = str(budget_range or "").strip()
    if token in {BUDGET_NO_PREFERENCE, UNCERTAIN_BUTTON_LABEL, "不確定"}:
        return True
    return _has_any_phrase(
        normalized_text,
        (
            "預算不確定",
            "價位不確定",
            "預算我不確定",
            "我不確定預算",
            "預算都可以",
            "價位都可以",
            "預算可彈性",
            "預算都可",
            "價位都可",
            "預算可以",
        ),
    )


def _candidate_services_for_task_slots(slots):
    direction = slots.get("direction")
    direction_values = TASK_SLOT_ENUMS.get("direction", ())
    if direction is None or len(direction_values) < 3:
        return []

    dye_direction, perm_direction, treatment_direction = direction_values[0], direction_values[1], direction_values[2]

    if direction == dye_direction:
        dye_services = _service_names_by_category_index(0)
        if len(dye_services) < 4:
            return dye_services

        detail = _normalized_dye_detail(slots.get("dye_detail"))
        bleach_accept = slots.get("bleach_accept")
        brand_priority = slots.get("brand_priority")
        dye_detail_values = TASK_SLOT_ENUMS.get("dye_detail", ())
        brand_values = TASK_SLOT_ENUMS.get("brand_priority", ())

        if len(dye_detail_values) >= 2 and detail == dye_detail_values[1]:
            return [dye_services[2]]
        if detail == "全頭染" and _needs_bleach_for_slots(slots) and bleach_accept == "可接受漂髮":
            return [dye_services[3]]

        candidates = []
        if len(brand_values) >= 2 and brand_priority == brand_values[0]:
            candidates.extend([dye_services[1], dye_services[0]])
        elif len(brand_values) >= 2 and brand_priority == brand_values[1]:
            candidates.extend([dye_services[0], dye_services[1]])
        else:
            candidates.extend([dye_services[0], dye_services[1]])

        deduped = []
        for item in candidates:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    if direction == perm_direction:
        perm_services = _service_names_by_category_index(1)
        if len(perm_services) < 4:
            return perm_services

        detail = slots.get("perm_detail")
        blocker = slots.get("perm_blocker")
        preference = slots.get("perm_preference")
        perm_detail_values = TASK_SLOT_ENUMS.get("perm_detail", ())

        if blocker in PERM_HARD_BLOCKERS:
            return []

        if len(perm_detail_values) >= 3 and detail == perm_detail_values[1]:
            return [perm_services[2]]
        if len(perm_detail_values) >= 3 and detail == perm_detail_values[2]:
            return [perm_services[3]]
        if preference == "重視燙後髮質、柔順度與修護感":
            return [perm_services[1], perm_services[0]]
        if preference in {"平衡預算，完成基本燙髮造型", "不確定"}:
            return [perm_services[0], perm_services[1]]
        return [perm_services[0], perm_services[1]]

    if direction == treatment_direction:
        treatment_services = _service_names_by_category_index(2)
        if len(treatment_services) < 3:
            return treatment_services

        return _rank_treatment_services_by_preference(slots, treatment_services)

    return []


def _has_no_bleach_constraint(slots, normalized_text):
    if slots.get("bleach_accept") == "希望不漂髮":
        return True
    no_bleach_phrases = TASK_SLOT_KEYWORDS.get("bleach_accept", {}).get("希望不漂髮", ())
    return _has_any_phrase(normalized_text, no_bleach_phrases)


def _has_budget_compatible_candidates(slots, normalized_text):
    budget_range = slots.get("budget_range")
    if not budget_range:
        return False
    candidates = _candidate_services_for_task_slots(slots)
    if not candidates:
        return False
    if _is_budget_no_preference_value(budget_range, normalized_text):
        return True
    filtered = _filter_services_by_budget(candidates, budget_range, normalized_text)
    return len(filtered) > 0


def _needs_tradeoff_priority(slots, normalized_text):
    direction = slots.get("direction")
    if direction not in {"染髮", "護髮"}:
        return False
    if not slots.get("budget_range"):
        return False
    if _is_budget_no_preference_value(slots.get("budget_range"), normalized_text):
        return False

    ranked_candidates = _candidate_services_for_task_slots(slots)
    if len(ranked_candidates) < 2:
        return False

    budget_candidates = _filter_services_by_budget(ranked_candidates, slots.get("budget_range"), normalized_text)
    if not budget_candidates:
        return False

    return ranked_candidates[0] != budget_candidates[0]


def _build_task_text_final_output(conversation_text):
    normalized_text = _normalize_task_free_text(conversation_text)
    if not normalized_text:
        return None

    slots = _extract_task_slots(normalized_text)
    if _has_no_bleach_constraint(slots, normalized_text):
        slots["bleach_accept"] = "希望不漂髮"

    if slots.get("direction") == "燙髮" and slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
        return _blocked_perm_final_output(slots.get("perm_blocker"))

    ranked_candidates = _candidate_services_for_task_slots(slots)
    if not ranked_candidates:
        return None

    if slots.get("direction") == "染髮" and _normalized_dye_detail(slots.get("dye_detail")) == "補染":
        service_name = ranked_candidates[0]
        if service_name not in SERVICE_HINTS:
            return None
        reason = _build_task_recommendation_reason(
            service_name,
            slots,
            normalized_text,
            ranked_candidates=ranked_candidates,
        )
        return _final_output_for(service_name, reason=reason)

    if (
        slots.get("direction") == "染髮"
        and _normalized_dye_detail(slots.get("dye_detail")) == "全頭染"
        and _needs_bleach_for_slots(slots)
        and slots.get("bleach_accept") == "可接受漂髮"
    ):
        service_name = ranked_candidates[0]
        if service_name not in SERVICE_HINTS:
            return None
        reason = _build_task_recommendation_reason(
            service_name,
            slots,
            normalized_text,
            ranked_candidates=ranked_candidates,
        )
        return _final_output_for(service_name, reason=reason)

    if slots.get("direction") == "燙髮":
        detail = slots.get("perm_detail")
        preference = slots.get("perm_preference")
        if detail in {"髮根燙", "燙瀏海"}:
            service_name = ranked_candidates[0]
            if service_name not in SERVICE_HINTS:
                return None
            reason = _build_task_recommendation_reason(
                service_name,
                slots,
                normalized_text,
                ranked_candidates=ranked_candidates,
            )
            return _final_output_for(service_name, reason=reason)

        if preference in {"平衡預算，完成基本燙髮造型", "重視燙後髮質、柔順度與修護感"}:
            service_name = ranked_candidates[0]
            if service_name not in SERVICE_HINTS:
                return None
            reason = _build_task_recommendation_reason(
                service_name,
                slots,
                normalized_text,
                ranked_candidates=ranked_candidates,
            )
            return _final_output_for(service_name, reason=reason)

    budget_range = slots.get("budget_range")
    if _is_budget_no_preference_value(budget_range, normalized_text):
        filtered = ranked_candidates
    else:
        filtered = _filter_services_by_budget(ranked_candidates, budget_range, normalized_text)
    if not filtered and slots.get("tradeoff_priority") != "以效果為優先":
        return None

    use_candidates = filtered
    if _needs_tradeoff_priority(slots, normalized_text):
        priority = slots.get("tradeoff_priority")
        if priority == "以效果為優先":
            use_candidates = ranked_candidates
        elif priority in {"以預算為優先", "我不確定"}:
            use_candidates = filtered
        else:
            return None

    if not use_candidates:
        return None

    service_name = use_candidates[0]
    if service_name not in SERVICE_HINTS:
        return None
    reason = _build_task_recommendation_reason(service_name, slots, normalized_text, ranked_candidates=use_candidates)
    return _final_output_for(service_name, reason=reason)



def _build_task_text_final_output_from_slots(slots):
    if not isinstance(slots, dict):
        return None

    normalized_text = _slots_to_normalized_text(slots)
    if _has_no_bleach_constraint(slots, normalized_text):
        slots = dict(slots)
        slots["bleach_accept"] = "希望不漂髮"

    if slots.get("direction") == "燙髮" and slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
        return _blocked_perm_final_output(slots.get("perm_blocker"))

    ranked_candidates = _candidate_services_for_task_slots(slots)
    if not ranked_candidates:
        return None

    if slots.get("direction") == "染髮" and _normalized_dye_detail(slots.get("dye_detail")) == "補染":
        service_name = ranked_candidates[0]
        if service_name not in SERVICE_HINTS:
            return None
        reason = _build_task_recommendation_reason(
            service_name,
            slots,
            normalized_text,
            ranked_candidates=ranked_candidates,
        )
        return _final_output_for(service_name, reason=reason)

    if (
        slots.get("direction") == "染髮"
        and _normalized_dye_detail(slots.get("dye_detail")) == "全頭染"
        and _needs_bleach_for_slots(slots)
        and slots.get("bleach_accept") == "可接受漂髮"
    ):
        service_name = ranked_candidates[0]
        if service_name not in SERVICE_HINTS:
            return None
        reason = _build_task_recommendation_reason(
            service_name,
            slots,
            normalized_text,
            ranked_candidates=ranked_candidates,
        )
        return _final_output_for(service_name, reason=reason)

    if slots.get("direction") == "燙髮":
        detail = slots.get("perm_detail")
        preference = slots.get("perm_preference")
        if detail in {"髮根燙", "燙瀏海"}:
            service_name = ranked_candidates[0]
            if service_name not in SERVICE_HINTS:
                return None
            reason = _build_task_recommendation_reason(
                service_name,
                slots,
                normalized_text,
                ranked_candidates=ranked_candidates,
            )
            return _final_output_for(service_name, reason=reason)

        if preference in {"平衡預算，完成基本燙髮造型", "重視燙後髮質、柔順度與修護感"}:
            service_name = ranked_candidates[0]
            if service_name not in SERVICE_HINTS:
                return None
            reason = _build_task_recommendation_reason(
                service_name,
                slots,
                normalized_text,
                ranked_candidates=ranked_candidates,
            )
            return _final_output_for(service_name, reason=reason)

    budget_range = slots.get("budget_range")
    if _is_budget_no_preference_value(budget_range, normalized_text):
        filtered = ranked_candidates
    else:
        filtered = _filter_services_by_budget(ranked_candidates, budget_range, normalized_text)
    if not filtered and slots.get("tradeoff_priority") != "以效果為優先":
        return None

    use_candidates = filtered
    if _needs_tradeoff_priority(slots, normalized_text):
        priority = slots.get("tradeoff_priority")
        if priority == "以效果為優先":
            use_candidates = ranked_candidates
        elif priority in {"以預算為優先", "我不確定"}:
            use_candidates = filtered
        else:
            return None

    if not use_candidates:
        return None

    service_name = use_candidates[0]
    if service_name not in SERVICE_HINTS:
        return None
    reason = _build_task_recommendation_reason(service_name, slots, normalized_text, ranked_candidates=use_candidates)
    return _final_output_for(service_name, reason=reason)


def _blocked_perm_final_output(blocker):
    blocker_text = str(blocker or "").strip() or "不可操作條件"
    return {
        "recommended_service": "暫不建議染燙",
        "reason": f"你目前條件包含「{blocker_text}」，為了安全與髮況穩定，暫不建議直接進行染燙類服務。",
        "next_step": "建議先由現場設計師評估髮況與風險，再決定是否可操作，必要時可先做修護型服務。",
    }


def _build_final_output(conversation_text, allow_inferred_recommendation):
    normalized_text = _normalize_task_free_text(conversation_text)
    no_bleach_requested = _has_any_phrase(
        normalized_text,
        TASK_SLOT_KEYWORDS.get("bleach_accept", {}).get("希望不漂髮", ()),
    )
    for service_name, details in SERVICE_HINTS.items():
        if service_name == "漂髮" and no_bleach_requested:
            continue
        if service_name in conversation_text:
            return _final_output_for(service_name)

    if not allow_inferred_recommendation:
        return None

    for service_name, keywords in RECOMMENDATION_RULES:
        if service_name == "漂髮" and no_bleach_requested:
            continue
        if any(keyword in conversation_text for keyword in keywords):
            return _final_output_for(service_name)

    return None


def _build_task_recommendation_reason(service_name, slots, normalized_text, ranked_candidates=None):
    if not isinstance(slots, dict):
        return SERVICE_HINTS[service_name]["reason"]

    conflict_text = _build_conflict_inference(slots, normalized_text)
    fit_text = _build_fit_inference(service_name, slots)
    comparison_text = _build_comparison_inference(service_name, slots, ranked_candidates)
    boundary_text = _build_boundary_inference(service_name, slots, normalized_text)

    parts = []
    if conflict_text:
        parts.append(conflict_text)
    parts.append(fit_text)
    if comparison_text:
        parts.append(comparison_text)
    if boundary_text:
        parts.append(boundary_text)
    parts.append(ONSITE_EVALUATION_NOTE)
    return "".join(parts)


def _profile_value(service_name, field):
    details = SERVICE_HINTS.get(service_name, {})
    profile = details.get("profile") if isinstance(details, dict) else {}
    if not isinstance(profile, dict):
        return ""
    return str(profile.get(field) or "").strip()


def _first_sentence(text):
    content = str(text or "").strip()
    if not content:
        return ""
    for delimiter in ("。", "；"):
        if delimiter in content:
            return content.split(delimiter)[0].strip()
    return content


def _build_conflict_inference(slots, normalized_text):
    direction = slots.get("direction")
    if _needs_tradeoff_priority(slots, normalized_text):
        chosen_priority = slots.get("tradeoff_priority")
        if chosen_priority == "以預算為優先":
            return "你的條件在預算與效果偏好間有取捨，本次會先依你的選擇以預算為優先。"
        if chosen_priority == "以效果為優先":
            return "你的條件在預算與效果偏好間有取捨，本次會先依你的選擇以效果為優先。"
        if chosen_priority == "我不確定":
            return "你的條件在預算與效果偏好間有取捨，因為你目前未明確指定優先順序，本次先以預算可行性優先。"

    if direction == "染髮":
        if slots.get("target_color") == "高明度特殊色" and _has_no_bleach_constraint(slots, normalized_text):
            return "你想要高明度特殊色，但同時明確希望不漂髮，這兩個條件在技術上會互相牽制。"
    if direction == "燙髮" and slots.get("perm_blocker") in PERM_HARD_BLOCKERS:
        return "你的條件命中不可操作限制，這次建議先以風險控管與現場評估為優先。"
    return ""


def _build_fit_inference(service_name, slots):
    direction = slots.get("direction")
    strong_point = _first_sentence(_profile_value(service_name, "效果強項"))
    difference = _first_sentence(_profile_value(service_name, "與同類服務差異"))
    tradeoff = _first_sentence(_profile_value(service_name, "代價或取捨"))
    emphasis = slots.get("brand_priority")
    budget = slots.get("budget_range")
    tradeoff_priority = slots.get("tradeoff_priority")

    if direction == "染髮":
        rationale_bits = []
        if emphasis:
            rationale_bits.append(f"你目前偏好是「{emphasis}」")
        if budget:
            rationale_bits.append(f"預算為「{budget}」")
        if tradeoff_priority:
            rationale_bits.append(f"你最後選擇「{tradeoff_priority}」")
        if slots.get("bleach_accept") == "希望不漂髮":
            rationale_bits.append("且有不漂髮的前提")
        basis = "、".join(rationale_bits) if rationale_bits else "你目前提供的條件"
        feature_text = strong_point or difference or SERVICE_HINTS[service_name]["reason"]
        return f"基於{basis}，推薦「{service_name}」；此方案的核心優勢是{feature_text}。"

    if direction == "燙髮":
        feature_text = strong_point or difference or SERVICE_HINTS[service_name]["reason"]
        return f"考量你的燙髮條件，推薦「{service_name}」，重點是{feature_text}。"

    if direction == "護髮":
        feature_text = strong_point or difference or SERVICE_HINTS[service_name]["reason"]
        return f"依照你的護髮需求，推薦「{service_name}」，主要原因是{feature_text}。"

    if tradeoff:
        return f"推薦「{service_name}」，整體較符合你目前需求；同時需注意{tradeoff}。"
    return f"推薦「{service_name}」，整體較符合你目前需求。"


def _comparison_pool_by_direction(direction):
    if direction == "染髮":
        return ["日本資生堂染髮", "日本哥德式染髮", "補染", "漂髮"]
    if direction == "燙髮":
        return ["日本資生堂燙髮", "日本哥德式燙髮", "髮根燙", "燙瀏海"]
    if direction == "護髮":
        return ["哥德式護髮", "哥德式可洛娜三劑式護髮", "鉑金修護"]
    return []


def _pick_comparison_target(service_name, slots, ranked_candidates):
    candidates = ranked_candidates if isinstance(ranked_candidates, list) else []
    for item in candidates:
        if item and item != service_name:
            return item

    for item in _comparison_pool_by_direction(slots.get("direction")):
        if item and item != service_name:
            return item
    return ""


def _build_comparison_inference(service_name, slots, ranked_candidates):
    target = _pick_comparison_target(service_name, slots, ranked_candidates)
    if not target:
        return ""

    difference = _first_sentence(_profile_value(service_name, "與同類服務差異"))
    if difference and target in difference:
        if difference.startswith("相較於"):
            return f"{difference}。"
        return f"相較於「{target}」，{difference}。"

    direction = slots.get("direction")
    if direction == "染髮":
        if target == "漂髮" and slots.get("bleach_accept") == "希望不漂髮":
            return "相較於「漂髮」，這個方案可保留不漂髮前提並降低化學負擔。"
        if slots.get("brand_priority") == "重視顏色表現與CP值" and service_name == "日本資生堂染髮":
            return f"相較於「{target}」，此方案更貼近你優先的顏色表現與CP值。"
        if slots.get("brand_priority") == "重視染後髮質修護" and service_name == "日本哥德式染髮":
            return f"相較於「{target}」，此方案把染後髮質修護放在更前面。"
    return f"相較於「{target}」，這個方案與你目前條件的匹配度更高。"


def _build_boundary_inference(service_name, slots, normalized_text):
    direction = slots.get("direction")
    not_fit = _first_sentence(_profile_value(service_name, "不適合或限制"))
    tradeoff = _first_sentence(_profile_value(service_name, "代價或取捨"))

    if direction == "染髮":
        if slots.get("target_color") == "高明度特殊色" and _has_no_bleach_constraint(slots, normalized_text):
            return "在不漂髮條件下，明度與通透感會較保守，與理想特殊色仍可能有落差。"
        if slots.get("target_color") == "高明度特殊色" and slots.get("bleach_accept") == "可接受漂髮":
            return "若要追求更高明度，後續退色速度與護髮成本通常會提高。"

    if tradeoff:
        return f"需要留意的是，{tradeoff}。"
    if not_fit:
        return f"限制面向上，{not_fit}。"
    return ""


def _final_output_for(service_name, reason=None):
    resolved_reason = str(reason).strip() if reason else SERVICE_HINTS[service_name]["reason"]
    return {
        "recommended_service": service_name,
        "reason": resolved_reason,
        "next_step": f"請參考此建議，並從左側服務內容中選擇你最想預約的方案。{ONSITE_EVALUATION_NOTE}",
    }


def _build_default_final_output(conversation_text):
    normalized_text = _normalize_task_free_text(conversation_text)
    no_bleach_requested = _has_any_phrase(
        normalized_text,
        TASK_SLOT_KEYWORDS.get("bleach_accept", {}).get("希望不漂髮", ()),
    )
    if "染後" in conversation_text or "染髮又在意髮質" in conversation_text:
        service_name = "日本哥德式染髮"
    elif "補染" in conversation_text or "補髮根" in conversation_text:
        service_name = "補染"
    elif ("漂" in conversation_text or "淺色" in conversation_text or "特殊髮色" in conversation_text) and not no_bleach_requested:
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
