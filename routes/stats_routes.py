from flask import Blueprint, jsonify
from database.db import get_db_connection

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/<int:sid>", methods=["GET"])
def get_stats_by_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM SQStats WHERE sId=?", (sid,))
    rows = cursor.fetchall()

    stats = []
    for row in rows:
        stats.append({
            "statsId": row[0],
            "sId": row[1],
            "qId": row[2],
            "time": str(row[3]),
            "stressScore": row[4],
            "stressLevel": row[5]
        })

    conn.close()
    return jsonify(stats)
