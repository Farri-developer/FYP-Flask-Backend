import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Blueprint, jsonify
from database.db import get_db_connection
from scipy.signal import butter, filtfilt, welch, find_peaks

Model = Blueprint('Model', __name__)

#  only one api in this file to predict the stress level of a session based on the latest model and update the database with the results

#  url is /api/devices/Model/predict_session/<session_id>

# r"D:\Path\AIModel\stress_model_random_forest.pkl"
MODEL_PATH = r"C:\Users\Farhan Ayub\Desktop\Final Year Project\FYP-Flask-Backend\Data\stress_model_random_forest.pkl"
model = joblib.load(MODEL_PATH)

WIN_SEC = 30


# ================= FILTER =================
def bandpass_filter(data, low, high, fs):
    nyq = fs / 2
    if fs <= 0 or low >= high:
        return data
    b, a = butter(4, [low/nyq, high/nyq], btype='band')
    return filtfilt(b, a, data, axis=0)


# ================= EEG =================
def compute_band_powers(signal, fs):
    bands = {"Delta":(1,4),"Theta":(4,8),"Alpha":(8,13),"Beta":(13,30)}

    f, pxx = welch(signal, fs=fs, nperseg=min(len(signal), int(fs*2)))

    powers = {}
    for band,(low,high) in bands.items():
        mask = (f>=low) & (f<high)
        powers[band] = np.trapz(pxx[mask], f[mask]) if np.any(mask) else 0
    return powers


def eeg_score(beta_alpha):
    r = np.mean(beta_alpha)
    if r < 0.9: return 0
    elif r < 1.1: return 1
    else: return 2


# ================= PPG =================
def extract_hrv(signal, fs):

    peaks,_ = find_peaks(signal, distance=max(int(fs*0.4),1))
    if len(peaks)<2:
        return 0,0,0,0

    rr = np.diff(peaks)/fs*1000

    hr = 60/(np.mean(rr)/1000+1e-6)
    sdnn = np.std(rr)
    rmssd = np.sqrt(np.mean(np.diff(rr)**2)) if len(rr)>1 else 0
    pnn50 = np.sum(np.abs(np.diff(rr))>50)/(len(rr)+1e-6)*100

    return hr, sdnn, rmssd, pnn50


def ppg_score(hr, sdnn, rmssd, pnn50):

    hr_s = 1 if hr>110 else 0.7 if hr>95 else 0.4 if hr>80 else 0.1
    sdnn_s = 1 - min(sdnn/150,1)
    rmssd_s = 1 - min(rmssd/120,1)
    pnn_s = 1 - min(pnn50/60,1)

    return (0.4*hr_s + 0.3*sdnn_s + 0.2*rmssd_s + 0.1*pnn_s)*2


# ================= API =================

import os
import joblib
import pandas as pd
import numpy as np
from flask import Blueprint, jsonify
from database.db import get_db_connection
from scipy.signal import butter, filtfilt, welch, find_peaks

Model = Blueprint('Model', __name__)
#  change the path according to  data/stress_model_random_forest.pkl
MODEL_PATH = r"D:\Path\AIModel\stress_model_random_forest.pkl"
model = joblib.load(MODEL_PATH)


# ================= FILTER =================
def bandpass_filter(data, low, high, fs):
    nyq = fs / 2
    if fs <= 0 or low >= high:
        return data
    b, a = butter(4, [low/nyq, high/nyq], btype='band')
    return filtfilt(b, a, data, axis=0)


# ================= EEG =================
def compute_band_powers(signal, fs):
    bands = {"Delta":(1,4),"Theta":(4,8),"Alpha":(8,13),"Beta":(13,30)}
    f, pxx = welch(signal, fs=fs, nperseg=min(len(signal), int(fs*2)))

    powers = {}
    for band,(low,high) in bands.items():
        mask = (f>=low) & (f<high)
        powers[band] = np.trapz(pxx[mask], f[mask]) if np.any(mask) else 0

    return powers


def eeg_score(beta_alpha):
    r = np.mean(beta_alpha)
    if r < 0.9: return 0
    elif r < 1.1: return 1
    else: return 2


# ================= PPG =================
def extract_hrv(signal, fs):
    peaks,_ = find_peaks(signal, distance=max(int(fs*0.4),1))
    if len(peaks)<2:
        return 0,0,0,0

    rr = np.diff(peaks)/fs*1000

    hr = 60/(np.mean(rr)/1000+1e-6)
    sdnn = np.std(rr)
    rmssd = np.sqrt(np.mean(np.diff(rr)**2)) if len(rr)>1 else 0
    pnn50 = np.sum(np.abs(np.diff(rr))>50)/(len(rr)+1e-6)*100

    return hr, sdnn, rmssd, pnn50


def ppg_score(hr, sdnn, rmssd, pnn50):
    hr_s = 1 if hr>110 else 0.7 if hr>95 else 0.4 if hr>80 else 0.1
    sdnn_s = 1 - min(sdnn/150,1)
    rmssd_s = 1 - min(rmssd/120,1)
    pnn_s = 1 - min(pnn50/60,1)

    return (0.4*hr_s + 0.3*sdnn_s + 0.2*rmssd_s + 0.1*pnn_s)*2


