(function () {
  const shell = document.querySelector(".app-shell");
  if (!shell) {
    return;
  }

  const inputMode = shell.dataset.inputMode;
  const conversationStyle = shell.dataset.conversationStyle;
  const messagesEl = document.querySelector("#chat-messages");
  const buttonOptionsEl = document.querySelector("#button-options");
  const formEl = document.querySelector("#chat-form");
  const inputEl = document.querySelector("#chat-input");
  const recommendationCardEl = document.querySelector("#recommendation-card");
  const recommendedServiceEl = document.querySelector("#recommended-service");
  const recommendationReasonEl = document.querySelector("#recommendation-reason");
  const recommendationNextStepEl = document.querySelector("#recommendation-next-step");
  const resetConsultationEl = document.querySelector("#reset-consultation");
  const completionCardEl = document.querySelector("#completion-card");
  const completedServiceEl = document.querySelector("#completed-service");
  const initialGreeting = shell.dataset.initialGreeting;
  const maxButtonOptions = 3;
  const initialButtonLabels = buttonOptionsEl
    ? Array.from(buttonOptionsEl.querySelectorAll("[data-message]"))
        .map((button) => button.dataset.message)
        .slice(0, maxButtonOptions)
    : [];
  const history = [];

  function appendMessage(role, text) {
    const messageEl = document.createElement("div");
    messageEl.className = `message ${role}`;
    messageEl.textContent = text;
    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderButtons(buttons) {
    if (!buttonOptionsEl) {
      return;
    }

    buttonOptionsEl.innerHTML = "";
    buttons.slice(0, maxButtonOptions).forEach((label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chat-option";
      button.dataset.message = label;
      button.textContent = label;
      buttonOptionsEl.appendChild(button);
    });
  }

  function setInputDisabled(disabled) {
    if (buttonOptionsEl) {
      buttonOptionsEl.hidden = disabled;
    }

    if (formEl) {
      formEl.hidden = disabled;
    }
  }

  function showFinalOutput(finalOutput) {
    if (!recommendationCardEl || !finalOutput) {
      return;
    }

    recommendedServiceEl.textContent = finalOutput.recommended_service;
    recommendationReasonEl.textContent = finalOutput.reason;
    recommendationNextStepEl.textContent = finalOutput.next_step;
    recommendationCardEl.hidden = false;
    completionCardEl.hidden = true;
    setInputDisabled(true);
  }

  function resetConsultation() {
    // TODO: When Hermes integration is added, also clear the backend/Hermes session state here.
    history.length = 0;
    messagesEl.innerHTML = "";
    appendMessage("assistant", initialGreeting);
    recommendationCardEl.hidden = true;
    completionCardEl.hidden = true;
    completedServiceEl.textContent = "";
    renderButtons(initialButtonLabels);
    if (inputEl) {
      inputEl.value = "";
    }
    setInputDisabled(false);
  }

  function completeServiceSelection(serviceName) {
    if (!serviceName) {
      return;
    }

    completedServiceEl.textContent = serviceName;
    recommendationCardEl.hidden = true;
    completionCardEl.hidden = false;
    setInputDisabled(true);
  }

  async function sendMessage(message) {
    appendMessage("user", message);
    history.push({ role: "user", content: message });

    const response = await fetch("/chat/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input_mode: inputMode,
        conversation_style: conversationStyle,
        message,
        history,
      }),
    });

    if (!response.ok) {
      appendMessage("assistant", "目前無法取得回覆，請稍後再試。");
      return;
    }

    const data = await response.json();
    appendMessage("assistant", data.reply);
    history.push({ role: "assistant", content: data.reply });
    renderButtons(data.buttons || []);

    if (data.is_final) {
      showFinalOutput(data.final_output);
    }
  }

  document.addEventListener("click", (event) => {
    const serviceButton = event.target.closest("[data-service-choice]");
    if (serviceButton) {
      completeServiceSelection(serviceButton.dataset.serviceChoice);
      return;
    }

    const button = event.target.closest("[data-message]");
    if (!button) {
      return;
    }

    sendMessage(button.dataset.message);
  });

  if (formEl) {
    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = inputEl.value.trim();
      if (!message) {
        return;
      }

      inputEl.value = "";
      sendMessage(message);
    });
  }

  if (resetConsultationEl) {
    resetConsultationEl.addEventListener("click", resetConsultation);
  }
})();
