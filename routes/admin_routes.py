from flask import Blueprint, request, jsonify
from database.db import get_db_connection

admin_BP = Blueprint("admin", __name__)

# ---------------- LOGIN ----------------
@admin_BP.route("", methods=["POST"])
def getAdmin():
    data = request.json
    users = data["users"]
    passwords = data["passwords"]

    if users == "admin" and passwords == "1234":
        return jsonify({"success": "Logged in successfully"})
    else:
        return jsonify({"error": "Invalid credentials"}), 401


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




# ---------------- STUDENTS Screen Admin side ----------------

