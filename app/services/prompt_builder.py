def build_system_prompt(conversation_style):
    if conversation_style == "task":
        return (
            "You are a task-led salon booking assistant. Guide the participant "
            "step by step toward choosing a treatment, time, and booking details."
        )

    return (
        "You are a topic-led salon consultation assistant. Discuss hair care "
        "topics first, then help the participant connect their needs to a booking."
    )
