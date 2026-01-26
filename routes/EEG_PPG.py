import os, sys, csv, time, asyncio, threading, traceback,subprocess
from datetime import datetime
from flask import Blueprint, jsonify, request
from pylsl import StreamInlet, resolve_byprop
from bleak import BleakClient

# =========================
# CONFIG & GLOBAL STATE
# =========================
health_api = Blueprint("health_api", __name__)

# Base path
BASE_DIR = r"D:\DataSet"
os.makedirs(BASE_DIR, exist_ok=True)

# BP Device
BP_ADDRESS = "18:7A:93:12:26:AE"
BP_UUID = "00002a35-0000-1000-8000-00805f9b34fb"

# Stream & Recording
proc = None
eeg_inlet = None
ppg_inlet = None
recording = False
worker_thread = None

# Session
session_id = "1"
name = "User"
folder = os.path.join(BASE_DIR, f"Session_{session_id}_{name}")
os.makedirs(folder, exist_ok=True)
eeg_file = os.path.join(folder, "eeg_ppg_raw.csv")
bp_file  = os.path.join(folder, "Question_Data_bp.csv")

# Create headers if not exist
for file, header in [
    (eeg_file, ["time","EEG1","EEG2","EEG3","EEG4","PPG1","PPG2","PPG3","PPG4"]),
    (bp_file,  ["time","label","SYS","DIA","MAP","PULSE","DeltaSYS","DeltaDIA","DeltaPulse"])
]:
    if not os.path.exists(file):
        with open(file,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(header)

# Baseline BP
base_bp = None

# =========================
# BP DECODER
# =========================
def decode_bp(data):
    flags = data[0]
    systolic  = int.from_bytes(data[1:3], "little")
    diastolic = int.from_bytes(data[3:5], "little")
    mean_art  = int.from_bytes(data[5:7], "little")
    idx = 7
    if flags & 0x02: idx += 7
    pulse = int.from_bytes(data[idx:idx+2], "little") if flags & 0x04 else None
    if mean_art == 0:
        mean_art = round(diastolic + (systolic - diastolic)/3,1)
    return systolic, diastolic, mean_art, pulse

# =========================
# BP WORKER
# =========================
async def measure_bp():
    try:
        async with BleakClient(BP_ADDRESS, timeout=12) as client:
            got = False
            result = {}
            def handler(_, data):
                nonlocal got, result
                if not got:
                    got = True
                    result["sys"], result["dia"], result["map"], result["pulse"] = decode_bp(data)
            await client.start_notify(BP_UUID, handler)
            for _ in range(45):
                if got: break
                await asyncio.sleep(1)
            await client.stop_notify(BP_UUID)
            return result
    except Exception as e:
        return {"error": str(e)}

# =========================
# RECORDING LOOP
# =========================
def record_loop():
    global recording
    while recording:
        ts = int(time.time())
        try:
            if eeg_inlet:
                s,_ = eeg_inlet.pull_sample(timeout=0.0)
                if s:
                    with open(eeg_file,"a",newline="",encoding="utf-8") as f:
                        csv.writer(f).writerow([ts]+s)
            if ppg_inlet:
                s,_ = ppg_inlet.pull_sample(timeout=0.0)
                if s:
                    with open(eeg_file,"a",newline="",encoding="utf-8") as f:
                        csv.writer(f).writerow([ts]+[0]*4+s)  # PPG appended
        except Exception as e:
            print(f"Recording Error: {e}")
        time.sleep(0.01)

# =========================
# 01 API: START STREAM
# =========================
@health_api.route("/start_stream", methods=["POST"])
def start_stream():
    global proc, eeg_inlet, ppg_inlet, folder, eeg_file, bp_file, session_id, name

    if proc:
        return jsonify({"status":"stream already running"})

    try:
        data = request.get_json() or {}
        session_id = str(data.get("session_id", session_id))
        name = str(data.get("name", name)).replace(" ","_")
        folder = os.path.join(BASE_DIR, f"Session_{session_id}_{name}")
        os.makedirs(folder, exist_ok=True)

        eeg_file = os.path.join(folder, "eeg_ppg_raw.csv")
        bp_file  = os.path.join(folder, "Question_Data_bp.csv")
        for file, header in [
            (eeg_file, ["time","EEG1","EEG2","EEG3","EEG4","PPG1","PPG2","PPG3","PPG4"]),
            (bp_file,  ["time","label","SYS","DIA","MAP","PULSE","DeltaSYS","DeltaDIA","DeltaPulse"])
        ]:
            if not os.path.exists(file):
                with open(file,"w",newline="",encoding="utf-8") as f:
                    csv.writer(f).writerow(header)

        proc = subprocess.Popen([sys.executable,"-m","muselsl","stream","--ppg"])
        time.sleep(5)
        eeg = resolve_byprop("type","EEG",timeout=10)
        ppg = resolve_byprop("type","PPG",timeout=10)
        if not eeg or not ppg:
            return jsonify({"error":"EEG/PPG stream not found"}), 500
        eeg_inlet = StreamInlet(eeg[0])
        ppg_inlet = StreamInlet(ppg[0])
        return jsonify({"status":"stream started"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}), 500

# =========================
# 02 API: START RECORDING
# =========================
@health_api.route("/start_recording", methods=["POST"])
def start_recording():
    global recording, worker_thread
    if recording:
        return jsonify({"status":"already recording"})
    recording = True
    worker_thread = threading.Thread(target=record_loop, daemon=True)
    worker_thread.start()
    return jsonify({"status":"recording started"})

# =========================
# 03 API: STOP RECORDING
# =========================
@health_api.route("/stop_recording", methods=["POST"])
def stop_recording():
    global recording
    recording = False
    return jsonify({"status":"recording stopped"})

# =========================
# 04 API: STOP STREAM
# =========================
@health_api.route("/stop_stream", methods=["POST"])
def stop_stream():
    global proc, eeg_inlet, ppg_inlet, recording
    recording = False
    if proc:
        proc.terminate()
        proc = None
    eeg_inlet = None
    ppg_inlet = None
    return jsonify({"status":"stream stopped"})

# =========================
# 05 API: BASELINE BP
# =========================
@health_api.route("/baseline_bp", methods=["POST"])
def baseline_bp():
    global base_bp, bp_file
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(measure_bp())
    loop.close()
    if "error" in result:
        return jsonify(result), 500
    base_bp = (result["sys"], result["dia"], result["pulse"])
    t = datetime.now().strftime("%H:%M:%S")
    with open(bp_file,"a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow([t,"Baseline",result["sys"],result["dia"],result["map"],result["pulse"],0,0,0])
    return jsonify({"status":"baseline saved","data":result})

# =========================
# 06 API: QUESTION-END BP
# =========================
@health_api.route("/question_bp", methods=["POST"])
def question_bp():
    global base_bp, bp_file
    if not base_bp:
        return jsonify({"error":"baseline BP not measured"}), 400
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(measure_bp())
    loop.close()
    if "error" in result:
        return jsonify(result), 500
    delta_sys = result["sys"] - base_bp[0]
    delta_dia = result["dia"] - base_bp[1]
    delta_pulse = result["pulse"] - base_bp[2]
    t = datetime.now().strftime("%H:%M:%S")
    with open(bp_file,"a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow([t,"Question-End",result["sys"],result["dia"],result["map"],result["pulse"],
                                delta_sys,delta_dia,delta_pulse])
    return jsonify({"status":"question BP saved","data":result,
                    "delta":{"sys":delta_sys,"dia":delta_dia,"pulse":delta_pulse}})

# =========================
# 07 API: STATUS
# =========================
@health_api.route("/status", methods=["GET"])
def status():
    global proc, recording, base_bp
    return jsonify({
        "stream": "ON" if proc else "OFF",
        "recording": "ON" if recording else "OFF",
        "baseline_bp": base_bp is not None
    })
