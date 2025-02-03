
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
import openai
import logging
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Needed for session handling

openai.api_key = os.getenv("OPENAI_API_KEY")  # OpenAI API Key

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize the database
def init_db():
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            personality TEXT
        )
    """)
    conn.commit()
    conn.close()

# Save user details in the database
def save_user_data(user_id, name=None, personality=None):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, name, personality) VALUES (?, ?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, personality=excluded.personality
    """, (user_id, name, personality))
    conn.commit()
    conn.close()

# Retrieve user details
def get_user_data(user_id):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, personality FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None)

# Chat route using OpenAI
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_id = data.get("user_id", "unknown")
    message = data.get("message", "").strip()

    # Retrieve user-specific data
    name, personality = get_user_data(user_id)

    # Check session-based cache
    if "chat_history" not in session:
        session["chat_history"] = []

    chat_history = session["chat_history"]

    # Construct prompt with user context
    user_prompt = f"User: {message}\n"
    if name:
        user_prompt = f"{name}: {message}\n"
    if personality:
        user_prompt = f"{name} ({personality}): {message}\n"

    # Add context from session cache
    for chat in chat_history[-5:]:  # Keep last 5 interactions
        user_prompt = chat + "\n" + user_prompt

    # Call OpenAI API
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": user_prompt}]
        )
        reply = response["choices"][0]["message"]["content"].strip()

        # Update session cache
        chat_history.append(f"User: {message}\nAI: {reply}")
        session["chat_history"] = chat_history

        return jsonify({"reply": reply})

    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return jsonify({"reply": "I'm having trouble responding right now. Please try again later."})

# Clear chat session cache when a new chat starts
@app.route("/new_chat", methods=["POST"])
def new_chat():
    session.pop("chat_history", None)
    return jsonify({"message": "New chat session started."})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
