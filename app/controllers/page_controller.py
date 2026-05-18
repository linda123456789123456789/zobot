from flask import Blueprint, redirect, render_template, request, url_for

from app.services.button_flow import get_button_options, get_initial_question


page_bp = Blueprint("pages", __name__)

CONDITIONS = {
    "A": {
        "input_mode": "button",
        "conversation_style": "task",
        "label": "按鈕選項 × 任務導向",
        "description": "參與者用按鈕回答，ZOBOT 依步驟引導到服務建議。",
    },
    "B": {
        "input_mode": "button",
        "conversation_style": "topic",
        "label": "按鈕選項 × 主題導向",
        "description": "參與者用按鈕回答，ZOBOT 先從髮況主題討論再整理建議。",
    },
    "C": {
        "input_mode": "text",
        "conversation_style": "task",
        "label": "自由輸入 × 任務導向",
        "description": "參與者自由打字，ZOBOT 依步驟詢問並引導到服務建議。",
    },
    "D": {
        "input_mode": "text",
        "conversation_style": "topic",
        "label": "自由輸入 × 主題導向",
        "description": "參與者自由打字，ZOBOT 先討論髮況與需求再整理建議。",
    },
}


@page_bp.get("/")
def index():
    return render_template("condition_select.html", conditions=CONDITIONS.items())


@page_bp.get("/select-condition/<condition>")
def select_condition(condition):
    condition = condition.upper()
    if condition not in CONDITIONS:
        condition = "A"

    return redirect(url_for("pages.chat_page", condition=condition))


@page_bp.get("/chat")
def chat_page():
    condition = request.args.get("condition", "A").upper()

    if condition not in CONDITIONS:
        return redirect(url_for("pages.chat_page", condition="A"))

    input_mode = CONDITIONS[condition]["input_mode"]
    conversation_style = CONDITIONS[condition]["conversation_style"]

    return render_template(
        "chat.html",
        condition=condition,
        input_mode=input_mode,
        conversation_style=conversation_style,
        initial_question=get_initial_question(input_mode, conversation_style),
        initial_buttons=get_button_options(input_mode, conversation_style),
    )
