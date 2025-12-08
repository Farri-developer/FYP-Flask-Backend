from flask import Blueprint, request, jsonify
from database.db import get_db_connection

student_bp = Blueprint("student", __name__)

# ---------------- STUDENTS   ----------------

# GetStudent
@student_bp.route("/getAll", methods=["GET"])
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


# ---------------- insertStudent ----------------

@student_bp.route("/insert", methods=["POST"])
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


# ---------------- updateStudent ----------------
@student_bp.route("/update/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Student
        SET Regno = ?, 
            Name = ?, 
            Gender = ?, 
            Password = ?, 
            cgpa = ?, 
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

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "Student updated successfully"})


# ---------------- Delete Student (Admin side) ----------------
@student_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Student
        WHERE sid = ?
    """, (id,))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "Student deleted successfully"})


# Report api part


# ----------- Get all Reports By Student ID -------------
@student_bp.route("/allReports/<int:sid>", methods=["GET"])
def get_student_reports(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT sessionId,
                          CONVERT(VARCHAR, endTime, 23) AS endDate,
                          sys,
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
@student_bp.route("/ReportsTop5/<int:sid>", methods=["GET"])
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

