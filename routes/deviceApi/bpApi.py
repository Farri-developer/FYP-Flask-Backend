from database.db import get_db_connection
import os, sys, csv, time, asyncio, threading, subprocess
from datetime import datetime
from flask import Blueprint, jsonify, request
from pylsl import StreamInlet, resolve_byprop
from bleak import BleakClient

devices_api = Blueprint("devices", __name__)

# =====================================================
# CONFIG
# =====================================================
BASE_PATH = r"D:\Path"
BP_ADDRESS = "18:7A:93:12:26:AE"
BP_UUID = "00002a35-0000-1000-8000-00805f9b34fb"

# =====================================================
# GLOBAL VARIABLES
# =====================================================
proc = None
eeg_inlet = None
ppg_inlet = None

recording = False
record_thread = None

current_session_id = None
current_question_attempt_id = None
current_session_folder = None

baseline_sys = None
baseline_dia = None
baseline_pulse = None
bp_csv_path = None
eeg_file_path = None
ppg_file_path = None


# =====================================================
# BP DECODER
# =====================================================
def decode_bp(data):
    flags = data[0]
    systolic  = int.from_bytes(data[1:3], "little")
    diastolic = int.from_bytes(data[3:5], "little")
    mean_art  = int.from_bytes(data[5:7], "little")
    idx = 7
    if flags & 0x02:
        idx += 7
    pulse = None
    if flags & 0x04:
        pulse = int.from_bytes(data[idx:idx+2], "little")
    return systolic, diastolic, mean_art, pulse


# =====================================================
# START STREAM
# URL: http://127.0.0.1:5000/api/devices/start_stream
# =====================================================

@devices_api.route("/start_stream", methods=["POST"])
def start_stream():

    global proc, eeg_inlet, ppg_inlet

    if proc:
        return jsonify({"status": "already running"}), 200

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "muselsl", "stream", "--ppg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(8)

        # 🔵 Resolve EEG
        eeg_streams = resolve_byprop("type", "EEG", timeout=10)
        if not eeg_streams:
            proc.terminate()
            proc = None
            return jsonify({"error": "EEG stream not found"}), 500

        # 🟢 Resolve PPG
        ppg_streams = resolve_byprop("type", "PPG", timeout=10)
        if not ppg_streams:
            proc.terminate()
            proc = None
            return jsonify({"error": "PPG stream not found"}), 500

        eeg_inlet = StreamInlet(eeg_streams[0])
        ppg_inlet = StreamInlet(ppg_streams[0])

        return jsonify({
            "status": "success",
            "message": "EEG & PPG connected"
        }), 200

    except Exception as e:
        if proc:
            proc.terminate()
            proc = None
        return jsonify({"error": str(e)}), 500

# =====================================================
# START SESSION + BASELINE BP
# URL: http://127.0.0.1:5000/api/devices/start_session_bp
# =====================================================
@devices_api.route("/start_session_bp", methods=["POST"])
def start_session_bp():

    global current_session_id, current_question_attempt_id
    global current_session_folder
    global baseline_sys, baseline_dia, baseline_pulse
    global bp_csv_path

    data = request.get_json()
    sid = data.get("sid")
    qid = data.get("qid")

    if not sid or not qid:
        return jsonify({"error": "sid and qid required"}), 400

    async def read_bp():
        async with BleakClient(BP_ADDRESS, timeout=20) as client:
            result = {}
            event = asyncio.Event()

            def handler(sender, data):
                nonlocal result
                sys_v, dia, map_v, pulse = decode_bp(data)
                result = {"SYS": sys_v, "DIA": dia, "PULSE": pulse}
                event.set()

            await client.start_notify(BP_UUID, handler)
            await asyncio.wait_for(event.wait(), timeout=60)
            await client.stop_notify(BP_UUID)
            return result

    result = asyncio.run(read_bp())

    baseline_sys = result["SYS"]
    baseline_dia = result["DIA"]
    baseline_pulse = result["PULSE"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert Session
    cursor.execute("""
        INSERT INTO Session (sid, starttime)
        OUTPUT INSERTED.sessionid
        VALUES (?, GETDATE())
    """, (sid,))
    current_session_id = cursor.fetchone()[0]

    # Create folder
    os.makedirs(BASE_PATH, exist_ok=True)
    folder_name = f"{sid}&{current_session_id}&{qid}"
    current_session_folder = os.path.join(BASE_PATH, folder_name)
    os.makedirs(current_session_folder, exist_ok=True)

    # Save BP CSV
    bp_csv_path = os.path.join(current_session_folder, "bp.csv")

    with open(bp_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time","label","SYS","DIA",
            "PULSE","DeltaSYS","DeltaDIA","DeltaPulse"
        ])
        writer.writerow([
            datetime.now().strftime("%H:%M:%S"),
            "Baseline",
            baseline_sys,
            baseline_dia,
            baseline_pulse,
            0,0,0
        ])

    # Insert QuestionAttempt
    cursor.execute("""
        INSERT INTO QuestionAttempt (sessionid, sid, qid, bppath)
        OUTPUT INSERTED.QuestionAttemptID
        VALUES (?, ?, ?, ?)
    """, (current_session_id, sid, qid, bp_csv_path))

    current_question_attempt_id = cursor.fetchone()[0]

    # Insert Reports baseline
    cursor.execute("""
        INSERT INTO Reports (sessionid, qid, sid, BaselineSYS, BaselineDIA)
        VALUES (?, ?, ?, ?, ?)
    """, (
        current_session_id,
        qid,
        sid,
        baseline_sys,
        baseline_dia
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "baseline saved"}), 200


