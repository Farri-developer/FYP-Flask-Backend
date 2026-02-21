from flask import Blueprint, jsonify, request
from database.db import get_db_connection
import asyncio
from bleak import BleakClient
import os
import csv
from datetime import datetime

Bloodpresure_bp = Blueprint("Bloodpresure", __name__)

# 🔥 SAVE DIRECTLY INSIDE D:\Path
BASE_PATH = r"D:\Path"

BP_ADDRESS = "18:7A:93:12:26:AE"
BP_UUID = "00002a35-0000-1000-8000-00805f9b34fb"


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
@Bloodpresure_bp.route("/start_session_bp", methods=["POST"])
def start_session_bp():

    data = request.get_json()
    sid = data.get("sid")

    if not sid:
        return jsonify({"error": "sid is required"}), 400

    # =========================
    # READ BP
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
    # DATABASE FIRST
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
        # CREATE BASE FOLDER (if not exists)
        # =========================
        os.makedirs(BASE_PATH, exist_ok=True)

        # Folder name: sid&sessionid
        folder_name = f"{sid}&{session_id}"
        session_folder = os.path.join(BASE_PATH, folder_name)

        os.makedirs(session_folder, exist_ok=True)

        csv_path = os.path.join(session_folder, "bp.csv")

        # =========================
        # SAVE CSV
        # =========================
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
        # INSERT QuestionAttempt
        # =========================
        cursor.execute("""
            INSERT INTO QuestionAttempt (sessionid, sid, bppath)
            VALUES (?, ?, ?)
        """, (session_id, sid, csv_path))

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
        "sid": sid,
        "folder": folder_name,
        "bp_path": csv_path,
        "bp_values": result
    }), 200