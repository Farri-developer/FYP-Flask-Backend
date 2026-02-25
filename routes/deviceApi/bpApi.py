
from database.db import get_db_connection

import os, sys, csv, time, asyncio, threading, traceback,subprocess
from datetime import datetime
from flask import Blueprint, jsonify, request
from pylsl import StreamInlet, resolve_byprop
from bleak import BleakClient

import signal




devices_api = Blueprint("devices", __name__)

# 🔥 SAVE DIRECTLY INSIDE D:\Path
BASE_PATH = r"D:\Path"

BP_ADDRESS = "18:7A:93:12:26:AE"
BP_UUID = "00002a35-0000-1000-8000-00805f9b34fb"


# =========================
# GLOBAL STREAM VARIABLES
# =========================
proc = None
eeg_inlet = None
ppg_inlet = None
folder = None


# =========================
# Decode BP
# =========================
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


# =========================
# API
# =========================

@devices_api.route("/start_session_bp", methods=["POST"])
def start_session_bp():

    data = request.get_json()
    sid = data.get("sid")
    qid = data.get("qid")   # ✅ NEW

    if not sid or not qid:
        return jsonify({"error": "sid and qid are required"}), 400

    # =========================
    # READ BP (Same as before)
    # =========================
    async def read_bp():
        try:
            async with BleakClient(BP_ADDRESS, timeout=20) as client:

                if not client.is_connected:
                    return {"error": "Device not connected"}

                result = {}
                event = asyncio.Event()

                def handler(sender, data):
                    nonlocal result
                    sys, dia, map_val, pulse = decode_bp(data)
                    result = {
                        "SYS": sys,
                        "DIA": dia,
                        "MAP": map_val,
                        "PULSE": pulse
                    }
                    event.set()

                await client.start_notify(BP_UUID, handler)
                await asyncio.wait_for(event.wait(), timeout=60)
                await client.stop_notify(BP_UUID)

                return result

        except Exception as e:
            return {"error": str(e)}

    result = asyncio.run(read_bp())

    if "error" in result:
        return jsonify(result), 500


    # =========================
    # DATABASE
    # =========================
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1️⃣ Insert Session
        cursor.execute("""
            INSERT INTO Session (sid, starttime)
            OUTPUT INSERTED.sessionid
            VALUES (?, GETDATE())
        """, (sid,))

        row = cursor.fetchone()

        if row is None:
            raise Exception("Session ID not generated")

        session_id = int(row[0])

        # =========================
        # Folder Creation
        # =========================
        os.makedirs(BASE_PATH, exist_ok=True)

        # Folder name: sid&sessionid&qid
        folder_name = f"{sid}&{session_id}&{qid}"
        session_folder = os.path.join(BASE_PATH, folder_name)

        os.makedirs(session_folder, exist_ok=True)



        csv_path = os.path.join(session_folder, "bp.csv")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time","SYS","DIA","MAP","PULSE"])
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                result["SYS"],
                result["DIA"],
                result["MAP"],
                result["PULSE"]
            ])

        # =========================
        # 2️⃣ Insert QuestionAttempt WITH QID
        # =========================
        cursor.execute("""
            INSERT INTO QuestionAttempt (sessionid, sid, qid, bppath)
            VALUES (?, ?, ?, ?)
        """, (session_id, sid, qid, csv_path))


        # =========================
        # 3️⃣ Insert Reports TABLE
        # =========================
        cursor.execute("""
            INSERT INTO Reports 
            (sessionid, qid, sid, BaselineSYS, BaselineDIA)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            qid,
            sid,
            result["SYS"],   # Baseline SYS
            result["DIA"]    # Baseline DIA
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 500

    conn.close()

    # =========================
    # RESPONSE
    # =========================
    return jsonify({
        "status": "success",
        "sessionid": session_id,
        "qid": qid,
        "sid": sid,
        "bp_values": result
    }), 200



@devices_api.route("/start_stream", methods=["POST"])
def start_stream():
    global proc, eeg_inlet, ppg_inlet, folder

    if proc:
        return jsonify({"status": "stream already running"}), 200

    try:
        # =========================
        # Start Muse Stream
        # =========================
        proc = subprocess.Popen(
            [sys.executable, "-m", "muselsl", "stream", "--ppg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(6)

        # =========================
        # Resolve EEG
        # =========================
        eeg_streams = resolve_byprop("type", "EEG", timeout=10)
        ppg_streams = resolve_byprop("type", "PPG", timeout=10)

        if not eeg_streams:
            proc.terminate()
            proc = None
            return jsonify({"error": "EEG device not found"}), 500

        if not ppg_streams:
            proc.terminate()
            proc = None
            return jsonify({"error": "PPG device not found"}), 500

        # =========================
        # Create Inlets
        # =========================
        eeg_inlet = StreamInlet(eeg_streams[0])
        ppg_inlet = StreamInlet(ppg_streams[0])

        return jsonify({
            "status": "ok",
            "message": "EEG & PPG stream connected successfully"
        }), 200

    except Exception as e:
        if proc:
            proc.terminate()
            proc = None
        return jsonify({"error": str(e)}), 500



@devices_api.route("/stop_stream", methods=["POST"])
def stop_stream():
    global proc, eeg_inlet, ppg_inlet

    try:

        # =========================
        # Close LSL Inlets
        # =========================
        if eeg_inlet:
            try:
                eeg_inlet.close_stream()
            except:
                pass
            eeg_inlet = None

        if ppg_inlet:
            try:
                ppg_inlet.close_stream()
            except:
                pass
            ppg_inlet = None

        # =========================
        # Force Kill MuseLSL Stream (🔥 MOST IMPORTANT PART)
        # =========================

        os.system("taskkill /f /im python.exe")
        os.system("taskkill /f /im muselsl.exe")

        proc = None

        return jsonify({
            "status": "success",
            "message": "Stream forcefully stopped"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500