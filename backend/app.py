from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import logging
import string
import pandas as pd
import nfl_data_py as nfl

app = Flask(__name__)
CORS(app, resources={r"/https://nfl-chat-bot.vercel.app": {"origins": "*"}})

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize the database
def init_db():
    conn = sqlite3.connect("nfl_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            question TEXT PRIMARY KEY,
            answer TEXT
        )
    """)
    conn.commit()
    conn.close()

# Normalize text by removing punctuation and converting to lowercase
def normalize_text(text):
    return text.lower().translate(str.maketrans('', '', string.punctuation))

# Search the database for cached answers with fuzzy matching
def search_cache(question):
    conn = sqlite3.connect("nfl_cache.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM cache")
    results = cursor.fetchall()
    conn.close()

    normalized_question = normalize_text(question)
    matches = []
    for cached_question, cached_answer in results:
        similarity = SequenceMatcher(None, normalized_question, normalize_text(cached_question)).ratio()
        if similarity > 0.8:  # Consider matches with similarity > 80%
            matches.append((similarity, cached_answer))

    matches.sort(reverse=True, key=lambda x: x[0])
    return matches[0][1] if matches else None

# Save a new question-answer pair to the database
def save_to_cache(question, answer):
    conn = sqlite3.connect("nfl_cache.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO cache (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()

# Fetch player stats using nfl-data-py
def get_player_stats(player_name):
    try:
        player_stats = nfl.import_player_stats(season=2023, stat_type="passing")  # Example for passing stats
        player = player_stats[player_stats["player_name"].str.contains(player_name, case=False, na=False)]
        if not player.empty:
            return player.iloc[0].to_dict()
        return "Player stats not found."
    except Exception as e:
        logging.error(f"Error fetching player stats: {e}")
        return "Error accessing NFL player stats."

# Fetch team stats using nfl-data-py
def get_team_stats(team_name):
    try:
        team_stats = nfl.import_team_desc()  # Fetch team descriptions
        team = team_stats[team_stats["team_name"].str.contains(team_name, case=False, na=False)]
        if not team.empty:
            return team.iloc[0].to_dict()
        return "Team stats not found."
    except Exception as e:
        logging.error(f"Error fetching team stats: {e}")
        return "Error accessing NFL team stats."

# Web scraping function as a fallback
def scrape_websites(question):
    websites = [
        "https://www.nfl.com/news/",
        "https://www.espn.com/nfl/",
        "https://www.profootballnetwork.com/",
    ]
    potential_answers = []
    key_terms = set(question.lower().split())

    for website in websites:
        try:
            response = requests.get(website, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")

            for paragraph in paragraphs:
                paragraph_text = paragraph.text.lower()
                overlap = len(key_terms & set(paragraph_text.split()))
                if overlap >= 3:  # At least 3 words must overlap
                    potential_answers.append(paragraph.text)
        except Exception as e:
            logging.error(f"Error scraping {website}: {e}")

    return potential_answers[:3]  # Return up to 3 potential answers

@app.route("/")
def home():
    return "Welcome to the NFL AI Chatbot API!", 200

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()

    # Step 1: Check cache
    cached_answer = search_cache(question)
    if cached_answer:
        return jsonify({"reply": cached_answer})

    # Step 2: Fetch data via nfl-data-py
    if "team stats" in question.lower():
        team_name = question.split("team stats")[-1].strip()
        return jsonify({"reply": get_team_stats(team_name)})
    if "player stats" in question.lower():
        player_name = question.split("player stats")[-1].strip()
        return jsonify({"reply": get_player_stats(player_name)})

    # Step 3: Web scrape if not in cache or nfl-data-py
    scraped_answers = scrape_websites(question)
    if scraped_answers:
        formatted_answers = "\n".join([f"- {answer}" for answer in scraped_answers])
        return jsonify({"reply": f"I found some information on this topic:\n{formatted_answers}"})

    # Fallback response if no answer is found
    fallback_message = "I couldn't find an answer to that question. Try rephrasing it!"
    save_to_cache(question, fallback_message)
    return jsonify({"reply": fallback_message})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
