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
    cursor.execute("SELECT s_Id, Regno, Name, semester FROM Student")
    rows = cursor.fetchall()

    students = []
    for row in rows:
        students.append({
            "s_Id": row[0],
            "regno": row[1],
            "name": row[2],
            "semester": row[3]
        })

    conn.close()
    return jsonify(students)


# -----------------GetStudent by id-------------
@student_bp.route("/getbyid/<int:id>", methods=["GET"])
def GetStudentById(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT s_Id, Regno, Name, semester,cgpa,gender,password FROM student where s_id = ?", (id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Student not found"}), 404

    student = {
            "s_Id": row[0],
            "regno": row[1],
            "name": row[2],
            "semester": row[3],
            "cgpa": row[4],
            "gender": row[5],
            "password": row[6]
    }
    conn.close()
    return jsonify(student)



# ---------------- insertStudent ----------------
@student_bp.route("/insert", methods=["POST"])
def add_student():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Student (Regno, Name, Gender, Password, cgpa, semester)
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
                       WHERE s_id = ?
                       """, (
                           data["regno"],
                           data["name"],
                           data["gender"],
                           data["password"],
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

        cursor.execute("SELECT * FROM Student WHERE s_id = ?", (id,))
        student = cursor.fetchone()

        if student is None:
            return jsonify({"error": "Student not found"}), 404


        cursor.execute("DELETE FROM Student WHERE s_id = ?", (id,))
        conn.commit()

        return jsonify({"success": f"Student {id} deleted successfully"}), 200

    except pyodbc.IntegrityError as ie:

        return jsonify({
            "error": "Cannot delete student. This student is referenced in another table (e.g., SQStats).",
            "details": str(ie)
        }), 400


    finally:
        conn.close()


# ---------------- Get all Reports By Student ID ----------------
@student_bp.route("/allreports/<int:s_id>", methods=["GET"])
def get_student_reports(s_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            r.report_id,
            r.session_id,
            CONVERT(VARCHAR, ss.endTime, 23) AS endDate,
            r.SYS,
            r.DYS,
            r.SDNN,
            r.HR,
            r.stress_level
        FROM Reports r
        JOIN StudentSession ss ON r.session_id = ss.session_id
        WHERE r.s_id = ?
        ORDER BY ss.endTime ASC
    """, (s_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    reports = []
    for r in rows:
        reports.append({
            "reportId": r[0],
            "sessionId": r[1],
            "date": r[2],
            "bloodPressure": f"{r[3]} / {r[4]} mmHg",
            "heartRate": f"{r[6]} BPM",
            "sdnn": r[5],
            "stressLevel": r[7]
        })

    return jsonify(reports)


# ---------------- Get Top 5 Recent Reports By Student ID ----------------
@student_bp.route("/reportstop5/<int:s_id>", methods=["GET"])
def get_student_reports_top5(s_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 5 
            r.report_id,
            r.session_id,
            CONVERT(VARCHAR, ss.endTime, 23) AS endDate,
            r.SYS,
            r.DYS,
            r.SDNN,
            r.HR,
            r.stress_level
        FROM Reports r
        JOIN StudentSession ss ON r.session_id = ss.session_id
        WHERE r.s_id = ?
        ORDER BY ss.endTime DESC
    """, (s_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    reports = []
    for r in rows:
        reports.append({
            "reportId": r[0],
            "sessionId": r[1],
            "date": r[2],
            "bloodPressure": f"{r[3]} / {r[4]} mmHg",
            "heartRate": f"{r[6]} BPM",
            "sdnn": r[5],
            "stressLevel": r[7]
        })

    return jsonify(reports)
