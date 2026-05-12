from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from scipy.signal import welch
import os
from database.db import get_db_connection
import numpy as np
from scipy.signal import find_peaks

eeg_api = Blueprint("eeg_api", __name__)

# ==========================
# Optimized Settings
#  Show the graph
# ==========================

# BP REPORT API

# ==========================
# EEG Settings
# ==========================
EEG_FS = 256
EEG_WINDOW_SEC = 4
EEG_STEP_SEC = 2
EEG_WINDOW_SIZE = EEG_FS * EEG_WINDOW_SEC   # 1024
EEG_STEP_SIZE = EEG_FS * EEG_STEP_SEC       # 512

# =========================
# PPG Settings
# ==========================
PPG_FS = 63
PPG_WINDOW_SEC = 10
PPG_STEP_SEC = 5
PPG_WINDOW_SIZE = PPG_FS * PPG_WINDOW_SEC   # 940
PPG_STEP_SIZE = PPG_FS * PPG_STEP_SEC       # 470





# ppg fuction



def load_single_ppg(sessionid, sid, qid):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ppgpath
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


def compute_single_ppg(df):

    channels = ["PPG1", "PPG2", "PPG3"]

    ch_hr, ch_sdnn, ch_rmssd, ch_pnn50 = [], [], [], []

    for ch in channels:
        if ch not in df.columns:
            continue

        signal = df[ch].values

        hr, sdnn, rmssd, pnn50 = compute_ppg_features(signal)

        ch_hr.append(hr)
        ch_sdnn.append(sdnn)
        ch_rmssd.append(rmssd)
        ch_pnn50.append(pnn50)

    return {
        "HR": float(np.mean(ch_hr)) if ch_hr else 0,
        "SDNN": float(np.mean(ch_sdnn)) if ch_sdnn else 0,
        "RMSSD": float(np.mean(ch_rmssd)) if ch_rmssd else 0,
        "pNN50": float(np.mean(ch_pnn50)) if ch_pnn50 else 0
    }


def compute_ppg_features(signal):

    signal = signal - np.mean(signal)

    peaks, _ = find_peaks(signal, distance=PPG_FS * 0.5)  # ← PPG_FS

    if len(peaks) < 2:
        return 0, 0, 0, 0

    rr = np.diff(peaks) / PPG_FS

    hr = 60 / np.mean(rr)
    sdnn = np.std(rr) * 1000

    diff_rr = np.diff(rr)
    rmssd = np.sqrt(np.mean(diff_rr**2)) * 1000

    nn50 = np.sum(np.abs(diff_rr) > 0.05)
    pnn50 = (nn50 / len(diff_rr)) * 100 if len(diff_rr) > 0 else 0

    return float(hr), float(sdnn), float(rmssd), float(pnn50)


