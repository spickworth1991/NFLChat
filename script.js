const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const messages = document.getElementById("messages");

sendBtn.addEventListener("click", () => sendMessage());

userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

function sendMessage() {
  const userMessage = userInput.value.trim();
  if (!userMessage) return;

  // Display user message
  addMessage(userMessage, "user");
  userInput.value = "";

  // Show "searching" message while waiting for the bot's response
  const searchingMessage = addMessage("Searching for an answer...", "bot");

  // Call the backend API
  fetch("https://nfl-chat-bot.onrender.com", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userMessage }),
  })
    .then((response) => response.json())
    .then((data) => {
      searchingMessage.remove(); // Remove the "searching" message
      addMessage(data.reply, "bot");
    })
    .catch(() => {
      searchingMessage.remove();
      addMessage("Sorry, I couldn't process your request. Try again later.", "bot");
    });
}

function addMessage(text, sender) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", sender);
  messageDiv.textContent = text;
  messages.appendChild(messageDiv);
  messages.scrollTop = messages.scrollHeight;
}