import os
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify
from database.db import get_db_connection


report_bp = Blueprint("report", __name__)

#1 Get All Reports By Student ID  Admin & Student Side
#2 Get Top 5 Recent Reports By Student ID Student side
#3 Get Unattempted Question For Student  easy  Student side
#4 Get Unattempted Question For Student  Hard  Student side
#5 Get Unattempted Question For Student  Medium  Student side
#6 Question  Report By QID admin side
#7 Student Session Report Student side
#8 Student Question Report student side



# ---------------- Get All Reports By Student ID  Admin & Student Side----------------
@report_bp.route("/allsession/<int:sid>", methods=["GET"])
def get_student_reports(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
        s.sessionid,
        CONVERT(VARCHAR, s.endtime, 23) AS date,

        CONCAT(
            CAST(AVG(r.AfterQuestionsys) AS INT),
            '/',
            CAST(AVG(r.AfterQuestionDIA) AS INT)
        ) AS bp,

        AVG(r.HR)   AS avg_hr,
        AVG(r.SDNN) AS avg_sdnn,

        -- Most common stress level in session
        (
         SELECT TOP 1 r2.stresslevel
           FROM Reports r2
            WHERE r2.sessionid = s.sessionid   -- ✅ FIX
            GROUP BY r2.stresslevel
            ORDER BY COUNT(*) DESC
      ) AS stresslevel

    FROM Session s
    JOIN Reports r ON r.sessionid = s.sessionid
    WHERE s.sid = ?
    GROUP BY s.sessionid, s.endtime
    ORDER BY s.endtime ASC;

       


        """,
        (sid,),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    return jsonify(
        [
            {

                "sessionId": r[0],
                "date": r[1],
                "afterQuestionBP": r[2] ,
                "heartRate": r[3],
                "sdnn": r[4],
                "stressLevel": r[5],
            }
            for r in rows
        ]
    ), 200


# ---------------- Get Top 5 Recent Reports By Student ID Student side ----------------
@report_bp.route("/sessiontop5/<int:sid>", methods=["GET"])
def get_student_reports_top5(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """ 
                SELECT 
                top 5
                s.sessionid,
                CONVERT(VARCHAR, s.endtime, 23) AS date,

                CONCAT(
                    CAST(AVG(r.AfterQuestionsys) AS INT),
                    '/',
                    CAST(AVG(r.AfterQuestionDIA) AS INT)
                ) AS bp,

                AVG(r.HR)   AS avg_hr,
                AVG(r.SDNN) AS avg_sdnn,

                -- Most common stress level in session
                (
                 SELECT TOP 1 r2.stresslevel
                   FROM Reports r2
                    WHERE r2.sessionid = s.sessionid   -- ✅ FIX
                    GROUP BY r2.stresslevel
                    ORDER BY COUNT(*) DESC
              ) AS stresslevel

            FROM Session s
            JOIN Reports r ON r.sessionid = s.sessionid
            WHERE s.sid = ?
            GROUP BY s.sessionid, s.endtime
            ORDER BY s.endtime ASC;




                """,
        (sid,),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "No reports found"}), 404

    return jsonify(
        [
            {

                "sessionId": r[0],
                "date": r[1],
                "afterQuestionBP": r[2],
                "heartRate": r[3],
                "sdnn": r[4],
                "stressLevel": r[5],
            }
            for r in rows
        ]
    ), 200


# ---------------- Get Unattempted Question For Student  easy  Student side ----------------
@report_bp.route("/unattemptedeasy/<int:sid>", methods=["GET"])
def get_question_for_student_easy(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
       SELECT TOP 1 q.qid, q.description, q.duration, q.questionlevel, q.COUNT
       FROM Question q
       WHERE q.questionlevel = 'easy'
         AND NOT EXISTS (
             SELECT 1
             FROM QuestionAttempt qa
             WHERE qa.qid = q.qid
               AND qa.sid = ?
         )
       ORDER BY q.COUNT ASC;
    """

    cursor.execute(query, (sid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "qid": row[0],
            "description": row[1],
            "duration": row[2],
            "questionlevel": row[3],
            "count": row[4]
        }), 200
    else:
        return jsonify({"message": "No new question available for this student"}), 404



# ---------------- Get Unattempted Question For Student  hard  Student side ----------------
@report_bp.route("/unattemptedhard/<int:sid>", methods=["GET"])
def get_question_for_student_hard(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
       SELECT TOP 1 q.qid, q.description, q.duration, q.questionlevel, q.COUNT
       FROM Question q
       WHERE q.questionlevel = 'hard'
         AND NOT EXISTS (
             SELECT 1
             FROM QuestionAttempt qa
             WHERE qa.qid = q.qid
               AND qa.sid = ?
         )
       ORDER BY q.COUNT ASC;
    """

    cursor.execute(query, (sid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "qid": row[0],
            "description": row[1],
            "duration": row[2],
            "questionlevel": row[3],
            "count": row[4]
        }), 200
    else:
        return jsonify({"message": "No new question available for this student"}), 404



# ---------------- Get Unattempted Question For Student  Medium  Student side----------------
@report_bp.route("/unattemptedmedium/<int:sid>", methods=["GET"])
def get_question_for_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
       SELECT TOP 1 q.qid, q.description, q.duration, q.questionlevel, q.COUNT
       FROM Question q
       WHERE q.questionlevel = 'Medium'
         AND NOT EXISTS (
             SELECT 1
             FROM QuestionAttempt qa
             WHERE qa.qid = q.qid
               AND qa.sid = ?
         )
       ORDER BY q.COUNT ASC;
    """

    cursor.execute(query, (sid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "qid": row[0],
            "description": row[1],
            "duration": row[2],
            "questionlevel": row[3],
            "count": row[4]
        }), 200
    else:
        return jsonify({"message": "No new question available for this student"}), 404





# ---------------- Question  Report By QID admin side ----------------
@report_bp.route("/reportbyqid/<int:qid>", methods=["GET"])
def question_report(qid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
       SELECT 
            q.qid,
            q.description,
            q.duration,
            COUNT(r.reportid) AS total_attempts,
             CONCAT(
			   CAST(AVG(r.AfterQuestionsys) AS INT),
					'/',
			  CAST(AVG(r.AfterQuestionDIA) AS INT)
				 ) AS bp,
            AVG(r.HR)    AS avg_hr,
            AVG(r.SDNN)  AS avg_sdnn,
            AVG(r.RMSSD) AS avg_rmssd,
            AVG(r.SI)    AS avg_si,
            
            (
                SELECT TOP 1 r2.stresslevel
                FROM Reports r2
                WHERE r2.qid = q.qid
                GROUP BY r2.stresslevel
                ORDER BY COUNT(*) DESC
            ) AS most_common_stress_level
        FROM Question q
        LEFT JOIN Reports r ON q.qid = r.qid
        WHERE q.qid = ?
        GROUP BY q.qid, q.description, q.duration

    """

    cursor.execute(query, (qid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Question not found"}), 404

    response = {
        "qid": row[0],
        "description": row[1],
        "duration": row[2],
        "total_attempts": row[3],
        "avg_bp": row[4],
        "avg_heart_rate": row[5],
        "avg_sdnn": row[6],
        "avg_rmssd": row[7],
        "avg_si": row[8],
        "most_common_stress_level":row[9],
    }

    return jsonify(response), 200




# ---------------- Student Session Report Student side ----------------

@report_bp.route("/student_session_report/<int:sid>/<int:sessionid>", methods=["GET"])
def student_session_report(sid, sessionid):
    conn = get_db_connection()
    cursor = conn.cursor()

    # ---------------- Student Name ----------------
    cursor.execute("SELECT name FROM Student WHERE sid = ?", (sid,))
    student_row = cursor.fetchone()

    if not student_row:
        conn.close()
        return jsonify({"message": "Student not found"}), 404

    student_name = student_row[0]

    # ---------------- Attempted Questions ----------------
    question_query = """
        SELECT q.qid, q.description
        FROM Question q
        WHERE EXISTS (
            SELECT 1
            FROM QuestionAttempt qa
            WHERE q.qid = qa.qid
              AND qa.sessionid = ?
              AND qa.sid = ?
        )
    """

    cursor.execute(question_query, (sessionid, sid))
    questions = cursor.fetchall()

    question_list = []
    for row in questions:
        question_list.append({
            "qid": row[0],
            "description": row[1]
        })

    # ---------------- Overall Stress & Performance ----------------
    report_query = """
        SELECT  
            CONVERT(VARCHAR(10), s.endtime, 23) AS date,

            (
                SELECT TOP 1 r2.stresslevel
                FROM Reports r2
                WHERE r2.sessionid = s.sessionid
                GROUP BY r2.stresslevel
                ORDER BY COUNT(*) DESC
            ) AS stresslevel,

            DATEDIFF(MINUTE, s.starttime, s.endtime) AS min,

            CONCAT(
                CAST(AVG(r.AfterQuestionsys) AS INT),
                '/',
                CAST(AVG(r.AfterQuestionDIA) AS INT)
            ) AS bp,

            AVG(r.HR)    AS HR,
            AVG(r.SDNN)  AS SDNN,
            AVG(r.RMSSD) AS RMSSD,
            AVG(r.pNN50) AS pNN50,
            AVG(r.SI)    AS si

        FROM session s
        LEFT JOIN Reports r 
            ON s.sessionid = r.sessionid

        WHERE s.sessionid = ?
        GROUP BY s.sessionid, s.starttime, s.endtime
    """

    cursor.execute(report_query, (sessionid,))
    report_row = cursor.fetchone()

    conn.close()

    if not report_row:
        return jsonify({"message": "No report found for this session"}), 404

    return jsonify({
        "student_name": student_name,
        "session_id": sessionid,
        "date": report_row[0],
        "final_stress_level": report_row[1],
        "total_minutes": report_row[2],
        "average_bp": report_row[3],
        "HR": report_row[4],
        "SDNN": report_row[5],
        "RMSSD": report_row[6],
        "pNN50": report_row[7],
        "SI": report_row[8],
        "attempted_questions": question_list
    }), 200



# ---------------- Student Question Report student side   ----------------
@report_bp.route("/student_question_report/<int:sid>/<int:qid>", methods=["GET"])
def student_question_report(sid, qid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT TOP 1
            q.description,
            CONVERT(VARCHAR(8), r.TimeTaken, 108) AS time,

            CONCAT(
                r.AfterQuestionsys,
                '/',
                r.AfterQuestionDIA
            ) AS bp,

            r.HR,
            r.SDNN,
            r.RMSSD,
            r.SI,
            r.stresslevel

        FROM Question q
        LEFT JOIN Reports r ON q.qid = r.qid
        WHERE q.qid = ?
          AND r.sid = ?
        ORDER BY r.reportid DESC
    """

    cursor.execute(query, (qid, sid))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"message": "No report found for this student and question"}), 404

    return jsonify({
        "question_id": qid,
        "description": row[0],
        "time_taken": row[1],
        "bp": row[2],
        "HR": row[3],
        "SDNN": row[4],
        "RMSSD": row[5],
        "SI": row[6],
        "stress_level": row[7]
    }), 200















