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
# GLOBAL STATE
# =====================================================
proc = None
eeg_inlet = None
ppg_inlet = None

recording = False
record_thread = None

question_start_time = None

current_session_id = None
current_question_attempt_id = None
current_session_folder = None

baseline_sys = None
baseline_dia = None
baseline_pulse = None
baseline_time = None

bp_csv_path = None
eeg_file_path = None
ppg_file_path = None


# =====================================================
# BP READER (COMMON)
# =====================================================
def decode_bp(data):
    flags = data[0]
    systolic = int.from_bytes(data[1:3], "little")
    diastolic = int.from_bytes(data[3:5], "little")
    mean_art = int.from_bytes(data[5:7], "little")
    idx = 7
    if flags & 0x02:
        idx += 7
    pulse = None
    if flags & 0x04:
        pulse = int.from_bytes(data[idx:idx + 2], "little")
    return systolic, diastolic, mean_art, pulse


async def async_read_bp():
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


def read_bp():
    return asyncio.run(async_read_bp())


# =====================================================
# START STREAM
# =====================================================
@devices_api.route("/start_stream", methods=["POST"])
def start_stream():
    global proc, eeg_inlet, ppg_inlet

    if eeg_inlet and ppg_inlet:
        return jsonify({"status": "already running"}), 200

    proc = subprocess.Popen(
        [sys.executable, "-m", "muselsl", "stream", "--ppg"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(8)

    eeg_streams = resolve_byprop("type", "EEG", timeout=10)
    ppg_streams = resolve_byprop("type", "PPG", timeout=10)

    if not eeg_streams or not ppg_streams:
        return jsonify({"error": "EEG/PPG stream not found"}), 500

    eeg_inlet = StreamInlet(eeg_streams[0])
    ppg_inlet = StreamInlet(ppg_streams[0])

    return jsonify({"status": "stream started"}), 200


# =====================================================
# START SESSION + BASELINE
# =====================================================
@devices_api.route("/start_session_bp", methods=["POST"])
def start_session_bp():
    global baseline_sys, baseline_dia, baseline_pulse, baseline_time

    # Read baseline only
    try:
        result = read_bp()
    except Exception as e:
        return jsonify({"error": f"BP device error: {str(e)}"}), 500

    baseline_sys = result["SYS"]
    baseline_dia = result["DIA"]
    baseline_pulse = result["PULSE"]
    baseline_time = datetime.now()

    return jsonify({
        "status": "baseline captured",
        "SYS": baseline_sys,
        "DIA": baseline_dia,
        "PULSE": baseline_pulse
    }), 200


# =====================================================
# START RECORDING (FIRST QUESTION ONLY)
# =====================================================

@devices_api.route("/start_recording", methods=["POST"])
def start_recording():
    global recording, record_thread
    global eeg_file_path, ppg_file_path, bp_csv_path
    global current_question_attempt_id
    global current_session_folder
    global question_start_time
    global baseline_sys, baseline_dia, baseline_pulse, baseline_time
    global current_session_id

    data = request.get_json()
    sid = data.get("sid")
    qid = data.get("qid")

    if not sid or not qid:
        return jsonify({"error": "sid and qid required"}), 400

    # 🔴 Baseline check
    if baseline_sys is None:
        return jsonify({"error": "Baseline not captured"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create session only first time
    if current_session_id is None:
        cursor.execute("""
            INSERT INTO Session (sid, starttime)
            OUTPUT INSERTED.sessionid
            VALUES (?, GETDATE())
        """, (sid,))
        current_session_id = cursor.fetchone()[0]

    # ==========================================
    # CREATE QUESTION FOLDER
    # ==========================================
    current_session_folder = os.path.join(
        BASE_PATH,
        f"{sid}&{current_session_id}&{qid}"
    )
    os.makedirs(current_session_folder, exist_ok=True)

    # ==========================================
    # CREATE BP FILE
    # ==========================================
    bp_csv_path = os.path.join(current_session_folder, "bp.csv")

    with open(bp_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time", "label", "SYS", "DIA", "PULSE",
            "DeltaSYS", "DeltaDIA", "DeltaPulse"
        ])
        writer.writerow([
            baseline_time.strftime("%H:%M:%S") if baseline_time else "",
            "Baseline",
            baseline_sys,
            baseline_dia,
            baseline_pulse,
            0, 0, 0
        ])

    # ==========================================
    # CREATE EEG + PPG FILES
    # ==========================================
    eeg_file_path = os.path.join(current_session_folder, "eeg.csv")
    ppg_file_path = os.path.join(current_session_folder, "ppg.csv")

    with open(eeg_file_path, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "EEG1", "EEG2", "EEG3", "EEG4"])

    with open(ppg_file_path, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "PPG1", "PPG2", "PPG3"])

    # ==========================================
    # INSERT QUESTION ATTEMPT
    # ==========================================
    cursor.execute("""
        INSERT INTO QuestionAttempt 
        (sessionid, sid, qid, bppath, eegpath, ppgpath)
        OUTPUT INSERTED.QuestionAttemptID
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        current_session_id,
        sid,
        qid,
        bp_csv_path,
        eeg_file_path,
        ppg_file_path
    ))

    current_question_attempt_id = cursor.fetchone()[0]

    # ==========================================
    # INSERT REPORT (Baseline saved here only)
    # ==========================================
    cursor.execute("""
        INSERT INTO Reports
        (sessionid, QuestionAttemptID, qid, sid, BaselineSYS, BaselineDIA)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        current_session_id,
        current_question_attempt_id,
        qid,
        sid,
        baseline_sys,
        baseline_dia
    ))

    # # ==========================================
    # # increment question count
    # # ==========================================
    # cursor.execute("""
    #        UPDATE Question
    #        SET count = 3
    #        WHERE qid = ? ;
    #    """, (
    #     qid,
    #
    # ))

    conn.commit()
    conn.close()

    # ==========================================
    # START RECORDING THREAD
    # ==========================================
    question_start_time = datetime.now()
    recording = True

    def record_loop():
        global recording
        with open(eeg_file_path, "a", newline="") as ef, \
                open(ppg_file_path, "a", newline="") as pf:

            ew = csv.writer(ef)
            pw = csv.writer(pf)

            while recording:
                try:
                    if eeg_inlet:
                        e_sample, ts1 = eeg_inlet.pull_sample(timeout=0.0)
                        if e_sample:
                            ew.writerow([ts1] + e_sample[:4])

                    if ppg_inlet:
                        p_sample, ts2 = ppg_inlet.pull_sample(timeout=0.0)
                        if p_sample:
                            pw.writerow([ts2] + p_sample[:3])
                except:
                    pass

    record_thread = threading.Thread(target=record_loop, daemon=True)
    record_thread.start()

    return jsonify({
        "status": "recording started",
        "sessionid": current_session_id,
        "QuestionAttemptID": current_question_attempt_id
    }), 200


