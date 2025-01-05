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
import re 



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
    return text.translate(str.maketrans('', '', string.punctuation)).lower()

def standardize_name(name):
    return normalize_text(name)

def parse_query(query):
    query = query.lower()
    # Match patterns like "weekly data 2024 josh allen" or "weekly data josh allen 2024"
    match = re.search(r'(weekly|season) data (\d{4})? ?(.*)', query)
    if match:
        data_type = match.group(1)
        year = match.group(2)
        player_name = match.group(3).strip()
        if not year:
            # Try to find the year at the end of the player name
            match = re.search(r'(.*) (\d{4})$', player_name)
            if match:
                player_name = match.group(1).strip()
                year = match.group(2)
        return data_type, year, player_name
    return None, None, None

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



def get_weekly_player_data(year, player_name):
    try:
        player_name = standardize_name(player_name)
        # Load the dataset for the specified year
        weekly_data = nfl.import_weekly_data([year])
        weekly_data['player_display_name'] = weekly_data['player_display_name'].apply(standardize_name)
        # Filter for the specific player using the correct column
        player_data = weekly_data[weekly_data["player_display_name"].str.contains(player_name, case=False, na=False)]

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
        title = f"{player_info['player_display_name'].title()} - {player_info['position']} - {player_info['recent_team']}"

        # Convert to a list of dictionaries for JSON response
        response_data = {
            "title": title,
            "data": filtered_data.to_dict(orient="records"),
        }
        #logging.info(f"Final JSON response for '{player_name}': {response_data}")

        return response_data
    except Exception as e:
        logging.error(f"Error fetching weekly data for player: {e}")
        return f"An error occurred while fetching data for '{player_name}' in {year}."



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

# Fetch seasonal data
def get_seasonal_data(player_name, years, s_type="REG"):
    try:
        player_name = standardize_name(player_name)
        # Connect to the playerIds.db database
        conn = sqlite3.connect('playerIds.db')
        cursor = conn.cursor()

        # Fetch the gsis_id, name, and position for the given player name
        cursor.execute("SELECT gsis_id, name, position FROM Player_Ids WHERE REPLACE(LOWER(name), '.', '') = ?", (player_name,))
        result = cursor.fetchone()
        conn.close()

        if result is None:
            return {"title": f"No player found with name '{player_name}'.", "data": []}

        player_id, player_name, position = result

        # Fetch the seasonal data using the player_id
        seasonal_data = nfl.import_seasonal_data(years, s_type)
        player_data = seasonal_data[seasonal_data['player_id'] == player_id]

        if player_data.empty:
            return {"title": f"No seasonal data found for player '{player_name}' in {years}.", "data": []}

        # Define the columns to display
        columns_to_display = [
            'completions', 'attempts', 'passing_yards', 'passing_tds', 'interceptions', 'sacks', 'sack_yards',
            'sack_fumbles', 'sack_fumbles_lost', 'passing_air_yards', 'passing_yards_after_catch', 'passing_first_downs',
            'passing_epa', 'passing_2pt_conversions', 'pacr', 'dakota', 'carries', 'rushing_yards', 'rushing_tds',
            'rushing_fumbles', 'rushing_fumbles_lost', 'rushing_first_downs', 'rushing_epa', 'rushing_2pt_conversions',
            'receptions', 'targets', 'receiving_yards', 'receiving_tds', 'receiving_fumbles', 'receiving_fumbles_lost',
            'receiving_air_yards', 'receiving_yards_after_catch', 'receiving_first_downs', 'receiving_epa',
            'receiving_2pt_conversions', 'racr', 'target_share', 'air_yards_share', 'wopr_x', 'special_teams_tds',
            'fantasy_points', 'fantasy_points_ppr', 'games', 'tgt_sh', 'ay_sh', 'yac_sh', 'wopr_y', 'ry_sh', 'rtd_sh',
            'rfd_sh', 'rtdfd_sh', 'dom', 'w8dom', 'yptmpa', 'ppr_sh'
        ]

        # Filter relevant columns
        filtered_data = player_data[columns_to_display]

        # Replace NaN with 0 for consistent evaluation
        filtered_data = filtered_data.fillna(0)

        # Format numeric values
        for col in filtered_data.select_dtypes(include=['float', 'int']).columns:
            filtered_data[col] = filtered_data[col].apply(lambda x: f"{x:.2f}".rstrip('0').rstrip('.') if x % 1 else str(int(x)))

        # Drop columns where all values are 0 or empty
        
        filtered_data = filtered_data.loc[:, (filtered_data != '0').any(axis=0)]

        # Extract header/title info
        title = f"{player_name} - {position} - {years[0]}"

        # Convert to a list of dictionaries for JSON response
        response_data = {
            "title": title,
            "data": filtered_data.to_dict(orient="records"),
        }
        logging.info(f"Final JSON response for '{player_name}': {response_data}")

        return response_data
    except Exception as e:
        logging.error(f"Error fetching seasonal data for player: {e}")
        return {"title": f"An error occurred while fetching data for '{player_name}' in {years}.", "data": []}



