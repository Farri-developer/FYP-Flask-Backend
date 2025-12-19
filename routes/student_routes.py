from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import pyodbc

student_bp = Blueprint("student", __name__)

# ---------------- STUDENTS   ----------------

# GetStudent
@student_bp.route("/getall", methods=["GET"])
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




# GetStudent
@student_bp.route("/getbyid/<int:id>", methods=["GET"])
def GetStudentById(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sId, Regno, Name, semester,cgpa,gender,password FROM student where sid = ?", (id,))
    rows = cursor.fetchall()

    students = []
    for row in rows:
        students.append({
            "sId": row[0],
            "Regno": row[1],
            "Name": row[2],
            "semester": row[3],
            "cgpa": row[4],
            "gender": row[5],
            "password": row[6]
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


# ---------------- Delete Student  ----------------



@student_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("SELECT sid FROM Student WHERE sid = ?", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Student not found"}), 404


        cursor.execute("DELETE FROM Student WHERE sid = ?", (id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": f"Student {id} could not be deleted"}), 404

        return jsonify({"success": f"Student {id} deleted successfully"}), 200

    except pyodbc.IntegrityError as ie:
        # Foreign key constraint violation
        return jsonify({
            "error": "Cannot delete student. This student is referenced in another table (e.g., SQStats).",
            "details": str(ie)
        }), 400


    finally:
        conn.close()



# ----------- Get all Reports By Student ID -------------
@student_bp.route("/allreports/<int:sid>", methods=["GET"])
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
@student_bp.route("/reportstop5/<int:sid>", methods=["GET"])
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


#======================================]



def alpha_power(signal, fs):
    from scipy.signal import welch
    import numpy as np

    freqs, psd = welch(signal, fs=fs)
    idx = (freqs >= 8) & (freqs <= 13)

    return np.mean(psd[idx])

@student_bp.route("/eeg/alpha/combined", methods=["GET"])
def get_combined_alpha_timestamp():
    import pandas as pd
    import numpy as np

    # CSV read
    df = pd.read_csv("data/raw10.csv")

    fs = 128            # sampling rate
    window_sec = 1
    step_sec = 1

    window_size = fs * window_sec
    step_size = fs * step_sec

    time_axis = []
    alpha_values = []

    channels = ["Ch1", "Ch2", "Ch3", "Ch4"]  # match your CSV columns

    def alpha_power(signal, fs):
        # Simple example using FFT to get power in alpha band (8-12 Hz)
        freqs = np.fft.rfftfreq(len(signal), 1/fs)
        fft_vals = np.abs(np.fft.rfft(signal))**2
        alpha_band = (freqs >= 8) & (freqs <= 12)
        return np.mean(fft_vals[alpha_band])

    for i in range(0, len(df) - window_size, step_size):
        alpha_list = []
        for ch in channels:
            window_signal = df[ch].values[i:i + window_size]
            alpha_list.append(alpha_power(window_signal, fs))

        # 4 channels combine (average)
        combined_alpha = np.mean(alpha_list)

        # timestamp in seconds
        ts = i / fs
        time_axis.append(round(ts, 3))
        alpha_values.append(round(combined_alpha, 4))

    return {
        "time": time_axis,
        "alpha": alpha_values
    }