# =====================================================
# STOP RECORDING (COMMON)
# =====================================================
@devices_api.route("/stop_recording", methods=["POST"])
@devices_api.route("/stop_recording_question", methods=["POST"])
def stop_recording_common():
    global recording, record_thread

    data = request.get_json()

    answers = data.get("answers") or data.get("answer")
    gptindex = data.get("gptindex")

    recording = False

    if record_thread:
        record_thread.join()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE QuestionAttempt
        SET Answers=?, gptindex=?
        WHERE QuestionAttemptID=?
    """, (
        answers,
        gptindex,
        current_question_attempt_id
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "recording stopped"}), 200


# =====================================================
# AFTER QUESTION BP
# =====================================================

@devices_api.route("/after_question_bp", methods=["POST"])
def after_question_bp():
    global question_start_time
    global current_question_attempt_id
    global baseline_sys, baseline_dia, baseline_pulse, baseline_time
    global bp_csv_path

    if not current_question_attempt_id:
        return jsonify({"error": "No active question"}), 400

    try:
        result = read_bp()
    except Exception as e:
        return jsonify({"error": f"BP read failed: {str(e)}"}), 500

    after_sys = result["SYS"]
    after_dia = result["DIA"]
    after_pulse = result["PULSE"]

    after_time = datetime.now()

    time_taken = int((after_time - question_start_time).total_seconds())

    # ==========================================
    # CALCULATE DELTA
    # ==========================================
    delta_sys = after_sys - baseline_sys
    delta_dia = after_dia - baseline_dia
    delta_pulse = after_pulse - baseline_pulse

    # ==========================================
    # APPEND TO BP FILE
    # ==========================================
    with open(bp_csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            after_time.strftime("%H:%M:%S"),
            "Question-End",
            after_sys,
            after_dia,
            after_pulse,
            delta_sys,
            delta_dia,
            delta_pulse
        ])

    # ==========================================
    # UPDATE DATABASE
    # ==========================================
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Reports
        SET AfterQuestionSYS=?,
            AfterQuestionDIA=?,
            TimeTaken=?
        WHERE QuestionAttemptID=?
    """, (
        after_sys,
        after_dia,
        time_taken,
        current_question_attempt_id
    ))

    conn.commit()
    conn.close()

    # ==========================================
    # UPDATE GLOBAL BASELINE FOR NEXT QUESTION
    # ==========================================
    baseline_sys = after_sys
    baseline_dia = after_dia
    baseline_pulse = after_pulse
    baseline_time = after_time

    current_question_attempt_id = None

    return jsonify({
        "status": "after question saved",
        "SYS": after_sys,
        "DIA": after_dia,
        "PULSE": after_pulse,
        "DeltaSYS": delta_sys,
        "DeltaDIA": delta_dia,
        "DeltaPulse": delta_pulse,
        "TimeTaken": time_taken
    }), 200


