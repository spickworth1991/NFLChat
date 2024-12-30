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
import json



app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

query_context = {}

# Set up logging
logging.basicConfig(level=logging.INFO)

def sanitize_json(data):
    return json.loads(json.dumps(data, default=lambda x: None))

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

# Fetch play-by-play data
def get_play_by_play(years, columns=None):
    try:
        pbp_data = nfl.import_pbp_data(years, columns)
        return pbp_data.head(10).to_dict(orient="records")  # Limit to first 10 rows for display
    except Exception as e:
        logging.error(f"Error fetching play-by-play data: {e}")
        return "Error accessing play-by-play data."

def get_weekly_player_data(year, player_name):
    try:
        # Load the dataset for the specified year
        weekly_data = nfl.import_weekly_data([year])
        logging.info(f"Dataset loaded for year {year}: {weekly_data.head()}")

        # Filter for the specific player using the correct column
        player_data = weekly_data[weekly_data["player_display_name"].str.contains(player_name, case=False, na=False)]
        logging.info(f"Player data found for '{player_name}': {player_data.head()}")

        if player_data.empty:
            return f"No data found for player '{player_name}' in {year}. Please check the player name and try again."

        # Columns for title 
        title_columns = ["player_display_name", "position", "recent_team"]

        # Columns to display
        columns_to_display = [
            "week", "opponent_team",
            "completions", "attempts", "passing_yards", "passing_tds", "interceptions", "sacks",
            "sack_yards", "sack_fumbles", "sack_fumbles_lost", "passing_air_yards",
            "passing_yards_after_catch", "passing_first_downs", "passing_epa", "passing_2pt_conversions",
            "pacr", "dakota", "carries", "rushing_yards", "rushing_tds", "rushing_fumbles",
            "rushing_fumbles_lost", "rushing_first_downs", "rushing_epa", "rushing_2pt_conversions",
            "receptions", "targets", "receiving_yards", "receiving_tds", "receiving_fumbles",
            "receiving_fumbles_lost", "receiving_air_yards", "receiving_yards_after_catch",
            "receiving_first_downs", "receiving_epa", "receiving_2pt_conversions", "racr",
            "target_share", "air_yards_share", "wopr", "special_teams_tds", "fantasy_points",
            "fantasy_points_ppr"
        ]

        # Filter relevant columns
        filtered_data = player_data[columns_to_display]

        # Replace NaN with 0 for consistent evaluation
        filtered_data = filtered_data.fillna(0)

        # Format numeric values
        for col in filtered_data.select_dtypes(include=['float', 'int']).columns:
            filtered_data[col] = filtered_data[col].apply(lambda x: f"{x:.2f}".rstrip('0').rstrip('.') if x % 1 else str(int(x)))

        # Drop columns where all values are 0
        filtered_data = filtered_data.loc[:, (filtered_data != '0').any(axis=0)]

        # Rearrange columns: fixed columns first, then the rest
        fixed_columns = ["week", "opponent_team", "fantasy_points", "fantasy_points_ppr"]
        other_columns = [col for col in filtered_data.columns if col not in fixed_columns]
        ordered_columns = fixed_columns + other_columns
        filtered_data = filtered_data[ordered_columns]

        # Extract header/title info
        filtered_data2 = player_data[title_columns].drop_duplicates()
        player_info = filtered_data2.iloc[0]
        title = f"{player_info['player_display_name']} - {player_info['position']} - {player_info['recent_team']}"

        # Convert to a list of dictionaries for JSON response
        response_data = {
            "title": title,
            "data": filtered_data.to_dict(orient="records"),
        }
        logging.info(f"Final JSON response for '{player_name}': {response_data}")

        return response_data
    except Exception as e:
        logging.error(f"Error fetching weekly data for player: {e}")
        return f"An error occurred while fetching data for '{player_name}' in {year}."




# Fetch seasonal data
def get_seasonal_data(years, s_type="REG"):
    try:
        seasonal_data = nfl.import_seasonal_data(years, s_type)
        return seasonal_data.head(10).to_dict(orient="records")  # Limit to first 10 rows for display
    except Exception as e:
        logging.error(f"Error fetching seasonal data: {e}")
        return "Error accessing seasonal data."


