import os
import joblib
import pandas as pd
import numpy as np
import traceback
from flask import Blueprint, jsonify
from database.db import get_db_connection
from scipy.signal import butter, filtfilt, welch, find_peaks

Model = Blueprint('Model', __name__)

# ================= MODEL LOAD =================
MODEL_PATH = r"D:\Path\AIModel\stress_rf_model.pkl"
model = joblib.load(MODEL_PATH)

WIN_SEC = 30


# ================= FILTER =================
def bandpass_filter(data, low, high, fs):
    nyq = fs / 2
    if fs <= 0 or low >= high:
        return data
    b, a = butter(4, [low / nyq, high / nyq], btype='band')
    return filtfilt(b, a, data, axis=0)


# ================= EEG =================
def compute_band_powers(signal, fs):
    bands = {
        "Delta": (1,  4),
        "Theta": (4,  8),
        "Alpha": (8,  13),
        "Beta":  (13, 30),
        "Gamma": (30, 45)
    }
    f, pxx = welch(signal, fs=fs, nperseg=min(len(signal), int(fs * 2)))
    powers = {}
    for band, (low, high) in bands.items():
        mask = (f >= low) & (f < high)
        powers[band] = float(np.trapz(pxx[mask], f[mask])) if np.any(mask) else 0.0
    return powers


# ================= PPG =================
def extract_hrv(signal, fs):
    peaks, _ = find_peaks(signal, distance=max(int(fs * 0.4), 1))
    if len(peaks) < 2:
        return 0.0, 0.0, 0.0, 0.0
    rr    = np.diff(peaks) / fs * 1000
    hr    = 60 / (np.mean(rr) / 1000 + 1e-6)
    sdnn  = float(np.std(rr))
    rmssd = float(np.sqrt(np.mean(np.diff(rr) ** 2))) if len(rr) > 1 else 0.0
    pnn50 = float(np.sum(np.abs(np.diff(rr)) > 50) / (len(rr) + 1e-6) * 100)
    return float(hr), sdnn, rmssd, pnn50


# ================= TIMESTAMP HELPERS =================
def get_tcol(df):
    """Return the time column name — auto-detect."""
    for col in ['timestamp', 'lsl_timestamp', 'time', 'Time']:
        if col in df.columns:
            return col
    raise ValueError(f"No time column found. Columns: {df.columns.tolist()}")


def normalize_timestamps(df, tcol):
    """
    Convert to seconds if timestamps are in ms or ns.
    nanoseconds  (range > 1e9) → divide by 1e9
    milliseconds (range > 1e6) → divide by 1e3
    seconds — leave as is
    """
    t = df[tcol].astype(float)
    t_range = t.iloc[-1] - t.iloc[0]
    df = df.copy()
    if t_range > 1e9:
        df[tcol] = t / 1e9
    elif t_range > 1e6:
        df[tcol] = t / 1e3
    else:
        df[tcol] = t
    return df


# ================= API =================

