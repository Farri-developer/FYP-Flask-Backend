from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc

bin_bp = Blueprint("bin", __name__)


#--------------------------------------------


# ----------- Get One Unattempted Question For Student -------------
@bin_bp.route("/unattemptedforsid/<int:sid>", methods=["GET"])
def get_question_for_student(sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT TOP 1 q.qid, q.description, q.duration
                   FROM Question q
                   WHERE NOT EXISTS (SELECT 1
                                     FROM SQStats s
                                     WHERE s.qid = q.qid
                                       AND s.sid = ?)
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
# ---------------- question-report-ID ----------------
@bin_bp.route("/reportbyqid/<int:question_id>", methods=["GET"])
def question_report(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            Q.qid,
            Q.description,
            Q.duration,

            COUNT(Se.sessionId) AS total_attempts,

            AVG(Se.SYS)   AS avg_sys,
            AVG(Se.dys)   AS avg_dys,
            AVG(Se.hr)    AS avg_hr,
            AVG(Se.SDNN)  AS avg_sdnn,
            AVG(Se.RMSSD) AS avg_rmssd,
            AVG(Se.SI)    AS avg_si,
            AVG(Se.RI)    AS avg_ri,
            AVG(Se.CL)    AS avg_cl,

            (
                SELECT TOP 1 se2.StressLevel
                FROM SQSession se2
                WHERE se2.qId = Q.qid
                GROUP BY se2.StressLevel
                ORDER BY COUNT(*) DESC
            ) AS most_common_stress_level

        FROM Question Q
        LEFT JOIN SQSession Se ON Q.qid = Se.qId
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



@bin_bp.route("/eeg/alpha/combined", methods=["GET"])
def get_combined_alpha_timestamp():
    import pandas as pd
    import numpy as np

    df = pd.read_csv("data/raw10.csv")

    fs = 128          # Sampling rate (Hz)
    window_sec = 1    # 1 second window
    step_sec = 1      # 1 second step

    window_size = fs * window_sec
    step_size = fs * step_sec

    channels = ["Ch1", "Ch2", "Ch3", "Ch4"]
    alpha_values = []
    time_axis = []

    # 🔒 SAFE + STABLE Alpha Power
    def alpha_power(signal, fs):
        if len(signal) == 0:
            return 0.0

        # DC removal (VERY IMPORTANT)
        signal = signal - np.mean(signal)

        fft_vals = np.abs(np.fft.rfft(signal)) ** 2
        freqs = np.fft.rfftfreq(len(signal), 1/fs)

        alpha_band = (freqs >= 8) & (freqs <= 12)

        if not np.any(alpha_band):
            return 0.0

        power = np.mean(fft_vals[alpha_band])

        if np.isnan(power) or np.isinf(power):
            return 0.0

        # 🔑 Log scale to avoid huge spikes
        return float(np.log10(power + 1))

    # 🔹 Sliding window
    t = 0
    for i in range(0, len(df) - window_size, step_size):
        ch_alpha = []

        for ch in channels:
            window_signal = df[ch].values[i:i + window_size]
            ch_alpha.append(alpha_power(window_signal, fs))

        combined_alpha = np.mean(ch_alpha)

        if np.isnan(combined_alpha) or np.isinf(combined_alpha):
            combined_alpha = 0.0

        alpha_values.append(combined_alpha)
        time_axis.append(t)
        t += step_sec

    # 🔹 SAFE Moving Average
    def moving_average(arr, n=5):
        arr = np.array(arr, dtype=float)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

        if len(arr) < n:
            return arr

        return np.convolve(arr, np.ones(n)/n, mode='valid')

    smooth_alpha = moving_average(alpha_values, n=5)
    smooth_alpha = np.nan_to_num(smooth_alpha, nan=0.0, posinf=0.0, neginf=0.0)

    smooth_time = time_axis[:len(smooth_alpha)]

    return {
        "time": smooth_time,              # seconds
        "alpha": smooth_alpha.tolist()    # clean & scaled
    }

