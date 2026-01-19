from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc

question_bp = Blueprint("question", __name__)


# ---------------- GET all Question----------------

@question_bp.route("/getall", methods=["GET"])
def get_all_questions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT qid, description, duration, questionlevel, count FROM Question")
    rows = cursor.fetchall()
    conn.close()

    questions = [{
        "qid": r[0],
        "description": r[1],
        "duration": r[2],
        "questionlevel": r[3],
        "count": r[4]
    } for r in rows]

    return jsonify(questions), 200


# ---------------- INSERT Question  ------------

@question_bp.route("/insert", methods=["POST"])
def add_question():
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Question (description, duration, questionlevel, count)
        VALUES (?, ?, ?, ?)
    """, (
        data["description"],
        data["duration"],
        data.get("questionlevel"),
        0
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Question added successfully"}), 201





# ---------------- update Question  ------------


@question_bp.route("/update/<int:qid>", methods=["PUT"])
def update_question(qid):
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Question
        SET description = ?,
            duration = ?,
            questionlevel = ?,
            count = ?
        WHERE qid = ?
    """, (
        data["description"],
        data["duration"],
        data.get("questionlevel"),
        data.get("count", 0),
        qid
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Question {qid} updated successfully"}), 200


# ---------------- DELETE Question ----------------

@question_bp.route("/delete/<int:qid>", methods=["DELETE"])
def delete_question(qid):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT qid FROM Question WHERE qid = ?", (qid,))
        if not cursor.fetchone():
            return jsonify({"error": "Question not found"}), 404

        cursor.execute("DELETE FROM Question WHERE qid = ?", (qid,))
        conn.commit()

        return jsonify({"message": f"Question {qid} deleted successfully"}), 200

    except pyodbc.IntegrityError:
        return jsonify({
            "error": "Cannot delete question. It is referenced in another table."
        }), 400

    finally:
        conn.close()



# ---------------- GET Question BY ID  ------------
@question_bp.route("/getbyid/<int:qid>", methods=["GET"])
def get_question_by_id(qid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT qid, description, duration, questionlevel, count
        FROM Question
        WHERE qid = ?
    """, (qid,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Question not found"}), 404

    return jsonify({
        "qid": row[0],
        "description": row[1],
        "duration": row[2],
        "questionlevel": row[3],
        "count": row[4]
    }), 200

