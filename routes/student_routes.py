from flask import Blueprint, request, jsonify
from database.db import get_db_connection

student_bp = Blueprint("student", __name__)

# GET all students
@student_bp.route("", methods=["GET"])
def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sId, Regno, Name, Gender, cgpa, semester FROM Student")
    rows = cursor.fetchall()

    students = []
    for row in rows:
        students.append({
            "sId": row[0],
            "Regno": row[1],
            "Name": row[2],
            "Gender": row[3],
            "cgpa": row[4],
            "semester": row[5]
        })

    conn.close()
    return jsonify(students)

# ADD student
@student_bp.route("/add", methods=["POST"])
def add_student():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Student (Regno, Name, Gender, Password, cgpa, semester)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["Regno"],
        data["Name"],
        data["Gender"],
        data["Password"],
        data["cgpa"],
        data["semester"]
    ))

    conn.commit()
    conn.close()
    return jsonify({"message": "Student added successfully"})
