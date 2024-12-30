document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('send-btn');
  const userInput = document.getElementById('user-input');
  const messages = document.getElementById('messages');

  // Attach click event listener to the button
  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }

  // Attach keypress event listener to allow pressing Enter to send a message
  if (userInput) {
    userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  function sendMessage() {
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    // Display user message
    addMessage(userMessage, 'user');
    userInput.value = '';

    // Show "searching" message while waiting for the bot's response
    const searchingMessage = addMessage('Searching for an answer...', 'bot');

    // Call the backend API
    fetch('http://127.0.0.1:5000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then((data) => {
            searchingMessage.remove(); // Remove the "searching" message
            if (data.reply) {
                if (data.reply.includes("\n")) {
                    // Wrap multi-line replies in a <pre> tag for better readability
                    const preformattedMessage = `<pre>${data.reply}</pre>`;
                    addMessage(preformattedMessage, 'bot', true); // Pass as HTML
                } else {
                    addMessage(data.reply, 'bot'); // For single-line responses
                }
            } else {
                addMessage("I couldn't find an answer. Please try again.", 'bot');
            }
        })
        .catch((error) => {
            searchingMessage.remove();
            console.error("Error in sendMessage:", error);
            addMessage("Sorry, I couldn't process your request. Try again later.", 'bot');
        });
}



function addMessage(text, sender, isHTML = false) {
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', sender);
  if (isHTML) {
      messageDiv.innerHTML = text; // Safely insert HTML content
  } else {
      messageDiv.textContent = text; // Insert plain text
  }
  messages.appendChild(messageDiv);
  messages.scrollTop = messages.scrollHeight;
  return messageDiv; // Ensure the created messageDiv is returned
}

  
});
