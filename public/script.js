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

    fetch('https://nfl-chat-bot.onrender.com/chat', {
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
        console.log(data.reply); // Log the response for debugging
        if (data.reply) {
          if (typeof data.reply === 'object' && data.reply.title && data.reply.data) {
            // Handle response with title and data
            const tableHTML = generateTableHTML(data.reply.data, data.reply.title);
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

    // Ensure the chat window scrolls to the bottom
    setTimeout(() => scrollToBottom(), 0);

    return messageDiv;
  }

  function scrollToBottom() {
    messages.scrollTo({
      top: messages.scrollHeight,
      behavior: 'smooth',
    });
  }

  function generateTableHTML(data, title) {
    if (!data || data.length === 0) return '<p>No data available.</p>';
  
    // Create the container for the table and title
    const container = document.createElement('div');
  
    // Add the title
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    container.appendChild(titleElement);
  
    // Desired column order
    const desiredOrder = [
      "week",
      "opponent_team",
      "fantasy_points",
      "fantasy_points_ppr",
      ...Object.keys(data[0]).filter(
        (key) => !["week", "opponent_team", "fantasy_points", "fantasy_points_ppr"].includes(key)
      ),
    ];
  
    // Create the table
    const table = document.createElement('table');
    table.classList.add('response-table');
  
    // Create table header
    const headerRow = document.createElement('tr');
    desiredOrder.forEach((key) => {
      const th = document.createElement('th');
      th.textContent = key.replace(/_/g, ' '); // Replace underscores with spaces for readability
      headerRow.appendChild(th);
    });
    table.appendChild(headerRow);
  
    // Create table rows
    data.forEach((row) => {
      const tableRow = document.createElement('tr');
      desiredOrder.forEach((key) => {
        const td = document.createElement('td');
        let value = row[key];
  
        // Format numbers: maximum 2 decimal places, no trailing zeros
        if (!isNaN(value) && typeof value === 'number') {
          value = value % 1 ? parseFloat(value).toFixed(2).replace(/\.?0+$/, '') : parseInt(value, 10);
        }
  
        td.textContent = value === null || value === undefined ? 'N/A' : value;
        tableRow.appendChild(td);
      });
      table.appendChild(tableRow);
    });
  
    container.appendChild(table);
    return container.outerHTML;
  }
});
