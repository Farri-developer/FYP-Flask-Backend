from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc


student_bp = Blueprint("student", __name__)

# ---------------- STUDENTS   ----------------

#------------- GetStudent all student---------
@student_bp.route("/getall", methods=["GET"])
def GetStudent():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sId, Regno, Name, semester FROM Student")
    rows = cursor.fetchall()

    students = []
    for row in rows:
        students.append({
            "sId": row[0],
            "Regno": row[1],
            "Name": row[2],
            "semester": row[3]
        })

    conn.close()
    return jsonify(students)


# -----------------GetStudent by id-------------
@student_bp.route("/getbyid/<int:id>", methods=["GET"])
def GetStudentById(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sId, Regno, Name, semester,cgpa,gender,password FROM student where sid = ?", (id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Student not found"}), 404

    student = {
            "sId": row[0],
            "Regno": row[1],
            "Name": row[2],
            "semester": row[3],
            "cgpa": row[4],
            "gender": row[5],
            "password": row[6]
    }
    conn.close()
    return jsonify(student)

from flask import Blueprint, request, jsonify
import sqlite3


# ---------------- insertStudent ----------------
@student_bp.route("/insert", methods=["POST"])
def add_student():
    try:
        data = request.get_json()  # safer than request.json


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
        return jsonify({"message": "Student added successfully"}), 201

    except Exception :
        return jsonify({"Message ": " Arid No Already Existed " }), 500



# ---------------- updateStudent ----------------
@student_bp.route("/update/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
                       UPDATE Student
                       SET Regno    = ?,
                           Name     = ?,
                           Gender   = ?,
                           Password = ?,
                           cgpa     = ?,
                           semester = ?
                       WHERE sid = ?
                       """, (
                           data["Regno"],
                           data["Name"],
                           data["Gender"],
                           data["Password"],
                           data["cgpa"],
                           data["semester"],
                           id
                       ))

        conn.commit()
        conn.close()

        return jsonify({"message": "Student updated successfully"})

    except Exception :
        return jsonify({"Message ": " Arid No Already Existed " })


# ---------------- Delete Student  ----------------
@student_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("SELECT * FROM Student WHERE sid = ?", (id,))
        student = cursor.fetchone()

        if student is None:
            return jsonify({"error": "Student not found"}), 404


        cursor.execute("DELETE FROM Student WHERE sid = ?", (id,))
        conn.commit()

        return jsonify({"success": f"Student {id} deleted successfully"}), 200

    except pyodbc.IntegrityError as ie:

        return jsonify({
            "error": "Cannot delete student. This student is referenced in another table (e.g., SQStats).",
            "details": str(ie)
        }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()




# ----------- Get all Reports By Student ID -------------
@student_bp.route("/allreports/<int:sid>", methods=["GET"])
def get_student_reports(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT sessionId,
                          CONVERT(VARCHAR, endTime, 23) AS endDate,
                          sys ,
                          dys,
                          sdnn,
                          hr,
                          stressLevel
                   FROM SQSession
                   WHERE sid = ?

                   """, (sid,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    reports = []
    for r in rows:
        reports.append({
            "sessionId": r[0],
            "date": r[1],
            "bloodPressure": f"{r[2]} / {r[3]} mmHg",
            "heartRate": f"{r[5]} BPM",
            "sdnn": r[4],
            "stressLevel": r[6]
        })

    return jsonify(reports)


# ----------- Get Top 5 Recent Reports By Student ID -------------
@student_bp.route("/reportstop5/<int:sid>", methods=["GET"])
def get_student_reports_top5(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT TOP 5 
               sessionId, CONVERT(VARCHAR, endTime, 23) AS endDate,
                          sys,
                          dys,
                          sdnn,
                          hr,
                          stressLevel
                   FROM SQSession
                   WHERE sid = ?
                   ORDER BY endTime DESC
                   """, (sid,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    reports = []
    for r in rows:
        reports.append({
            "sessionId": r[0],
            "date": r[1],
            "bloodPressure": f"{r[2]} / {r[3]} mmHg",
            "heartRate": f"{r[5]} BPM",
            "sdnn": r[4],
            "stressLevel": r[6]
        })

    return jsonify(reports)


