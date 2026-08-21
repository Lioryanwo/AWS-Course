// TODO (Phase 6): replace with the real API Gateway invoke URL, e.g.
// "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/chat"
const API_ENDPOINT =
  "https://vcn6rd2fl8.execute-api.us-east-1.amazonaws.com/prod/chat";
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const errorMessage = document.getElementById("error-message");

// Manually managed conversation state: the full history lives only here,
// in the browser. It is resent in full with every request and is lost on refresh.
const messages = [];

function renderMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function showError(text) {
  errorMessage.textContent = text;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.hidden = true;
  errorMessage.textContent = "";
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  chatInput.disabled = isLoading;
}

// Sends the full conversation history to the backend and resolves with the
// assistant's reply text. Lambda is stateless - it only ever sees what we send here.
async function sendMessageToBackend(history) {
  if (!API_ENDPOINT) {
    // Mock mode: no backend wired up yet (Phase 2/3). Lets us test the UI in isolation.
    await new Promise((resolve) => setTimeout(resolve, 600));
    const lastUserMessage = [...history].reverse().find((m) => m.role === "user");
    return `(mock reply) You said: "${lastUserMessage.content}"`;
  }

  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: history }),
  });

  if (!response.ok) {
    throw new Error(`Backend returned status ${response.status}`);
  }

  const data = await response.json();
  if (!data.reply) {
    throw new Error("Backend response did not include a reply");
  }

  return data.reply;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const text = chatInput.value.trim();
  if (!text) {
    return;
  }

  messages.push({ role: "user", content: text });
  renderMessage("user", text);
  chatInput.value = "";

  setLoading(true);
  const loadingBubble = renderMessage("loading", "Thinking...");

  try {
    const reply = await sendMessageToBackend(messages);
    messages.push({ role: "assistant", content: reply });
    loadingBubble.remove();
    renderMessage("assistant", reply);
  } catch (err) {
    loadingBubble.remove();
    showError("Something went wrong reaching the assistant. Please try again.");
    // The failed exchange is not added to messages, so it is not resent on the next request.
    messages.pop();
  } finally {
    setLoading(false);
    chatInput.focus();
  }
});
