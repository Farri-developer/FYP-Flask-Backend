from flask import Blueprint, request, jsonify
from database.db import get_db_connection


admin_BP = Blueprint("admin", __name__)


# ---------------- LOGIN (ADMIN + STUDENT) done ----------------
@admin_BP.route("", methods=["POST"])
def login():
    data = request.json
    users = data.get('users')
    password = data.get('passwords')

    # Admin login
    if users == "admin" and password == "1234":
        return jsonify({"role": "admin", "message": "Admin Login Successfully"})

    # Student login
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sId, Regno, Name ,semester FROM Student 
        WHERE Regno = ? AND Password = ?
    """, (users, password))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            'role': 'student',
            'message': 'Login Successfully',
            'sId': row[0],
            'regno': row[1],
            'name': row[2],
            'semester' : row[3]
        })

    return jsonify({'message': 'Invalid Credentials!'}), 401