# ================= API =================

@Model.route("/predict_session/<int:session_id>", methods=["GET"])
def predict_session(session_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT TOP 3 QuestionAttemptID, eegpath, ppgpath, bppath
            FROM QuestionAttempt
            WHERE sessionid = ?
        """, (session_id,))

        rows = cursor.fetchall()
        processed = 0

        for qa_id, eeg_path, ppg_path, bp_path in rows:

            try:
                eeg_df = pd.read_csv(eeg_path)
                ppg_df = pd.read_csv(ppg_path)
                bp_df = pd.read_csv(bp_path)

                # ===== TIME COLUMN AUTO FIX =====
                tcol = 'timestamp' if 'timestamp' in eeg_df.columns else 'lsl_timestamp'

                # ===== FS =====
                eeg_fs = len(eeg_df)/(eeg_df[tcol].iloc[-1]-eeg_df[tcol].iloc[0]+1e-6)
                ppg_fs = len(ppg_df)/(ppg_df[tcol].iloc[-1]-ppg_df[tcol].iloc[0]+1e-6)

                # ===== WINDOW =====
                start = max(eeg_df[tcol].iloc[0], ppg_df[tcol].iloc[0])
                end = min(eeg_df[tcol].iloc[-1], ppg_df[tcol].iloc[-1])

                WIN_SEC = 30
                num_windows = int((end - start) / WIN_SEC)

                all_rows = []

                # ===== WINDOW LOOP =====
                for w in range(num_windows):

                    ws = start + w * WIN_SEC
                    we = ws + WIN_SEC

                    eeg_win = eeg_df[(eeg_df[tcol]>=ws)&(eeg_df[tcol]<we)]
                    ppg_win = ppg_df[(ppg_df[tcol]>=ws)&(ppg_df[tcol]<we)]

                    if len(eeg_win)<10 or len(ppg_win)<10:
                        continue

                    features = {
                        "Time_Start": ws,
                        "Time_End": we,
                        "Window_Index": w
                    }

                    # ===== EEG =====
                    eeg_vals = bandpass_filter(
                        eeg_win[['EEG1','EEG2','EEG3','EEG4']].values,
                        0.5,45,eeg_fs
                    )

                    beta_list = []
                    alpha_list = []

                    for ch in range(4):

                        p = compute_band_powers(eeg_vals[:,ch], eeg_fs)

                        for band in p:
                            features[f"EEG{ch+1}_{band}"] = p[band]

                        ratio = p['Beta']/(p['Alpha']+1e-6)
                        features[f"EEG{ch+1}_BetaAlpha"] = ratio

                        beta_list.append(p['Beta'])
                        alpha_list.append(p['Alpha'])

                    # ===== SI =====
                    features["SI"] = np.mean(beta_list)/(np.mean(alpha_list)+1e-6)

                    # ===== PPG =====
                    hr, sdnn, rmssd, pnn50 = extract_hrv(
                        ppg_win['PPG1'].values,
                        ppg_fs
                    )

                    features.update({
                        "HR":hr,
                        "SDNN":sdnn,
                        "RMSSD":rmssd,
                        "pNN50":pnn50
                    })

                    # ===== BP =====
                    last = bp_df.iloc[-1]

                    features["DeltaSYS"] = float(last.get("DeltaSYS",0))
                    features["DeltaDIA"] = float(last.get("DeltaDIA",0))
                    features["DeltaPulse"] = float(last.get("DeltaPulse",0))

                    all_rows.append(features)

                # ===== FINAL DATAFRAME =====
                df = pd.DataFrame(all_rows)

                # ===== SAVE CSV =====
                folder = os.path.dirname(eeg_path)
                save_path = os.path.join(folder, f"{qa_id}_features.csv")
                df.to_csv(save_path, index=False)

                print("CSV SAVED:", save_path, "ROWS:", len(df))

                # ===== MODEL =====
                df_model = df.drop(columns=["Time_Start","Time_End","Window_Index"], errors="ignore")
                df_model = df_model.reindex(columns=model.feature_names_in_, fill_value=0)

                preds = model.predict(df_model)
                final_pred = int(pd.Series(preds).value_counts().idxmax())

                # ===== DB UPDATE =====
                cursor.execute("""
                    UPDATE Reports
                    SET HR=?, SDNN=?, RMSSD=?, pNN50=?, SI=?, stresslevel=?
                    WHERE QuestionAttemptID=? AND sessionid=?
                """, (
                    float(df["HR"].mean()),
                    float(df["SDNN"].mean()),
                    float(df["RMSSD"].mean()),
                    float(df["pNN50"].mean()),
                    float(df["SI"].mean()),
                    final_pred,
                    qa_id,
                    session_id
                ))

                processed += 1

            except Exception as e:
                print("ERROR:", e)

        conn.commit()

        return jsonify({
            "message": "SUCCESS",
            "processed_questions": processed
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        conn.close()