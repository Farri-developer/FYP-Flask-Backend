from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc


student_bp = Blueprint("student", __name__)

# ---------------- STUDENTS   ----------------

# GetStudent all student
# GetStudent by id
# insertStudent done
# Delete Student
# updateStudent


#------------- GetStudent all student---------


@student_bp.route("/getall", methods=["GET"])
def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sid, regno, name, semester,cgpa , password,gender FROM Student")
    rows = cursor.fetchall()
    conn.close()

    students = [{
        "sid": r[0],
        "regno": r[1],
        "name": r[2],
        "semester": r[3],
        "cgpa":r[4],
        "password":r[5]

    } for r in rows]

    return jsonify(students), 200

# -----------------GetStudent by id-------------

@student_bp.route("/getbyid/<int:sid>", methods=["GET"])
def get_student_by_id(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sid, regno, name, semester, cgpa, gender, password
        FROM Student
        WHERE sid = ?
    """, (sid,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({
        "sid": row[0],
        "regno": row[1],
        "name": row[2],
        "semester": row[3],
        "cgpa": row[4],
        "gender": row[5],
        "password": row[6]
    }), 200


# ---------------- insertStudent done ----------------

@student_bp.route("/insert", methods=["POST"])
def add_student():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Student (regno, name, gender, password, cgpa, semester)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["regno"],
            data["name"],
            data["gender"],
            data["password"],
            data["cgpa"],
            data["semester"]
        ))

        conn.commit()
        conn.close()
        return jsonify({"message": "Student added successfully"}), 201

    except Exception:
        return jsonify({"error": "ARID number already exists"}), 400



# ---------------- updateStudent ----------------

@student_bp.route("/update/<int:sid>", methods=["PUT"])
def update_student(sid):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE Student
            SET regno = ?, name = ?, gender = ?, password = ?, cgpa = ?, semester = ?
            WHERE sid = ?
        """, (
            data["regno"],
            data["name"],
            data["gender"],
            data["password"],
            data["cgpa"],
            data["semester"],
            sid
        ))

        conn.commit()
        conn.close()
        return jsonify({"message": "Student updated successfully"}), 200

    except Exception:
        return jsonify({"error": "ARID number already exists"}), 400



# ---------------- Delete Student  ----------------

@student_bp.route("/delete/<int:sid>", methods=["DELETE"])
def delete_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT sid FROM Student WHERE sid = ?", (sid,))
        if not cursor.fetchone():
            return jsonify({"error": "Student not found"}), 404

        cursor.execute("DELETE FROM Student WHERE sid = ?", (sid,))
        conn.commit()
        return jsonify({"message": "Student deleted successfully"}), 200

    except pyodbc.IntegrityError:
        return jsonify({
            "error": "Cannot delete student. Student has related records."
        }), 400

    finally:
        conn.close()

