from flask import Blueprint, request, jsonify
from database.db import get_db_connection

admin_BP = Blueprint("admin", __name__)


# ---------------- LOGIN (ADMIN + STUDENT) ----------------
@admin_BP.route("", methods=["POST"])
def login():
    data = request.json
    users = data.get("users")        # username / regno
    passwords = data.get("passwords")


    if users == "admin" and passwords == "1234":
        return jsonify({
            "role": "admin",
            "message": "Admin Login Successfully"
        })


    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s_id, regno, name
        FROM Student
        WHERE regno = ? AND password = ?
    """, (users, passwords))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "role": "student",
            "message": "Login Successfully",
            "s_id": row[0],
            "Regno": row[1],
            "Name": row[2]
        })


    return jsonify({"error": "Invalid Credentials"}), 401