@app.route("/")
def home():
    return "Welcome to the NFL AI Chatbot API!", 200

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()

    logging.info(f"Received question: {question}")

    # Check if there's an ongoing query context
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
                query_type = context["type"]
                query_context.pop("current_query")  # Clear context after completion

                if query_type == "weekly data":
                    return jsonify({"reply": get_weekly_player_data(year, player_name)})
                elif query_type == "season data":
                    return jsonify({"reply": get_seasonal_data(player_name, [year])})
            else:
                return jsonify({"reply": "Please provide a valid year."})

    # Check cache
    cached_answer = search_cache(question)
    if cached_answer:
        logging.info("Answer found in cache.")
        return jsonify({"reply": cached_answer})

    # Handle QB stats query
    if "qb stats" in question.lower():
        player_name = question.split("qb stats")[-1].strip()
        logging.info(f"Fetching player stats for: {player_name}")
        stats = get_player_stats(player_name)
        if isinstance(stats, dict):  # Ensure stats are properly formatted
            logging.info("Player stats successfully fetched.")
            return jsonify({"reply": stats})
        logging.warning("Player stats returned an error or no data.")
        return jsonify({"reply": stats})  # For error messages or fallback strings

    # Handle weekly data query
    if "weekly data" in question.lower():
        data_type, year, player_name = parse_query(question)
        if player_name and year:
            return jsonify({"reply": get_weekly_player_data(int(year), player_name)})
        elif player_name:
            query_context["current_query"] = {"type": "weekly data", "player_name": player_name}
            logging.info("Prompting for year.")
            return jsonify({"reply": "Got it! Now specify the year."})
        else:
            query_context["current_query"] = {"type": "weekly data"}
            logging.info("Prompting for player name.")
            return jsonify({"reply": "Please specify the player name."})

    # Handle season data query
    if "season data" in question.lower():
        data_type, year, player_name = parse_query(question)
        if player_name and year:
            return jsonify({"reply": get_seasonal_data(player_name, [int(year)])})
        elif player_name:
            query_context["current_query"] = {"type": "season data", "player_name": player_name}
            logging.info("Prompting for year.")
            return jsonify({"reply": "Got it! Now specify the year."})
        else:
            query_context["current_query"] = {"type": "season data"}
            logging.info("Prompting for player name.")
            return jsonify({"reply": "Who would you like season data for?"})

    # Handle play-by-play query
    if "play-by-play" in question.lower():
        query_context["current_query"] = "play_by_play"
        logging.info("Prompting for play-by-play years.")
        return jsonify({"reply": "For play-by-play data, specify years like '2010-2020'."})

    # Fallback response if no answer is found
    logging.warning("No suitable response found; returning fallback.")
    fallback_message = "I couldn't find an answer to that question. Try rephrasing it!"
    save_to_cache(question, fallback_message)
    return jsonify({"reply": fallback_message})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
