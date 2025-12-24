from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc

question_bp = Blueprint("question", __name__)


# ---------------- GET all Question----------------
@question_bp.route("/getall", methods=["GET"])
def get_all_Quesion():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(" SELECT q_id, description  from  Question")
    rows = cursor.fetchall()

    questions = []
    for row in rows:
        questions.append({
            "qid": row[0],
            "description": row[1],

        })

    conn.close()
    return jsonify(questions), 200


# ---------------- INSERT Question  ------------
@question_bp.route("/insert", methods=["POST"])
def add_question():
    data = request.json

    description = data.get("description")
    duration = data.get("duration")


    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO Question (description, duration , counts) VALUES (?, ?, ?)",
        (description, duration,0)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": "Question added successfully"}), 201


# ---------------- update Question  ------------

@question_bp.route("/update/<int:question_id>", methods=["PUT"])
def update_question(question_id):

    data = request.json
    description = data.get("description")
    duration = data.get("duration")
    counts = data.get("counts")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Question SET description=?, duration = ?,  counts=?  WHERE q_id = ?",
        (description, duration,counts , question_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": f"Question {question_id} updated successfully"}), 200




# ---------------- DELETE Question ----------------
@question_bp.route("/delete/<int:question_id>", methods=["DELETE"])
def delete_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("SELECT * FROM Question WHERE q_id = ?", (question_id,))
        question = cursor.fetchone()

        if question is None:
            return jsonify({"error": "Question not found"}), 404


        cursor.execute("DELETE FROM Question WHERE q_id = ?", (question_id,))
        conn.commit()

        return jsonify({"success": f"Question {question_id} deleted successfully"}), 200

    except pyodbc.IntegrityError as ie:

        return jsonify({
            "error": "Cannot delete question. It is referenced in another table (SQStats).",
            "details": str(ie)
        }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

# ---------------- GET Question BY ID  ------------

@question_bp.route("/getbyid/<int:question_id>", methods=["GET"])
def get_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT q_id, description, duration FROM Question WHERE q_id = ?", (question_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        question = {
            "q_id": row[0],
            "description": row[1],
            "duration": row[2]
        }
        return jsonify(question), 200
    else:
        return jsonify({"error": "Question not found"}), 404