# =====================================================
# START RECORDING
# URL: http://127.0.0.1:5000/api/devices/start_recording
# =====================================================
@devices_api.route("/start_recording", methods=["POST"])
def start_recording():

    global recording, record_thread
    global eeg_file_path, ppg_file_path

    if not current_session_folder:
        return jsonify({"error": "start session first"}), 400

    eeg_file_path = os.path.join(current_session_folder, "eeg.csv")
    ppg_file_path = os.path.join(current_session_folder, "ppg.csv")

    with open(eeg_file_path, "w", newline="") as f:
        csv.writer(f).writerow(["lsl_timestamp","EEG1","EEG2","EEG3","EEG4"])

    with open(ppg_file_path, "w", newline="") as f:
        csv.writer(f).writerow(["lsl_timestamp","PPG1","PPG2","PPG3"])

    recording = True

    def record_loop():
        with open(eeg_file_path, "a", newline="") as ef, \
             open(ppg_file_path, "a", newline="") as pf:

            ew = csv.writer(ef)
            pw = csv.writer(pf)

            while recording:
                e_sample, ts1 = eeg_inlet.pull_sample(timeout=0.0)
                if e_sample:
                    ew.writerow([ts1] + e_sample[:4])

                p_sample, ts2 = ppg_inlet.pull_sample(timeout=0.0)
                if p_sample:
                    pw.writerow([ts2] + p_sample[:3])

    record_thread = threading.Thread(target=record_loop)
    record_thread.daemon = True
    record_thread.start()

    return jsonify({"status": "recording started"}), 200


# =====================================================
# STOP RECORDING + SAVE ANSWER
# URL: http://127.0.0.1:5000/api/devices/stop_recording
# =====================================================
@devices_api.route("/stop_recording", methods=["POST"])
def stop_recording():

    global recording

    data = request.get_json()
    answer = data.get("answer")
    gptindex = data.get("gptindex")

    recording = False

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE QuestionAttempt
        SET eegpath=?, ppgpath=?, Answers=?, gptindex=?
        WHERE QuestionAttemptID=?
    """, (
        eeg_file_path,
        ppg_file_path,
        answer,
        gptindex,
        current_question_attempt_id
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "recording stopped & updated"}), 200


# =====================================================
# AFTER QUESTION BP
# URL: http://127.0.0.1:5000/api/devices/after_question_bp
# =====================================================
@devices_api.route("/after_question_bp", methods=["POST"])
def after_question_bp():

    global baseline_sys, baseline_dia, baseline_pulse

    async def read_bp():
        async with BleakClient(BP_ADDRESS, timeout=20) as client:
            result = {}
            event = asyncio.Event()

            def handler(sender, data):
                nonlocal result
                sys_v, dia, map_v, pulse = decode_bp(data)
                result = {"SYS": sys_v, "DIA": dia, "PULSE": pulse}
                event.set()

            await client.start_notify(BP_UUID, handler)
            await asyncio.wait_for(event.wait(), timeout=60)
            await client.stop_notify(BP_UUID)
            return result

    result = asyncio.run(read_bp())

    delta_sys = result["SYS"] - baseline_sys
    delta_dia = result["DIA"] - baseline_dia
    delta_pulse = result["PULSE"] - baseline_pulse

    # Append CSV
    with open(bp_csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%H:%M:%S"),
            "Question-End",
            result["SYS"],
            result["DIA"],
            result["PULSE"],
            delta_sys,
            delta_dia,
            delta_pulse
        ])

    # Update Reports
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Reports
        SET AfterQuestionSYS=?, AfterQuestionDIA=?
        WHERE sessionid=?
    """, (
        result["SYS"],
        result["DIA"],
        current_session_id
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "after question bp saved"}), 200


# =====================================================
# STOP STREAM
# URL: http://127.0.0.1:5000/api/devices/stop_stream
# =====================================================
@devices_api.route("/stop_stream", methods=["POST"])
def stop_stream():

    global proc, eeg_inlet, ppg_inlet

    if eeg_inlet:
        eeg_inlet.close_stream()
        eeg_inlet = None

    if ppg_inlet:
        ppg_inlet.close_stream()
        ppg_inlet = None

    if proc:
        proc.terminate()
        proc = None

    return jsonify({"status": "stream stopped"}), 200