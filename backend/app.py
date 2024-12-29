from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import logging
import string
import pandas as pd
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from rpy2.robjects import default_converter, pandas2ri
from rpy2.robjects.conversion import localconverter

# Activate pandas2ri conversion
pandas2ri.activate()

# Import nflreadr R package
nflreadr = importr("nflreadr")

app = Flask(__name__)
CORS(app)

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

def fetch_player_stats():
    try:
        with localconverter(default_converter + pandas2ri.converter):
            player_stats = nflreadr.load_player_stats()  # Fetch data from R
            print(f"Type of player_stats: {type(player_stats)}")  # Debugging
            if isinstance(player_stats, pandas.DataFrame):
                return player_stats  # Return as is if it's already a DataFrame
            player_stats_df = pandas2ri.rpy2py(player_stats)  # Convert to pandas DataFrame
        return player_stats_df
    except Exception as e:
        logging.error(f"Error fetching player stats: {e}")
        return None


# Fetch team stats using nflreadr
def fetch_team_stats():
    try:
        with localconverter(default_converter + pandas2ri.converter):
            team_stats = nflreadr.load_team_stats()  # Fetch data from R
            team_stats_df = pandas2ri.rpy2py(team_stats)  # Convert to pandas DataFrame
        return team_stats_df
    except Exception as e:
        logging.error(f"Error fetching team stats: {e}")
        return None

def get_team_stats(team_name):
    team_stats = fetch_team_stats()
    if team_stats is None:
        return "Error accessing NFL team stats."

    team = team_stats[team_stats["team"].str.contains(team_name, case=False, na=False)]
    if not team.empty:
        return team.iloc[0].to_dict()
    return "Team stats not found."

def get_player_stats(player_name):
    player_stats = fetch_player_stats()
    if player_stats is None:
        return "Error accessing NFL player stats."

    player = player_stats[player_stats["player"].str.contains(player_name, case=False, na=False)]
    if not player.empty:
        return player.iloc[0].to_dict()
    return "Player stats not found."

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

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()

    # Step 1: Check cache
    cached_answer = search_cache(question)
    if cached_answer:
        return jsonify({"reply": cached_answer})

    # Step 2: Fetch data via nflreadr
    if "team stats" in question.lower():
        nflreadr.clear_cache()
        team_name = question.split("team stats")[-1].strip()
        return jsonify({"reply": get_team_stats(team_name)})
    if "player stats" in question.lower():
        nflreadr.clear_cache()
        player_name = question.split("player stats")[-1].strip()
        return jsonify({"reply": get_player_stats(player_name)})

    # Step 3: Web scrape if not in cache or nflverse
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
