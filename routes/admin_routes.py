from flask import Blueprint, request, jsonify
from database.db import get_db_connection

admin_BP = Blueprint("admin", __name__)


# ---------------- LOGIN (ADMIN + STUDENT) ----------------
@admin_BP.route("", methods=["POST"])
def login():
    data = request.json
    users = data.get("users")        # username / regno
    passwords = data.get("passwords")

    # ✅ ADMIN LOGIN
    if users == "admin" and passwords == "1234":
        return jsonify({
            "role": "admin",
            "message": "Admin Login Successfully"
        })

    # ✅ STUDENT LOGIN (Database)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sId, Regno, Name
        FROM Student
        WHERE Regno = ? AND Password = ?
    """, (users, passwords))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "role": "student",
            "message": "Login Successfully",
            "sId": row[0],
            "Regno": row[1],
            "Name": row[2]
        })

    # ❌ INVALID
    return jsonify({"error": "Invalid Credentials"}), 401

#
#
# SELECT
# sessionId,
# CONVERT(VARCHAR, endTime, 23),
# CONVERT(VARCHAR, startTime, 23),
#
# sys,
# dys,
# sdnn,
# RMSSD
# hr,
#
# RI, SI, CL,
# stressLevel,
# stressScore
# FROM
# SQSession
# WHERE
# sid = 1
