from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import sqlite3
import logging

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

# Search the database for cached answers
def search_cache(question):
    conn = sqlite3.connect("nfl_cache.db")
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM cache WHERE question = ?", (question,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Save a new question-answer pair to the database
def save_to_cache(question, answer):
    conn = sqlite3.connect("nfl_cache.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO cache (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()

# Web scraping function
def scrape_websites(question):
    websites = [
        "https://www.nfl.com/news/",
        "https://www.espn.com/nfl/",
        "https://www.profootballnetwork.com/",
    ]
    for website in websites:
        try:
            response = requests.get(website, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            for paragraph in paragraphs:
                if question.lower() in paragraph.text.lower():
                    return paragraph.text
        except Exception as e:
            logging.error(f"Error scraping {website}: {e}")
    return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()

    # Check cache first
    cached_answer = search_cache(question)
    if cached_answer:
        return jsonify({"reply": cached_answer})

    # Scrape websites if not in cache
    scraped_answer = scrape_websites(question)
    if scraped_answer:
        save_to_cache(question, scraped_answer)
        return jsonify({"reply": scraped_answer})

    # Fallback response if no answer is found
    fallback_message = "I couldn't find an answer to that question. Try rephrasing it!"
    save_to_cache(question, fallback_message)
    return jsonify({"reply": fallback_message})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