# =====================================================
# STOP STREAM + END SESSION (SAFE VERSION)
# =====================================================

@devices_api.route("/stop_stream", methods=["POST"])
def stop_stream():
    global proc, eeg_inlet, ppg_inlet
    global current_session_id
    global recording, record_thread
    global question_start_time

    # ===============================
    # STOP RECORDING IF STILL RUNNING
    # ===============================
    recording = False

    if record_thread:
        record_thread.join(timeout=2)
        record_thread = None

    # ===============================
    # CLOSE LSL STREAMS SAFELY
    # ===============================
    try:
        if eeg_inlet:
            eeg_inlet.close_stream()
            eeg_inlet = None
    except:
        pass

    try:
        if ppg_inlet:
            ppg_inlet.close_stream()
            ppg_inlet = None
    except:
        pass

    # ===============================
    # TERMINATE MUSE PROCESS
    # ===============================
    try:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            proc = None
    except:
        pass

    # ===============================
    # UPDATE SESSION END TIME
    # ===============================
    if current_session_id:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Session
            SET endtime = ?
            WHERE sessionid = ?
        """, (datetime.now(), current_session_id))

        conn.commit()
        conn.close()

    # ===============================
    # RESET SESSION VARIABLES
    # ===============================

    current_question_attempt_id = None
    baseline_sys = None
    baseline_dia = None
    baseline_pulse = None

    return jsonify({
        "status": "stream stopped and session ended"
    }), 200


# =====================================================
# SELF REPORT (USING GLOBAL SESSION)
# =====================================================
@devices_api.route("/selfreport", methods=["POST"])
def selfreport():
    global current_session_id

    if current_session_id is None:
        return jsonify({"error": "No active session"}), 400

    data = request.get_json()

    mental_load = data.get("MentalLoad")
    frustration = data.get("Frustration")
    effort = data.get("Effort")
    comment = data.get("Comment")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Session
        SET MentalLoad = ?,
            Frustration = ?,
            Effort = ?,
            Comment = ?
        WHERE sessionid = ?
    """, (
        mental_load,
        frustration,
        effort,
        comment,
        current_session_id
    ))

    conn.commit()
    conn.close()

    # ✅ Save session id before resetting
    saved_session_id = current_session_id

    # ✅ Now reset session
    current_session_id = None

    return jsonify({
        "status": "self report saved",
        "sessionid": saved_session_id
    }), 200


# =====================================================
# RESET ALL GLOBAL VARIABLES (FORCE CLEAN)
# =====================================================

@devices_api.route("/reset_all", methods=["POST"])
def reset_all():
    global proc, eeg_inlet, ppg_inlet
    global recording, record_thread
    global question_start_time
    global current_session_id
    global current_question_attempt_id
    global current_session_folder
    global baseline_sys, baseline_dia, baseline_pulse, baseline_time
    global bp_csv_path, eeg_file_path, ppg_file_path

    try:
        # ===============================
        # STOP RECORDING THREAD
        # ===============================
        recording = False
        if record_thread:
            record_thread.join(timeout=2)
            record_thread = None

        # ===============================
        # CLOSE STREAMS
        # ===============================
        try:
            if eeg_inlet:
                eeg_inlet.close_stream()
        except:
            pass

        try:
            if ppg_inlet:
                ppg_inlet.close_stream()
        except:
            pass

        eeg_inlet = None
        ppg_inlet = None

        # ===============================
        # STOP PROCESS
        # ===============================
        try:
            if proc:
                proc.terminate()
                proc.wait(timeout=5)
        except:
            pass

        proc = None

        # ===============================
        # RESET ALL VARIABLES
        # ===============================
        question_start_time = None
        current_session_id = None
        current_question_attempt_id = None
        current_session_folder = None

        baseline_sys = None
        baseline_dia = None
        baseline_pulse = None
        baseline_time = None

        bp_csv_path = None
        eeg_file_path = None
        ppg_file_path = None

        return jsonify({
            "status": "All globals reset successfully"
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