# Fetch player stats using nfl-data-py
def get_player_stats(player_name):
    try:
        player_stats = nfl.import_seasonal_pfr("pass", [2023])  # Fetch all available stats
        player = player_stats[player_stats["player"].str.contains(player_name, case=False, na=False)]
        if player.empty:
            return f"No stats found for player '{player_name}'."

        stats = player.iloc[0].to_dict()
        filtered_stats = {key: value for key, value in stats.items() if pd.notnull(value)}

        # Format stats into a multi-line string
        formatted_stats = "\n".join([f"{key}: {value}" for key, value in filtered_stats.items()])
        return formatted_stats
    except Exception as e:
        logging.error(f"Error fetching player stats: {e}")
        return f"An error occurred while fetching stats for '{player_name}'."



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

    logging.info(f"Received question: {question}")
    if "current_query" in query_context:
        context = query_context.get("current_query", {})  # Ensure context is safely retrieved

        # Handle missing player name
        if "player_name" not in context:
            query_context["current_query"]["player_name"] = question
            return jsonify({"reply": "Got it! Now specify the year."})

        # Handle missing year
        if "year" not in context:
            if question.isdigit():
                query_context["current_query"]["year"] = int(question)
                player_name = context["player_name"]
                year = context["year"]
                query_context.pop("current_query")  # Clear context after completion
                return jsonify({"reply": get_weekly_player_data(year, player_name)})
            else:
                return jsonify({"reply": "Please provide a valid year."})


    # Check if the question matches an ongoing query context
    if question.isdigit() and "current_query" in query_context:
        years = [int(question)]
        current_query = query_context.pop("current_query")

        if current_query == "play_by_play":
            logging.info(f"Fetching play-by-play data for years: {years}")
            return jsonify({"reply": get_play_by_play(years)})
        
        if current_query == "seasonal data":
            logging.info(f"Fetching seasonal data for years: {years}")
            return jsonify({"reply": get_seasonal_data(years)})

    # Step 1: Check cache
    cached_answer = search_cache(question)
    if cached_answer:
        logging.info("Answer found in cache.")
        return jsonify({"reply": cached_answer})

    # Step 2: Fetch data via nfl-data-py
    if "team stats" in question.lower():
        team_name = question.split("team stats")[-1].strip()
        logging.info(f"Fetching team stats for: {team_name}")
        return jsonify({"reply": get_team_stats(team_name)})

    if "player stats" in question.lower():
        player_name = question.split("player stats")[-1].strip()
        logging.info(f"Fetching player stats for: {player_name}")
        stats = get_player_stats(player_name)
        if isinstance(stats, dict):  # Ensure stats are properly formatted
            logging.info("Player stats successfully fetched.")
            return jsonify({"reply": stats})
        logging.warning("Player stats returned an error or no data.")
        return jsonify({"reply": stats})  # For error messages or fallback strings

    # Handle play-by-play data query
    # Handle specific queries
    if "weekly data" in question.lower():
        query_context["current_query"] = {"type": "weekly_data"}
        logging.info("Prompting for player name.")
        return jsonify({"reply": "Please specify the player name."})
    if "play-by-play" in question.lower():
        query_context["current_query"] = "play_by_play"
        logging.info("Prompting for play-by-play years.")
        return jsonify({"reply": "For play-by-play data, specify years like '2010-2020'."})
    
    # Handle seasonal data query
    if "seasonal data" in question.lower():
        query_context["current_query"] = "seasonal data"
        logging.info("Prompting for seasonal data years.")
        return jsonify({"reply": "For seasonal data, specify years like '2020-2023'."})

    # Parse year ranges dynamically
    if any(keyword in question.lower() for keyword in ["years", "season", "data"]):
        try:
            years = list(map(int, question.split(" ")[-1].split("-")))
            logging.info(f"Fetching play-by-play data for years: {years}")
            return jsonify({"reply": get_play_by_play(years)})
        except Exception as e:
            logging.error(f"Error parsing years: {e}")
            return jsonify({"reply": "Invalid year format. Provide years like '2010-2020'."})

    # Step 3: Web scrape if not in cache or nfl-data-py
    scraped_answers = scrape_websites(question)
    if scraped_answers:
        logging.info(f"Web scraping returned answers: {scraped_answers}")
        formatted_answers = "\n".join([f"- {answer}" for answer in scraped_answers])
        return jsonify({"reply": f"I found some information on this topic:\n{formatted_answers}"})

    # Fallback response if no answer is found
    logging.warning("No suitable response found; returning fallback.")
    fallback_message = "I couldn't find an answer to that question. Try rephrasing it!"
    save_to_cache(question, fallback_message)
    return jsonify({"reply": fallback_message})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
