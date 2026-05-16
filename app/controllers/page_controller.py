from flask import Blueprint, redirect, render_template, request, url_for

from app.services.button_flow import get_button_options, get_initial_question


page_bp = Blueprint("pages", __name__)

CONDITIONS = {
    "A": {"input_mode": "button", "conversation_style": "task"},
    "B": {"input_mode": "button", "conversation_style": "topic"},
    "C": {"input_mode": "text", "conversation_style": "task"},
    "D": {"input_mode": "text", "conversation_style": "topic"},
}


@page_bp.get("/")
def index():
    return render_template("condition_select.html", conditions=CONDITIONS.keys())


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
