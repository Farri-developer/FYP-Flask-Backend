from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from scipy.signal import welch
import os
from database.db import get_db_connection

eeg_api = Blueprint("eeg_api", __name__)

# ==========================
# Optimized Settings
# ==========================

FS = 256
WINDOW_SEC = 4      # smoother
STEP_SEC = 2        # 50% overlap

WINDOW_SIZE = FS * WINDOW_SEC
STEP_SIZE = FS * STEP_SEC


# ==========================
# Band Power
# ==========================

def band_power(signal, band):
    signal = signal - np.mean(signal)
    freqs, psd = welch(signal, FS, nperseg=FS)

    idx = (freqs >= band[0]) & (freqs <= band[1])
    if not np.any(idx):
        return 0.0

    power = np.trapz(psd[idx], freqs[idx])
    return float(np.log10(power + 1))


def moving_average(arr, n=5):   # stronger smoothing
    if len(arr) < n:
        return arr
    return np.convolve(arr, np.ones(n)/n, mode='same')


# ==========================
# Load Files
# ==========================

def load_eeg_files(sessionid, sid):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT eegpath 
        FROM QuestionAttempt
        WHERE sessionid = ? AND sid = ?
        ORDER BY QuestionAttemptID
    """, (sessionid, sid))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None, None

    dataframes = []
    file_info = []

    for row in rows:
        path = row[0]

        if not path or not os.path.exists(path):
            continue

        df = pd.read_csv(path)

        file_info.append({
            "path": path,
            "rows": len(df)
        })

        dataframes.append(df)

    if not dataframes:
        return None, None

    combined_df = pd.concat(dataframes, ignore_index=True)

    return combined_df, file_info




# load_single_question_file
def load_single_question_file(sessionid, sid, qid):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT eegpath
        FROM QuestionAttempt
        WHERE sessionid = ? AND sid = ? AND qid = ?
    """, (sessionid, sid, qid))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, None

    path = row[0]

    if not path or not os.path.exists(path):
        return None, None

    df = pd.read_csv(path)

    return df, path


# ==========================
# Compute Bands
# ==========================

# compute_all_bands

def compute_all_bands(df):

    channels = ["EEG1", "EEG2", "EEG3", "EEG4"]

    bands_def = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 45)
    }

    result = {key: [] for key in bands_def.keys()}
    time_axis = []

    t = 0
    for start in range(0, len(df) - WINDOW_SIZE + 1, STEP_SIZE):

        window_data = df.iloc[start:start + WINDOW_SIZE]
        band_values = {key: [] for key in bands_def.keys()}

        for ch in channels:
            if ch not in window_data.columns:
                continue

            signal = window_data[ch].values

            for band_name, band_range in bands_def.items():
                band_values[band_name].append(
                    band_power(signal, band_range)
                )

        for band_name in bands_def.keys():
            if band_values[band_name]:
                result[band_name].append(
                    float(np.mean(band_values[band_name]))
                )
            else:
                result[band_name].append(0.0)

        time_axis.append(t)
        t += STEP_SEC

    # Smooth for frontend
    for band_name in result.keys():
        result[band_name] = moving_average(result[band_name], 5).tolist()

    return time_axis, result


def compute_single_band(df, band_range):

    channels = ["EEG1", "EEG2", "EEG3", "EEG4"]

    band_values = []
    time_axis = []

    t = 0
    for start in range(0, len(df) - WINDOW_SIZE + 1, STEP_SIZE):

        window_data = df.iloc[start:start + WINDOW_SIZE]
        ch_values = []

        for ch in channels:
            if ch not in window_data.columns:
                continue

            signal = window_data[ch].values
            ch_values.append(band_power(signal, band_range))

        if ch_values:
            band_values.append(float(np.mean(ch_values)))
        else:
            band_values.append(0.0)

        time_axis.append(t)
        t += STEP_SEC

    band_values = moving_average(band_values, 5).tolist()

    return time_axis, band_values


# ==========================
# FINAL ALL API
# ==========================

@eeg_api.route("/all", methods=["GET"])
def eeg_all():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")

    if not sessionid or not sid:
        return jsonify({"error": "sessionid and sid required"}), 400

    df, file_info = load_eeg_files(sessionid, sid)

    if df is None:
        return jsonify({"error": "No EEG files found"}), 404

    time_axis, bands = compute_all_bands(df)

    response = {
        "sessionid": str(sessionid),
        "sid": str(sid),

        "total_files": len(file_info),
        "files": file_info,
        "combined_total_rows": int(len(df)),

        "time": time_axis,
        "delta": bands["delta"],
        "theta": bands["theta"],
        "alpha": bands["alpha"],
        "beta": bands["beta"],
        "gamma": bands["gamma"]
    }

    return jsonify(response)


# delta

@eeg_api.route("/delta", methods=["GET"])
def eeg_delta():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_question_file(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "EEG file not found"}), 404

    time_axis, values = compute_single_band(df, (0.5, 4))

    return jsonify({
        "band": "delta",
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {"path": path, "rows": len(df)},
        "time": time_axis,
        "delta": values
    })




# theta
@eeg_api.route("/theta", methods=["GET"])
def eeg_theta():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_question_file(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "EEG file not found"}), 404

    time_axis, values = compute_single_band(df, (4, 8))

    return jsonify({
        "band": "theta",
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {"path": path, "rows": len(df)},
        "time": time_axis,
        "theta": values
    })


# alpha
@eeg_api.route("/alpha", methods=["GET"])
def eeg_alpha():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_question_file(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "EEG file not found"}), 404

    time_axis, values = compute_single_band(df, (8, 13))

    return jsonify({
        "band": "alpha",
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {"path": path, "rows": len(df)},
        "time": time_axis,
        "alpha": values
    })


# beta
@eeg_api.route("/beta", methods=["GET"])
def eeg_beta():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_question_file(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "EEG file not found"}), 404

    time_axis, values = compute_single_band(df, (13, 30))

    return jsonify({
        "band": "beta",
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {"path": path, "rows": len(df)},
        "time": time_axis,
        "beta": values
    })

# gamma
@eeg_api.route("/gamma", methods=["GET"])
def eeg_gamma():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_question_file(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "EEG file not found"}), 404

    time_axis, values = compute_single_band(df, (30, 45))

    return jsonify({
        "band": "gamma",
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {"path": path, "rows": len(df)},
        "time": time_axis,
        "gamma": values
    })