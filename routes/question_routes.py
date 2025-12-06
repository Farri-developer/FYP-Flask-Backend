from flask import Blueprint, jsonify
from database.db import get_db_connection

question_bp = Blueprint("question", __name__)

@question_bp.route("", methods=["GET"])
def get_questions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT qId, description, duration FROM Question")
    rows = cursor.fetchall()

    questions = []
    for row in rows:
        questions.append({
            "qId": row[0],
            "description": row[1],
            "duration": row[2]
        })

    conn.close()
    return jsonify(questions)
