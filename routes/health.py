from flask import Blueprint, jsonify, request
from database.db import get_db_connection
import asyncio
from bleak import BleakClient
import os
import csv
from datetime import datetime

health_bp = Blueprint("health", __name__)

# =========================
# CONFIG
# =========================
BASE_PATH = r"D:\Path"
BP_ADDRESS = "18:7A:93:12:26:AE"
BP_UUID = "00002a35-0000-1000-8000-00805f9b34fb"

# =========================
# BP Decode
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
# MAIN API
# =========================

@health_bp.route("/start_session_bp", methods=["POST"])
def start_session_bp():

    data = request.get_json()
    sid = data.get("sid")

    if not sid:
        return jsonify({"error": "sid is required"}), 400

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
                    event.set()   # 🔥 Signal received

                await client.start_notify(BP_UUID, handler)

                try:
                    # 🔥 Wait maximum 60 seconds for reading
                    await asyncio.wait_for(event.wait(), timeout=60)
                except asyncio.TimeoutError:
                    return {"error": "BP device timeout - no reading received"}

                await client.stop_notify(BP_UUID)

                return result

        except Exception as e:
            return {"error": f"Connection failed: {str(e)}"}

    result = asyncio.run(read_bp())

    if "error" in result:
        return jsonify(result), 500

    # =========================
    # SAVE CSV
    # =========================
    sid_folder = os.path.join(BASE_PATH, str(sid))
    os.makedirs(sid_folder, exist_ok=True)

    csv_path = os.path.join(sid_folder, "bp.csv")
    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["time","label","SYS","DIA","MAP","PULSE","DeltaSYS","DeltaDIA","DeltaPulse"])

        current_time = datetime.now().strftime("%H:%M:%S")

        writer.writerow([
            current_time,
            "Baseline",
            result["SYS"],
            result["DIA"],
            result["MAP"],
            result["PULSE"],
            0,0,0
        ])

    # =========================
    # SAVE DATABASE
    # =========================
    conn = get_db_connection()
    cursor = conn.cursor()

    start_time = datetime.now()

    cursor.execute("""
        INSERT INTO Session (sid, starttime, bppath)
        VALUES (?, ?, ?)
    """, (sid, start_time, csv_path))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "sid": sid,
        "bp_file": csv_path,
        "data": result
    }), 200