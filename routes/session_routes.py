from flask import Blueprint, jsonify
from database.db import get_db_connection

session_bp = Blueprint("session", __name__)

@session_bp.route("/", methods=["GET"])
def get_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM SQSession")
    rows = cursor.fetchall()

    sessions = []
    for row in rows:
        sessions.append({
            "sessionId": row[0],
            "sId": row[1],
            "qId": row[2],
            "startTime": str(row[3]),
            "endTime": str(row[4]),
            "stressScore": row[5],
            "stressLevel": row[6]
        })

    conn.close()
    return jsonify(sessions)