def load_ppg_files(sessionid, sid):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ppgpath
        FROM QuestionAttempt
        WHERE sessionid = ? AND sid = ?
        ORDER BY QuestionAttemptID
    """, (sessionid, sid))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None, None

    dfs = []
    info = []

    for row in rows:
        path = row[0]

        if not path or not os.path.exists(path):
            continue

        df = pd.read_csv(path)

        dfs.append(df)
        info.append({
            "path": path,
            "rows": len(df)
        })

    if not dfs:
        return None, None

    combined = pd.concat(dfs, ignore_index=True)

    return combined, info

def compute_ppg_windows(df):

    channels = ["PPG1", "PPG2", "PPG3"]

    time_axis = []
    hr_list, sdnn_list, rmssd_list, pnn50_list = [], [], [], []

    t = 0

    for start in range(0, len(df) - PPG_WINDOW_SIZE + 1, PPG_STEP_SIZE):
        window = df.iloc[start:start + PPG_WINDOW_SIZE]

        ch_hr, ch_sdnn, ch_rmssd, ch_pnn50 = [], [], [], []

        for ch in channels:
            if ch not in df.columns:
                continue

            signal = window[ch].values

            hr, sdnn, rmssd, pnn50 = compute_ppg_features(signal)

            ch_hr.append(hr)
            ch_sdnn.append(sdnn)
            ch_rmssd.append(rmssd)
            ch_pnn50.append(pnn50)

        # average of all channels
        if ch_hr:
            hr_list.append(float(np.mean(ch_hr)))
            sdnn_list.append(float(np.mean(ch_sdnn)))
            rmssd_list.append(float(np.mean(ch_rmssd)))
            pnn50_list.append(float(np.mean(ch_pnn50)))
        else:
            hr_list.append(0)
            sdnn_list.append(0)
            rmssd_list.append(0)
            pnn50_list.append(0)

        time_axis.append(t)
        t += PPG_STEP_SEC

    return time_axis, hr_list, sdnn_list, rmssd_list, pnn50_list

# ==========================
# Band Power
# ==========================

def band_power(signal, band):
    signal = signal - np.mean(signal)
    freqs, psd = welch(signal, EEG_FS, nperseg=EEG_FS)  # ← EEG_FS

    idx = (freqs >= band[0]) & (freqs <= band[1])
    if not np.any(idx):
        return 0.0

    power = np.trapz(psd[idx], freqs[idx])
    return float(np.log10(power + 1))

def moving_average(arr, n=5):
    if len(arr) < n:
        return np.array(arr)   # ✅ ALWAYS numpy
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
    for start in range(0, len(df) - EEG_WINDOW_SIZE + 1, EEG_STEP_SIZE):
        window_data = df.iloc[start:start + EEG_WINDOW_SIZE]
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
        t += EEG_STEP_SEC

    # Smooth for frontend
    for band_name in result.keys():
        result[band_name] = moving_average(result[band_name], 5).tolist()

    return time_axis, result


def compute_single_band(df, band_range):

    channels = ["EEG1", "EEG2", "EEG3", "EEG4"]

    band_values = []
    time_axis = []

    t = 0
    for start in range(0, len(df) - EEG_WINDOW_SIZE + 1, EEG_STEP_SIZE):
        window_data = df.iloc[start:start + EEG_WINDOW_SIZE]
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
        t += EEG_STEP_SEC

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



# ppg api fuction
@eeg_api.route("/allp", methods=["GET"])
def ppg_all():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")

    df, info = load_ppg_files(sessionid, sid)

    if df is None:
        return jsonify({"error": "No PPG files found"}), 404

    time, hr, sdnn, rmssd, pnn50 = compute_ppg_windows(df)

    return jsonify({
        "sessionid": sessionid,
        "sid": sid,
        "time": time,
        "HR": hr,
        "SDNN": sdnn,
        "RMSSD": rmssd,
        "pNN50": pnn50,
        "files": info,
        "total_files": len(info)
    })



@eeg_api.route("/single", methods=["GET"])
def ppg_single():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")
    qid = request.args.get("qid")

    if not sessionid or not sid or not qid:
        return jsonify({"error": "sessionid, sid, qid required"}), 400

    df, path = load_single_ppg(sessionid, sid, qid)

    if df is None:
        return jsonify({"error": "PPG file not found"}), 404

    # 🔥 SAME LOGIC AS /all
    time, hr, sdnn, rmssd, pnn50 = compute_ppg_windows(df)

    return jsonify({
        "sessionid": sessionid,
        "sid": sid,
        "qid": qid,
        "file": {
            "path": path,
            "rows": len(df)
        },
        "time": time,
        "HR": hr,
        "SDNN": sdnn,
        "RMSSD": rmssd,
        "pNN50": pnn50
    })






#  Task Work


# ==========================
# BP REPORT API
# ==========================

@eeg_api.route("/bp-report", methods=["GET"])
def bp_report():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")

    if not sessionid or not sid:
        return jsonify({
            "error": "sessionid and sid required"
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ReportID,

                BaselineSYS,
                BaselineDIA,

                MidSYS,
                MidDIA,

                AfterQuestionSYS,
                AfterQuestionDIA

            FROM Reports
            WHERE sessionid = ? AND sid = ?
            ORDER BY ReportID ASC
        """, (sessionid, sid))

        rows = cursor.fetchall()

        conn.close()

        if not rows:
            return jsonify({
                "message": "No BP report found",
                "data": []
            }), 404

        result = []

        for row in rows[:3]:   # max 3 rows

            result.append({

                "ReportID": row[0],

                "Baseline": {
                    "SYS": row[1],
                    "DIA": row[2]
                },

                "Mid": {
                    "SYS": row[3],
                    "DIA": row[4]
                },

                "AfterQuestion": {
                    "SYS": row[5],
                    "DIA": row[6]
                }

            })

        return jsonify({
            "sessionid": sessionid,
            "sid": sid,
            "total_rows": len(result),
            "reports": result
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500



# =========================================================
# COMBINED EEG + BP API (QUESTION WISE)
# =========================================================

@eeg_api.route("/combined-question-report", methods=["GET"])
def combined_question_report():

    sessionid = request.args.get("sessionid")
    sid = request.args.get("sid")

    if not sessionid or not sid:
        return jsonify({
            "error": "sessionid and sid required"
        }), 400

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        # =====================================================
        # GET ALL QUESTIONS
        # =====================================================

        cursor.execute("""
            SELECT
                qa.qid,
                qa.eegpath,

                r.BaselineSYS,
                r.BaselineDIA,

                r.MidSYS,
                r.MidDIA,

                r.AfterQuestionSYS,
                r.AfterQuestionDIA

            FROM QuestionAttempt qa

            LEFT JOIN Reports r
                ON qa.sessionid = r.sessionid
                AND qa.sid = r.sid

            WHERE qa.sessionid = ?
            AND qa.sid = ?

            ORDER BY qa.QuestionAttemptID ASC
        """, (sessionid, sid))

        rows = cursor.fetchall()

        conn.close()

        if not rows:
            return jsonify({
                "error": "No question data found"
            }), 404

        final_response = []

        # =====================================================
        # LOOP EACH QUESTION
        # =====================================================

        for row in rows:

            qid = row[0]
            eegpath = row[1]

            baseline_sys = row[2]
            baseline_dia = row[3]

            mid_sys = row[4]
            mid_dia = row[5]

            end_sys = row[6]
            end_dia = row[7]

            # =================================================
            # LOAD EEG FILE
            # =================================================

            eeg_graph = {}

            if eegpath and os.path.exists(eegpath):

                df = pd.read_csv(eegpath)

                time_axis, bands = compute_all_bands(df)

                eeg_graph = {
                    "time": time_axis,
                    "delta": bands["delta"],
                    "theta": bands["theta"],
                    "alpha": bands["alpha"],
                    "beta": bands["beta"],
                    "gamma": bands["gamma"]
                }

            # =================================================
            # BP SECTION
            # =================================================

            bp_section = []

            # START BP
            if baseline_sys is not None:

                bp_section.append({
                    "type": "START_BP",
                    "minute": 0,
                    "SYS": baseline_sys,
                    "DIA": baseline_dia
                })

            # MID BP (ONLY IF EXISTS)
            if mid_sys is not None:

                bp_section.append({
                    "type": "MID_BP",
                    "minute": 5,
                    "SYS": mid_sys,
                    "DIA": mid_dia
                })

            # END BP
            if end_sys is not None:

                bp_section.append({
                    "type": "END_BP",
                    "minute": 10,
                    "SYS": end_sys,
                    "DIA": end_dia
                })

            # =================================================
            # FINAL QUESTION OBJECT
            # =================================================

            final_response.append({

                "qid": qid,

                # -----------------------------------------
                # BP DATA
                # -----------------------------------------
                "bp": bp_section,

                # -----------------------------------------
                # EEG GRAPH
                # -----------------------------------------
                "eeg": eeg_graph

            })

        # =====================================================
        # FINAL RETURN
        # =====================================================

        return jsonify({

            "sessionid": sessionid,
            "sid": sid,
            "total_questions": len(final_response),

            "questions": final_response

        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500