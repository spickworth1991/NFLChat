document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('send-btn');
  const userInput = document.getElementById('user-input');
  const messages = document.getElementById('messages');

  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }

  if (userInput) {
    userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  function sendMessage() {
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    addMessage(userMessage, 'user');
    userInput.value = '';

    const searchingMessage = addMessage('Searching for an answer...', 'bot');

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
        searchingMessage.remove();
        console.log(data.reply); // Log the response to debug
        if (data.reply) {
          if (Array.isArray(data.reply)) {
            // Handle array of objects
            const tableHTML = generateTableHTML(data.reply);
            addMessage(tableHTML, 'bot', true);
          } else if (data.reply.includes("\n")) {
            // Multiline string
            const preformattedMessage = `<pre>${data.reply}</pre>`;
            addMessage(preformattedMessage, 'bot', true);
          } else {
            // Single-line string
            addMessage(data.reply, 'bot');
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
      messageDiv.innerHTML = text;
    } else {
      messageDiv.textContent = text;
    }
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
    return messageDiv;
  }

  function generateTableHTML(data) {
    if (!data || data.length === 0) return '<p>No data available.</p>';
    const table = document.createElement('table');
    table.classList.add('response-table');

    // Create table header
    const headerRow = document.createElement('tr');
    Object.keys(data[0] || {}).forEach((key) => {
        const th = document.createElement('th');
        th.textContent = key;
        headerRow.appendChild(th);
    });
    table.appendChild(headerRow);

    // Create table rows
    data.forEach((row) => {
        const tableRow = document.createElement('tr');
        Object.values(row).forEach((value) => {
            const td = document.createElement('td');
            td.textContent = value === null || value === undefined ? 'N/A' : value;
            tableRow.appendChild(td);
        });
        table.appendChild(tableRow);
    });

    return table.outerHTML;
}

});
