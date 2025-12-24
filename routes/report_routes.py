import os
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify
from database.db import get_db_connection


report_bp = Blueprint("report", __name__)


#--------------------------------------------


# ----------- Get One Unattempted Question For Student -------------
@report_bp.route("/unattemptedforsid/<int:sid>", methods=["GET"])
def get_question_for_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 1 q.q_id, q.description, q.duration
        FROM Question q
        WHERE NOT EXISTS (
            SELECT 1
            FROM QuestionAttempt qa
            JOIN StudentSession ss ON qa.session_id = ss.session_id
            WHERE qa.q_id = q.q_id
              AND qa.s_id = ?
        )
        ORDER BY q.q_id
    """, (sid,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "q_id": row[0],
            "description": row[1],
            "duration": row[2]
        }), 200
    else:
        return jsonify({
            "message": "No new question available for this student"
        }), 404



# ---------------- question-report-ID ----------------
@report_bp.route("/reportbyqid/<int:question_id>", methods=["GET"])
def question_report(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            q.q_id,
            q.description,
            q.duration,
            COUNT(r.report_id) AS total_attempts,
            AVG(r.SYS)   AS avg_sys,
            AVG(r.DYS)   AS avg_dys,
            AVG(r.HR)    AS avg_hr,
            AVG(r.SDNN)  AS avg_sdnn,
            AVG(r.RMSSD) AS avg_rmssd,
            AVG(r.SI)    AS avg_si,
            AVG(r.RI)    AS avg_ri,
            AVG(r.CL)    AS avg_cl,
            (
                SELECT TOP 1 r2.stress_level
                FROM Reports r2
                WHERE r2.q_id = q.q_id
                GROUP BY r2.stress_level
                ORDER BY COUNT(*) DESC
            ) AS most_common_stress_level
        FROM Question q
        LEFT JOIN Reports r ON q.q_id = r.q_id
        WHERE q.q_id = ?
        GROUP BY q.q_id, q.description, q.duration
    """

    cursor.execute(query, (question_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Question not found"}), 404

    response = {
        "q_id": row[0],
        "description": row[1],
        "duration": row[2],
        "total_attempts": row[3],
        "avg_sys": round(row[4]) if row[4] else None,
        "avg_dys": round(row[5]) if row[5] else None,
        "avg_heart_rate": round(row[6]) if row[6] else None,
        "avg_sdnn": round(row[7]) if row[7] else None,
        "avg_rmssd": round(row[8]) if row[8] else None,
        "avg_si": round(row[9]) if row[9] else None,
        "avg_ri": round(row[10]) if row[10] else None,
        "avg_cl": round(row[11]) if row[11] else None,
        "most_common_stress_level": row[12]
    }

    return jsonify(response), 200


#Band Graph

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