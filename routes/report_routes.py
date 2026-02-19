import os
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify
from database.db import get_db_connection


report_bp = Blueprint("report", __name__)

# ---------------- Get All Reports By Student ID ----------------
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


# ---------------- Get Top 5 Recent Reports By Student ID ----------------
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



# ---------------- Get Unattempted Question For Student ----------------
@report_bp.route("/unattemptedforsid/<int:sid>", methods=["GET"])
def get_question_for_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
       
        SELECT top 1 q.qid, q.description, q.duration
        FROM Question q
        WHERE NOT EXISTS (
        SELECT 1
        FROM QuestionAttempt qa
        WHERE qa.qid = q.qid
        AND qa.sid = ?
    )
    ORDER BY COUNT ASC
    """

    cursor.execute(query, (sid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "qid": row[0],
            "description": row[1],
            "duration": row[2],
        }), 200
    else:
        return jsonify({"message": "No new question available for this student"}), 404






# ---------------- Question Analytics Report By QID ----------------
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




















@report_bp.route("/eeg/alpha/combined", methods=["GET"])
def get_combined_alpha_timestamp():
    try:
        # 🔹 Absolute path based on current file
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_PATH = os.path.join(BASE_DIR, "..", "Data", "Raw10.csv")

        if not os.path.exists(DATA_PATH):
            return jsonify({"error": f"CSV file not found at {DATA_PATH}"}), 404

        df = pd.read_csv(DATA_PATH)

        fs = 128          # Sampling rate (Hz)
        window_sec = 1
        step_sec = 1      # 1 second step

        window_size = fs * window_sec
        step_size = fs * step_sec

        channels = ["Ch1", "Ch2", "Ch3", "Ch4"]
        alpha_values = []
        time_axis = []

        # 🔒 Safe Alpha Power computation
        def alpha_power(signal, fs):
            if len(signal) == 0:
                return 0.0
            signal = signal - np.mean(signal)
            fft_vals = np.abs(np.fft.rfft(signal)) ** 2
            freqs = np.fft.rfftfreq(len(signal), 1/fs)
            alpha_band = (freqs >= 8) & (freqs <= 12)
            if not np.any(alpha_band):
                return 0.0
            power = np.mean(fft_vals[alpha_band])
            if np.isnan(power) or np.isinf(power):
                return 0.0
            return float(np.log10(power + 1))

        # 🔹 Sliding window computation
        t = 0
        for i in range(0, len(df) - window_size, step_size):
            ch_alpha = []
            for ch in channels:
                if ch not in df.columns:
                    ch_alpha.append(0.0)
                    continue
                window_signal = df[ch].values[i:i + window_size]
                ch_alpha.append(alpha_power(window_signal, fs))
            combined_alpha = np.mean(ch_alpha)
            if np.isnan(combined_alpha) or np.isinf(combined_alpha):
                combined_alpha = 0.0
            alpha_values.append(combined_alpha)
            time_axis.append(t)
            t += step_sec

        # 🔹 Moving average smoothing
        def moving_average(arr, n=5):
            arr = np.array(arr, dtype=float)
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            if len(arr) < n:
                return arr
            return np.convolve(arr, np.ones(n)/n, mode='valid')

        smooth_alpha = moving_average(alpha_values, n=5)
        smooth_alpha = np.nan_to_num(smooth_alpha, nan=0.0, posinf=0.0, neginf=0.0)
        smooth_time = time_axis[:len(smooth_alpha)]

        return jsonify({
            "time": smooth_time,
            "alpha": smooth_alpha.tolist()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500