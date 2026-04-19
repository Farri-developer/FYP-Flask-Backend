# 🧠 Multimodal Stress Detection System (AI + Flask Backend)

A **research-grade full-stack system** that combines:

- 🧠 EEG Signals  
- ❤️ PPG Signals  
- 🩺 Blood Pressure  
- 📋 NASA-TLX (Self Report)  

to **detect human stress levels** using **Machine Learning + Flask APIs**.

---

## 📌 Project Overview

This system provides a **complete pipeline**:

- 📡 Real-time biosignal acquisition  
- 🧪 Dataset generation (feature engineering)  
- 🤖 Machine learning model training  
- 🌐 Flask backend APIs  
- 📊 Stress prediction & reporting  

---

## 🗂️ Project Structure


FYP-Flask-Backend/

│
├── app.py

├── routes/

│ ├── deviceApi/

│ │ ├── eeg_api.py

│ │ ├── Model.py

│ │ ├── session.py

│ ├── question_routes.py

│ ├── student_routes.py

│ ├── report_routes.py

│ ├── admin_routes.py

│ ├── EEG_PPG.py

│
├── database/

├── Data/

│ └── stress_model_random_forest.pkl

│
└── README.md


---

## ⚙️ Technologies Used

- Python  
- Flask (Backend APIs)  
- PySide6 (GUI)  
- NumPy / Pandas  
- SciPy (Signal Processing)  
- Scikit-learn (Machine Learning)  
- Joblib  
- Muse LSL (EEG + PPG Streaming)  
- Bleak (Bluetooth BP Device)  
- SQL Server / pyodbc  

---

## 🧩 System Workflow

### 1️⃣ Data Acquisition (Devices API)

📄 File: :contentReference[oaicite:0]{index=0}  

- Start EEG + PPG stream  
- Capture Blood Pressure  
- Record session data  

#### APIs:
- `/start_stream`
- `/start_session_bp`
- `/start_recording`
- `/stop_recording`
- `/after_question_bp`
- `/stop_stream`
- `/selfreport`

---

### 2️⃣ EEG Processing API

📄 File: :contentReference[oaicite:1]{index=1}  

Provides EEG band power analysis:

#### APIs:
- `/delta`
- `/theta`
- `/alpha`
- `/beta`
- `/gamma`
- `/all`

#### Features:
- Sliding window processing  
- Band power extraction  
- Smoothed signals for frontend  

---

### 3️⃣ AI Model Prediction API

📄 File: :contentReference[oaicite:2]{index=2}  

Predicts stress level using trained ML model.

#### API:

GET /predict_session/<session_id>


#### Features:
- EEG + PPG + BP feature extraction  
- Window-based prediction  
- Majority voting  
- Database update  

---

### 4️⃣ Question Management APIs

- Add / Update / Delete Questions  
- Fetch questions  

#### APIs:
- `/question/getall`
- `/question/insert`
- `/question/update/<id>`
- `/question/delete/<id>`

---

### 5️⃣ Student Management APIs

- Add / Update / Delete Students  
- Get student info  

#### APIs:
- `/student/getall`
- `/student/getbyid/<id>`
- `/student/insert`
- `/student/update/<id>`
- `/student/delete/<id>`

---

### 6️⃣ Reports & Analytics APIs

📄 File: :contentReference[oaicite:3]{index=3}  

#### Features:
- Session reports  
- Stress analysis  
- Question performance  
- GPT vs Non-GPT comparison  

#### APIs:
- `/report/allsession/<sid>`
- `/report/sessiontop5/<sid>`
- `/report/reportbyqid/<qid>`
- `/report/student_session_report/<sid>/<sessionid>`
- `/report/student_question_report/<sid>/<qid>`
- `/report/delete_session/<sessionid>`
- `/report/selfreport/<sessionid>`

---

## 🧠 Stress Levels

| Label | Meaning        |
|------|--------------|
| 0    | Low Stress   |
| 1    | Medium Stress|
| 2    | High Stress  |

---

## 🚀 How to Run Backend

### Step 1: Install Dependencies

```bash
pip install flask numpy pandas scipy scikit-learn joblib pyodbc bleak pylsl
Step 2: Run Server
python app.py
Step 3: API Base URL
http://127.0.0.1:5000/
📊 Key Features
✅ Real-time EEG + PPG streaming
✅ Blood pressure integration
✅ Machine learning prediction
✅ RESTful APIs
✅ Database integration
✅ Session-based tracking
✅ Advanced analytics
🔬 Research Contribution
Combines physiological + self-report data
Uses multimodal fusion approach
Provides real-time stress monitoring
Includes AI-based prediction + analytics dashboard
⚠️ Limitations
Requires Muse device
Requires BP device
Needs controlled environment
📌 Future Work
Deep Learning (LSTM / CNN)
Mobile App Integration
Cloud Deployment
Real-time Dashboard
🎓 Final Year Project

Multimodal Stress Detection System

👨‍💻 Developed By: Waleed Ahmed
🏫 University: Your University Name
📅 Year: 2026


---

🔥 This is now:
- **Professional GitHub README**
- **Backend + AI + APIs documented**
- **Perfect for FYP submission**

---

If you want next level:
- I can add **API documentation (Swagger style)**
- Or **Frontend integration guide**
- Or **Deployment (Render / AWS / VPS)**