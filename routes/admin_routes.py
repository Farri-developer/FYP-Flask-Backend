from flask import Blueprint, request, jsonify
from database.db import get_db_connection

admin_BP = Blueprint("admin", __name__)


# ---------------- LOGIN (ADMIN + STUDENT) done ----------------
@admin_BP.route("", methods=["POST"])
def login():
    data = request.json
    users = data.get("users")        # username / regno
    passwords = data.get("passwords")


    if users == "admin" and passwords == "1234":
        return jsonify({
            "role": "admin",
        })


    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sid, regno, name
        FROM Student
        WHERE regno = ? AND password = ?
    """, (users, passwords))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "role": "student",
        })


    return jsonify({"error": "Invalid Credentials"}), 401
