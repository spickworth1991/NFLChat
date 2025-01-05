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
    //fetch('http://127.0.0.1:5000/chat', {
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
        //console.log(data.reply); // Log the response for debugging
        if (data.reply) {
          if (typeof data.reply === 'object' && data.reply.title && data.reply.data) {
            // Handle response with title and data
            const tableHTML = handleResponse(data.reply);
            addMessage(tableHTML, 'bot', true);
          } else if (Array.isArray(data.reply)) {
            // Handle response as an array
            const tableHTML = handleResponse(data.reply);
            addMessage(tableHTML, 'bot', true);
          } else if (data.reply.includes("\n")) {
            // Multiline string
            const preformattedMessage = `<pre>${data.reply}</pre>`;
            addMessage(preformattedMessage, 'bot', true);
          } else {
            // Single-line string
            addMessage(data.reply, 'bot');
          }
        }
      })
      .catch((error) => {
        searchingMessage.remove();
        console.error('Error fetching data:', error);
        addMessage('Sorry, there was an error fetching the data.', 'bot');
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
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function generateTableHTML(data, title, columnOrder = null) {
    if (!data || data.length === 0) return '<p>No data available.</p>';
  
    // Mapping column names to user-friendly display names
    const columnHeaderMap = {
      week: "Week",
      opponent_team: "Opp.",
      fantasy_points: "Ftsy Pts",
      fantasy_points_ppr: "PPR Pts",
      completions: "Compl.",
      attempts: "Attempts",
      passing_yards: "Pass Yds",
      passing_tds: "Pass TDs",
      interceptions: "Int.",
      carries: "Carries",
      rushing_yards: "Rush Yds",
      rushing_tds: "Rush TDs",
      receptions: "Receptions",
      targets: "Targets",
      receiving_yards: "Rec. Yds",
      receiving_tds: "Rec. TDs",
      receiving_fumbles: "Rec. Fum.",
      receiving_fumbles_lost:  "R Fum. Lost",
      receiving_air_yards: "Rec. Air Yds",
      receiving_yards_after_catch: "Rec. YAC",
      receiving_first_downs: "Rec. 1st Downs",
      receiving_epa: "Rec. EPA",
      receiving_2pt_conversions: "Rec. 2pt Conv.",
      target_share: "Tgt. Share",
      air_yards_share: "Air Yds Share",
      special_teams_tds: "ST TDs",

  
      // Add more mappings as needed for your column names
    };
  
    const container = document.createElement('div');
    const tableContainer = document.createElement('div');
    tableContainer.classList.add('response-table-container');
  
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    container.appendChild(titleElement);
  
    const columns = Object.keys(data[0]);
    let desiredOrder = columnOrder ? columnOrder.filter(col => columns.includes(col)) : columns;
    desiredOrder = [...desiredOrder, ...columns.filter(key => !desiredOrder.includes(key))];
  
    const table = document.createElement('table');
    table.classList.add('response-table');
  
    const headerRow = document.createElement('tr');
    desiredOrder.forEach((key) => {
      const th = document.createElement('th');
      th.textContent = columnHeaderMap[key] || key.replace(/_/g, ' '); // Use mapped name or fallback to formatted key
      headerRow.appendChild(th);
    });
    table.appendChild(headerRow);
  
    data.forEach((row) => {
      const tableRow = document.createElement('tr');
      desiredOrder.forEach((key) => {
        const td = document.createElement('td');
        td.textContent = row[key];
        tableRow.appendChild(td);
      });
      table.appendChild(tableRow);
    });
  
    tableContainer.appendChild(table);
    container.appendChild(tableContainer);
  
    return container.innerHTML;
  }
  
  
  // Example usage for weekly data
  const weeklyColumnOrder = [
    "week",
    "opponent_team",
    "fantasy_points",
    "fantasy_points_ppr",
    // Add other columns as needed
  ];
  
  // Example usage for seasonal data
  const seasonalColumnOrder = [
    "completions", "attempts", "passing_yards", "passing_tds", "interceptions", "sacks", "sack_yards",
    "sack_fumbles", "sack_fumbles_lost", "passing_air_yards", "passing_yards_after_catch", "passing_first_downs",
    "passing_epa", "passing_2pt_conversions", "pacr", "dakota", "carries", "rushing_yards", "rushing_tds",
    "rushing_fumbles", "rushing_fumbles_lost", "rushing_first_downs", "rushing_epa", "rushing_2pt_conversions",
    "receptions", "targets", "receiving_yards", "receiving_tds", "receiving_fumbles", "receiving_fumbles_lost",
    "receiving_air_yards", "receiving_yards_after_catch", "receiving_first_downs", "receiving_epa",
    "receiving_2pt_conversions", "racr", "target_share", "air_yards_share", "wopr_x", "special_teams_tds",
    "fantasy_points", "fantasy_points_ppr", "games", "tgt_sh", "ay_sh", "yac_sh", "wopr_y", "ry_sh", "rtd_sh",
    "rfd_sh", "rtdfd_sh", "dom", "w8dom", "yptmpa", "ppr_sh",
    // Add other columns as needed
  ];
  
  // Function to generate weekly data table
  function generateWeeklyTable(data, title) {
    return generateTableHTML(data, title, weeklyColumnOrder);
  }
  
  // Function to generate seasonal data table
  function generateSeasonalTable(data, title) {
    return generateTableHTML(data, title, seasonalColumnOrder);
  }
  
// Function to handle the response and generate the appropriate table
function handleResponse(response) {
  //console.log('Response:', response); // Log the response for debugging

  let title;
  let data;

  // Normalize the response structure
  if (response && response.title && response.data) {
    title = response.title;
    data = response.data;
  } else if (Array.isArray(response)) {
    data = response;
    title = "Data"; // Default title for array response
  } else {
    return '<p>No data available.</p>';
  }

  // Check if data is defined and is an array
  if (Array.isArray(data)) {
    if (data.length === 0) {
      // Handle case where data is empty but title is provided
      return `<p>${title}</p>`;
    }

    const columns = Object.keys(data[0]);
    if (columns.includes("week") && columns.includes("opponent_team")) {
      // Weekly data
      return generateWeeklyTable(data, title);
    } else {
      // Seasonal data
      return generateSeasonalTable(data, title);
    }
  }

  return '<p>No data available.</p>';
}
  
});
