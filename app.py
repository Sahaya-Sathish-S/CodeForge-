from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json

app = Flask(__name__, static_folder=".")
CORS(app)

OPENROUTER_API_KEY = "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"

# =====================================
# HOME
# =====================================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def files(path):
    return send_from_directory(".", path)

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
                    "role":"system",
                    "content":"You are CodeForge AI. Helpful, smart, professional assistant."
                },
                {
                    "role":"user",
                    "content":msg
                }
            ]
        }

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code != 200:
            return jsonify({"reply": "API Error"})

        result = r.json()
        reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"})


# =====================================
# QUIZ GAME
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
            return jsonify([
                {"q":"API Failed","o":["A","B","C","D"],"a":0}
            ])

        txt = r.json()["choices"][0]["message"]["content"].strip()

        start = txt.find("[")
        end = txt.rfind("]") + 1
        txt = txt[start:end]

        data = json.loads(txt)

        return jsonify(data)

    except:
        return jsonify([
            {"q":"Quiz Error","o":["A","B","C","D"],"a":0}
        ])


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

    except Exception as e:
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
    app.run(host="0.0.0.0", port=5000, debug=True)