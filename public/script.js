document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('send-btn');
  const userInput = document.getElementById('user-input');
  const messages = document.getElementById('messages');
  const newChatBtn = document.getElementById('new-chat-btn'); // Add button for resetting chat

  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }

  if (userInput) {
    userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  if (newChatBtn) {
    newChatBtn.addEventListener('click', resetChat); // Attach event for new chat button
  }

  function sendMessage() {
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    addMessage(userMessage, 'user');
    userInput.value = '';

    const searchingMessage = addMessage('Thinking...', 'bot');

    fetch('https://nfl-chat-bot.onrender.com/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: "some_unique_id",  // Replace this with actual user logic if available
        message: userMessage
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        searchingMessage.remove();
        if (data.reply) {
          addMessage(data.reply, 'bot');
        }
      })
      .catch((error) => {
        searchingMessage.remove();
        console.error('Error fetching data:', error);
        addMessage('Sorry, there was an error processing your request.', 'bot');
      });
  }

  function resetChat() {
    fetch("https://nfl-chat-bot.onrender.com/new_chat", {
      method: "POST",
    })
    .then(() => {
      messages.innerHTML = ''; // Clear chat window
      addMessage("New chat session started.", 'bot');
    })
    .catch((error) => console.error("Error resetting chat:", error));
  }

  function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    messageDiv.textContent = text;
    messages.appendChild(messageDiv);

    setTimeout(() => scrollToBottom(), 0);
    return messageDiv;
  }

  function scrollToBottom() {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
});
