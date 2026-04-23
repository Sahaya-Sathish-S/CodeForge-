from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import requests
import json
import os
import random

app = Flask(__name__, static_folder=".")
app.secret_key = "codeforge_secret_key_2026"

CORS(app)

# SOCKET
socketio = SocketIO(app, cors_allowed_origins="*")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# =====================================
# MULTIPLAYER DATA
# =====================================
waiting_players = []
rooms_data = {}

# =====================================
# HOME
# =====================================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/auth")
def auth_page():
    return send_from_directory(".", "auth.html")


@app.route("/<path:path>")
def files(path):
    return send_from_directory(".", path)


# =====================================
# LOGIN SUCCESS
# =====================================
@app.route("/login_success", methods=["POST"])
def login_success():
    try:
        data = request.get_json(force=True)

        session["user"] = {
            "email": data.get("email", ""),
            "name": data.get("name", "")
        }

        return jsonify({"success": True})

    except:
        return jsonify({"success": False})


# =====================================
# CHECK LOGIN
# =====================================
@app.route("/check_login")
def check_login():
    if "user" in session:
        return jsonify({
            "loggedIn": True,
            "user": session["user"]
        })

    return jsonify({"loggedIn": False})


# =====================================
# LOGOUT
# =====================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/auth")


# =====================================
# CHATBOT
# =====================================
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(force=True)
        msg = data.get("message", "").strip()

        if not msg:
            return jsonify({"reply": "Please type a message."})

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are CodeForge AI. Helpful, smart, professional assistant."
                },
                {
                    "role": "user",
                    "content": msg
                }
            ]
        }

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code != 200:
            return jsonify({"reply": f"API Error: {r.text}"})

        result = r.json()
        reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"})


# =====================================
# QUIZ (OLD API ROUTE KEPT SAME)
# =====================================
@app.route("/quiz", methods=["GET"])
def quiz():
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "temperature": 1.1,
            "messages": [
                {
                    "role": "system",
                    "content": """
Generate a NEW unique quiz every request.

Return ONLY valid JSON array.

Need exactly 5 MCQ questions.

Topics:
Python, Java, C, C++, HTML, CSS, JavaScript, SQL, MongoDB,
AI, Cybersecurity, Communication, Interview Skills.

First 2 easy.
Last 3 medium/hard.

Format:
[
 {"q":"Question","o":["A","B","C","D"],"a":0}
]
"""
                }
            ]
        }

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code != 200:
            raise Exception("API Failed")

        txt = r.json()["choices"][0]["message"]["content"].strip()

        start = txt.find("[")
        end = txt.rfind("]") + 1
        txt = txt[start:end]

        data = json.loads(txt)

        return jsonify(data)

    except:
        return jsonify([
            {"q":"HTML full form?","o":["Hyper Text Markup Language","High Text","Mail","None"],"a":0},
            {"q":"CSS used for?","o":["Style","Virus","Database","Audio"],"a":0},
            {"q":"Python keyword for loop?","o":["loop","for","go","repeat"],"a":1},
            {"q":"SQL used for?","o":["Styling","Database","Video","Drawing"],"a":1},
            {"q":"JS runs mainly in?","o":["Browser","Mouse","RAM","Fan"],"a":0}
        ])


# =====================================
# MULTIPLAYER QUIZ SOCKET
# =====================================
@socketio.on("find_match")
def find_match():
    sid = request.sid

    if sid not in waiting_players:
        waiting_players.append(sid)

    if len(waiting_players) >= 2:
        p1 = waiting_players.pop(0)
        p2 = waiting_players.pop(0)

        room = f"room_{random.randint(1000,9999)}"

        join_room(room, sid=p1)
        join_room(room, sid=p2)

        questions = [
            {"q":"Python keyword for function?","o":["func","define","def","fun"],"a":2},
            {"q":"HTML full form?","o":["Hyper Text Markup Language","Mail","None","High"],"a":0},
            {"q":"CSS used for?","o":["Style","Database","Virus","Audio"],"a":0},
            {"q":"2 + 5 = ?","o":["6","7","8","9"],"a":1},
            {"q":"JavaScript runs in?","o":["Browser","Keyboard","Mouse","RAM"],"a":0}
        ]

        rooms_data[room] = {
            "p1": 0,
            "p2": 0,
            "questions": questions
        }

        emit("match_found", {
            "room": room,
            "player": "p1",
            "questions": questions
        }, to=p1)

        emit("match_found", {
            "room": room,
            "player": "p2",
            "questions": questions
        }, to=p2)