@Model.route("/predict_session/<int:session_id>", methods=["GET"])
def predict_session(session_id):

    conn      = get_db_connection()
    cursor    = conn.cursor()
    debug_log = []

    def log(msg):
        print(msg)
        debug_log.append(msg)

    try:
        # ===== DB QUERY =====
        cursor.execute("""
            SELECT TOP 3 QuestionAttemptID, eegpath, ppgpath, bppath
            FROM QuestionAttempt
            WHERE sessionid = ?
        """, (session_id,))

        rows = cursor.fetchall()
        log(f"DB rows found for sessionid={session_id}: {len(rows)}")

        if not rows:
            return jsonify({
                "message":   "NO_DATA",
                "detail":    f"No QuestionAttempt rows for sessionid={session_id}",
                "debug_log": debug_log
            }), 404

        processed = 0
        results   = []

        for qa_id, eeg_path, ppg_path, bp_path in rows:

            qa_steps = []

            def qlog(msg):
                log(f"  QA {qa_id}: {msg}")
                qa_steps.append(msg)

            try:
                # ===== READ CSVs =====
                qlog(f"EEG  path → {eeg_path}")
                eeg_df = pd.read_csv(eeg_path)

                qlog(f"PPG  path → {ppg_path}")
                ppg_df = pd.read_csv(ppg_path)

                qlog(f"BP   path → {bp_path}")
                bp_df  = pd.read_csv(bp_path)

                qlog(f"EEG  shape={eeg_df.shape}  cols={eeg_df.columns.tolist()}")
                qlog(f"PPG  shape={ppg_df.shape}  cols={ppg_df.columns.tolist()}")
                qlog(f"BP   shape={bp_df.shape}   cols={bp_df.columns.tolist()}")

                # ===== TIME COLUMN =====
                eeg_tcol = get_tcol(eeg_df)
                ppg_tcol = get_tcol(ppg_df)
                qlog(f"Time cols → EEG:{eeg_tcol}  PPG:{ppg_tcol}")

                # ===== NORMALIZE TIMESTAMPS =====
                eeg_df = normalize_timestamps(eeg_df, eeg_tcol)
                ppg_df = normalize_timestamps(ppg_df, ppg_tcol)

                # ===== SAMPLING RATE =====
                eeg_dur = eeg_df[eeg_tcol].iloc[-1] - eeg_df[eeg_tcol].iloc[0]
                ppg_dur = ppg_df[ppg_tcol].iloc[-1] - ppg_df[ppg_tcol].iloc[0]
                eeg_fs  = len(eeg_df) / (eeg_dur + 1e-6)
                ppg_fs  = len(ppg_df) / (ppg_dur + 1e-6)
                qlog(f"FS → EEG:{eeg_fs:.1f} Hz  PPG:{ppg_fs:.1f} Hz")
                qlog(f"Duration → EEG:{eeg_dur:.1f}s  PPG:{ppg_dur:.1f}s")

                # ===== OVERLAP WINDOW RANGE =====
                start       = max(eeg_df[eeg_tcol].iloc[0], ppg_df[ppg_tcol].iloc[0])
                end         = min(eeg_df[eeg_tcol].iloc[-1], ppg_df[ppg_tcol].iloc[-1])
                total_dur   = end - start
                num_windows = int(total_dur / WIN_SEC)
                qlog(f"Overlap={total_dur:.1f}s  num_windows={num_windows} (WIN_SEC={WIN_SEC})")

                if num_windows == 0:
                    qlog(f"⚠ Recording too short for {WIN_SEC}s window — skipping.")
                    results.append({
                        "question_attempt_id": qa_id,
                        "status": "skipped_short_duration",
                        "debug": qa_steps
                    })
                    continue

                all_rows = []

                # ===== WINDOW LOOP =====
                for w in range(num_windows):

                    ws = start + w * WIN_SEC
                    we = ws + WIN_SEC

                    eeg_win = eeg_df[(eeg_df[eeg_tcol] >= ws) & (eeg_df[eeg_tcol] < we)]
                    ppg_win = ppg_df[(ppg_df[ppg_tcol] >= ws) & (ppg_df[ppg_tcol] < we)]

                    if len(eeg_win) < 10 or len(ppg_win) < 10:
                        qlog(f"  w{w}: skip — eeg={len(eeg_win)} ppg={len(ppg_win)} samples")
                        continue

                    features = {}

                    # ===== EEG =====
                    eeg_cols = [c for c in ['EEG1', 'EEG2', 'EEG3', 'EEG4']
                                if c in eeg_win.columns]
                    eeg_vals = bandpass_filter(
                        eeg_win[eeg_cols].values, 0.5, 45, eeg_fs
                    )

                    beta_list  = []
                    alpha_list = []

                    for ch in range(len(eeg_cols)):
                        p = compute_band_powers(eeg_vals[:, ch], eeg_fs)
                        for band in p:
                            features[f"EEG{ch+1}_{band}"] = p[band]
                        ratio = p['Beta'] / (p['Alpha'] + 1e-6)
                        features[f"EEG{ch+1}_BetaAlpha"] = ratio
                        beta_list.append(p['Beta'])
                        alpha_list.append(p['Alpha'])

                    features["SI"] = np.mean(beta_list) / (np.mean(alpha_list) + 1e-6)

                    # ===== PPG =====
                    ppg_col = 'PPG1' if 'PPG1' in ppg_win.columns else ppg_win.columns[1]
                    hr, sdnn, rmssd, pnn50 = extract_hrv(ppg_win[ppg_col].values, ppg_fs)
                    features.update({
                        "HR":    hr,
                        "SDNN":  sdnn,
                        "RMSSD": rmssd,
                        "pNN50": pnn50
                    })

                    # ===== BP =====
                    last = bp_df.iloc[-1]
                    features["DeltaSYS"]   = float(last.get("DeltaSYS",   0))
                    features["DeltaDIA"]   = float(last.get("DeltaDIA",   0))
                    features["DeltaPulse"] = float(last.get("DeltaPulse", 0))

                    all_rows.append(features)

                qlog(f"Valid windows extracted: {len(all_rows)}")

                if len(all_rows) == 0:
                    qlog("⚠ No valid windows after filtering — skipping.")
                    results.append({
                        "question_attempt_id": qa_id,
                        "status": "no_valid_windows",
                        "debug": qa_steps
                    })
                    continue

                # ===== DATAFRAME =====
                df = pd.DataFrame(all_rows)

                # ===== SAVE RAW FEATURES CSV =====
                folder    = os.path.dirname(eeg_path)
                save_path = os.path.join(folder, f"{qa_id}_features.csv")
                df.to_csv(save_path, index=False)
                qlog(f"Features CSV saved → {save_path}")

                # ===== MODEL PREDICTION =====
                df_model    = df.reindex(columns=model.feature_names_in_, fill_value=0)
                preds       = model.predict(df_model)
                proba       = model.predict_proba(df_model)
                class_list  = list(model.classes_)

                final_label = pd.Series(preds).value_counts().idxmax()
                label_idx   = class_list.index(final_label)
                final_score = round(float(np.mean(proba[:, label_idx]) * 100), 2)

                qlog(f"Prediction → label={final_label}  confidence={final_score}%")

                # per-window breakdown
                window_breakdown = []
                for i, (pred, prob_row) in enumerate(zip(preds, proba)):
                    pidx = class_list.index(pred)
                    window_breakdown.append({
                        "window":     i + 1,
                        "label":      int(pred),
                        "confidence": round(float(prob_row[pidx]) * 100, 2)
                    })

                # ===== HRV AVERAGES =====
                avg_hr    = round(float(df["HR"].mean()),    2)
                avg_sdnn  = round(float(df["SDNN"].mean()),  2)
                avg_rmssd = round(float(df["RMSSD"].mean()), 2)
                avg_pnn50 = round(float(df["pNN50"].mean()), 2)
                avg_si    = round(float(df["SI"].mean()),    2)

                # ===== DB UPDATE =====
                cursor.execute("""
                    UPDATE Reports
                    SET HR=?, SDNN=?, RMSSD=?, pNN50=?, SI=?,
                        stresslevel=?
                    WHERE QuestionAttemptID=? AND sessionid=?
                """, (
                    avg_hr, avg_sdnn, avg_rmssd, avg_pnn50, avg_si,
                    str(final_label),

                    qa_id,
                    session_id
                ))

                processed += 1

                results.append({
                    "question_attempt_id": qa_id,
                    "status":              "success",
                    "stress_label": int(final_label),
                    "stress_score":        final_score,
                    "hrv": {
                        "HR":    avg_hr,
                        "SDNN":  avg_sdnn,
                        "RMSSD": avg_rmssd,
                        "pNN50": avg_pnn50,
                        "SI":    avg_si
                    },
                    "windows_processed": len(all_rows),
                    "window_breakdown":  window_breakdown,
                    "debug":             qa_steps
                })

            except Exception as e:
                qlog(f"EXCEPTION → {str(e)}")
                traceback.print_exc()
                results.append({
                    "question_attempt_id": qa_id,
                    "status":              "error",
                    "error":               str(e),
                    "debug":               qa_steps
                })

        conn.commit()

        return jsonify({
            "message":             "SUCCESS",
            "processed_questions": processed,
            "total_questions":     len(rows),
            "results":             results,
            "debug_log":           debug_log
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error":     str(e),
            "debug_log": debug_log
        }), 500

    finally:
        cursor.close()
        conn.close()