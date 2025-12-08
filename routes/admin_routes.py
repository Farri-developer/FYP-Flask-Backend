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


# ---------------- Question Screen Admin side ----------------
# ---------------- GET all Question Screen Admin side ----------------
@admin_BP.route("/GetQuesion", methods=["GET"])
def get_all_Quesion():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(" SELECT qid, description  from  Question")
    rows = cursor.fetchall()

    questions = []
    for row in rows:
        questions.append({
            "qid": row[0],
            "description": row[1],

        })

    conn.close()
    return jsonify(questions), 200


# ---------------- ADD Question (Admin side) ------------
@admin_BP.route("/AddQuestion", methods=["POST"])
def add_question():
    data = request.json
    if not data:
        return jsonify({"error": "Missing data"}), 400

    description = data.get("description")
    duration = data.get("duration")

    if not description or not duration:
        return jsonify({"error": "description and duration are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO Question (description, duration) VALUES (?, ?)",
        (description, duration)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": "Question added successfully"}), 201


# ---------------- update  Question (Admin side) ------------

@admin_BP.route("/UpdateQuestion/<int:question_id>", methods=["PUT"])
def update_question(question_id):
    data = request.json
    if not data:
        return jsonify({"error": "Missing data"}), 400

    description = data.get("description")
    duration = data.get("duration")

    if not description and not duration:
        return jsonify({"error": "At least one of description or duration is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Question SET description = ?, duration = ? WHERE qid = ?",
        (description, duration, question_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": f"Question {question_id} updated successfully"}), 200

# ---------------- GET Question BY ID (Admin side) ------------

@admin_BP.route("/GetQuestion/<int:question_id>", methods=["GET"])
def get_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT qid, description, duration FROM Question WHERE qid = ?", (question_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        question = {
            "qid": row[0],
            "description": row[1],
            "duration": row[2]
        }
        return jsonify(question), 200
    else:
        return jsonify({"error": "Question not found"}), 404


# ----------- Get One Unattempted Question For Student -------------
@admin_BP.route("/GetQuestionByStudent/<int:sid>", methods=["GET"])
def get_question_for_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 1 q.qid, q.description, q.duration
        FROM Question q
        WHERE NOT EXISTS (
            SELECT 1
            FROM SQStats s
            WHERE s.qid = q.qid
              AND s.sid = ?
        )
        ORDER BY q.qid
    """, (sid,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "qid": row[0],
            "description": row[1],
            "duration": row[2]
        }), 200
    else:
        return jsonify({
            "message": "No new question available for this student"
        }), 404



# ---------------- DELETE Question BY ID (Admin side) ------------

@admin_BP.route("/DeleteQuestion/<int:question_id>", methods=["DELETE"])
def delete_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if question exists
    cursor.execute("SELECT qid FROM Question WHERE qid = ?", (question_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Question not found"}), 404

    # Delete the question
    cursor.execute("DELETE FROM Question WHERE qid = ?", (question_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": f"Question {question_id} deleted successfully"}), 200





# ---------------- Report Screen  GET ALL DATA (Admin side) ------------
@admin_BP.route("/question-report/<int:question_id>", methods=["GET"])
def question_report(question_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT 
        Q.qid,
        Q.description,
        Q.duration,

        COUNT(Se.qId) AS total_attempts,

        AVG(Se.SYS),
        AVG(Se.dys),
        AVG(Se.hr),
        AVG(Se.SDNN),
        AVG(Se.RMSSD),
        AVG(Se.SI),
        AVG(Se.RI),
        AVG(Se.CL),

        (
            SELECT TOP 1 StressLevel
            FROM SQSession se2
            WHERE se2.qId = Q.qid
            GROUP BY StressLevel
            ORDER BY COUNT(*) DESC
        ) AS most_common_stress_level

    FROM Question Q
    LEFT JOIN SQSession Se 
        ON Q.qid = Se.qId

    WHERE Q.qid = ?

    GROUP BY Q.qid, Q.description, Q.duration;
    """

    cursor.execute(query, (question_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Question not found"}), 404

    response = {
        "question_id": row[0],
        "question_description": row[1],
        "duration": row[2],
        "total_attempts": row[3],
         "avg_sys": round(row[4] ),
        "avg_dys": round(row[5] ),
        "avg_heart_rate": round(row[6] ),
        "avg_sdnn": round(row[7] ),
        "avg_rmssd": round(row[8]),
        "avg_si": round(row[9] ),
        "avg_ri": round(row[10] ),
        "avg_cl": round(row[11]),
        "most_common_stress_level": row[12]
    }

    return jsonify(response), 200




# ---------------- STUDENTS  Admin side ----------------

# GET all students
@admin_BP.route("GetStudent", methods=["GET"])
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
            "semester": row[5]
        })

    conn.close()
    return jsonify(students)


# ---------------- Insert Student   Admin side ----------------

@admin_BP.route("/studentInsert", methods=["POST"])
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


# ---------------- Update Student   Admin side ----------------
@admin_BP.route("/studentUpdate/<int:id>", methods=["PUT"])
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
@admin_BP.route("/studentDelete/<int:id>", methods=["DELETE"])
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


# ----------- Get all Reports By Student ID -------------
@admin_BP.route("/studentReports/<int:sid>", methods=["GET"])
def get_student_reports(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            sessionId,
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
@admin_BP.route("/studentReportsTop5/<int:sid>", methods=["GET"])
def get_student_reports_top5(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 5 
               sessionId,
               CONVERT(VARCHAR, endTime, 23) AS endDate,
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