@socketio.on("submit_answer")
def submit_answer(data):
    room = data["room"]
    player = data["player"]
    correct = data["correct"]

    if room not in rooms_data:
        return

    if correct:
        rooms_data[room][player] += 1

    emit("score_update", {
        "p1": rooms_data[room]["p1"],
        "p2": rooms_data[room]["p2"]
    }, room=room)


@socketio.on("finish_game")
def finish_game(data):
    room = data["room"]

    if room not in rooms_data:
        return

    p1 = rooms_data[room]["p1"]
    p2 = rooms_data[room]["p2"]

    winner = "🤝 DRAW"

    if p1 > p2:
        winner = "🏆 PLAYER 1 WINS"
    elif p2 > p1:
        winner = "🏆 PLAYER 2 WINS"

    emit("game_result", {
        "winner": winner,
        "p1": p1,
        "p2": p2
    }, room=room)


# =====================================
# PROGRAMMING GAME START
# =====================================
@app.route("/start_problem", methods=["POST"])
def start_problem():
    try:
        data = request.get_json(force=True)
        language = data.get("language", "Python")

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""
Create ONE easy beginner coding challenge for {language}.

Rules:
- solvable in 1 minute
- practical
- clear
- beginner friendly

Also give bot sample answer.

Return ONLY JSON:

{{
 "problem":"question here",
 "bot_code":"sample code here"
}}
"""

        payload = {
            "model":"openai/gpt-4o-mini",
            "temperature":1.0,
            "messages":[
                {"role":"system","content":prompt}
            ]
        }

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        txt = r.json()["choices"][0]["message"]["content"]

        start = txt.find("{")
        end = txt.rfind("}") + 1
        txt = txt[start:end]

        obj = json.loads(txt)

        return jsonify(obj)

    except:
        return jsonify({
            "problem":"Write code to print Hello World",
            "bot_code":"print('Hello World')"
        })


# =====================================
# PROGRAMMING GAME CHECK
# =====================================
@app.route("/check_battle", methods=["POST"])
def check_battle():
    try:
        data = request.get_json(force=True)

        language = data.get("language", "")
        problem = data.get("problem", "")
        user_code = data.get("user_code", "")
        user_time = int(data.get("user_time", 60))
        bot_time = int(data.get("bot_time", 30))

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""
Judge this coding battle.

Language: {language}

Problem:
{problem}

User Code:
{user_code}

Bot code assumed correct.

Give user score out of 100 based on:
- correctness
- syntax
- logic
- efficiency

Bot score random between 60 to 95.

Faster time gets bonus.

Return ONLY JSON:

{{
 "winner":"🏆 YOU WIN",
 "my_score":85,
 "bot_score":78,
 "my_time":{user_time},
 "bot_time":{bot_time}
}}
"""

        payload = {
            "model":"openai/gpt-4o-mini",
            "temperature":0.7,
            "messages":[
                {"role":"system","content":prompt}
            ]
        }

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        txt = r.json()["choices"][0]["message"]["content"]

        start = txt.find("{")
        end = txt.rfind("}") + 1
        txt = txt[start:end]

        obj = json.loads(txt)

        return jsonify(obj)

    except:
        return jsonify({
            "winner":"🤝 DRAW",
            "my_score":70,
            "bot_score":70,
            "my_time":60,
            "bot_time":30
        })


# =====================================
# RUN
# =====================================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)