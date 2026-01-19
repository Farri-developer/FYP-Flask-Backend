# Student Stress Monitoring System (API-Based Backend)

## 📄 Overview

Ye project **Student Stress Monitoring System** ka backend hai, jo **Flask REST APIs** aur **SQL Server** par based hai.  
System students ke physiological signals (EEG, PPG, BP) ko record karta hai, un par signal processing apply karta hai, aur per question / per session stress reports generate karta hai.

**Key Features:**
- Mobile App / Frontend (React Native) ke liye API data provide karta hai
- Student performance aur stress history track karta hai
- Real-time & historical analysis support karta hai

---

## 🔗 Database Structure

### 🗂 Tables Used by APIs

| Table Name       | API Usage                                      |
|-----------------|-----------------------------------------------|
| Student          | Student authentication, profile, reports     |
| Session          | Session start/end, sensor file paths         |
| Question         | Question fetching & management               |
| QuestionAttempt  | Student answers, time, scores                |
| Reports          | Stress analytics & visualization             |

### 🔑 Relationships

- `Student → Session` (1:N)  
- `Session → QuestionAttempt` (1:N)  
- `Question → QuestionAttempt` (1:N)  
- `Student → QuestionAttempt` (1:N)  
- `Session → Reports` (1:N)  
- `Question → Reports` (1:N)  
- `Student → Reports` (1:N)  

✔ APIs foreign key constraints ko follow karti hain  
✔ `ON DELETE CASCADE` se orphan data avoid hota hai  

---

## 🧠 API-Based System Flow

### 1. Student Authentication API
- Registration number + password verify hota hai
- Student ID (sid) frontend ko return hoti hai

### 2. Session Management APIs
- **Session Start API:** New session create hoti hai, startTime store hota hai
- **Session End API:** endTime update hota hai, self-report save hota hai

### 3. Sensor Data APIs
- EEG, PPG, BP signals record hotay hain
- File paths database mein store hotay hain
- Raw data Flask APIs se process hota hai

### 4. Question Handling APIs
- Student ke liye unattempted question fetch hota hai
- `QuestionAttempt` table update hoti hai (time, answer, scores)

### 5. Signal Processing APIs
- EEG, PPG, BP signals se features extract hotay hain
- Processing Python libraries (NumPy, Pandas) se hoti hai

### 6. Stress Calculation APIs
- Stress Score calculate hota hai (0–100)
- Stress Level assign hota hai: **Low / Medium / High**

### 7. Report Generation APIs
- Per question report  
- Per session report  
- Student-wise stress history

### 8. Visualization APIs
- EEG Alpha band combined graph  
- Stress trends over time  
- Question-wise stress analysis  

---

## 🧪 Extracted Features

| Signal | Features       |
|--------|----------------|
| PPG    | HR, SDNN, RMSSD|
| BP     | SYS, DYS       |
| EEG    | CL, RI, SI     |

✔ Features APIs ke through calculate aur `Reports` table mein save hotay hain  

---

## 🟢 Normalization

- **1NF** – Atomic fields  
- **2NF** – Full functional dependency  
- **3NF** – Controlled redundancy  

✔ APIs sirf normalized data access karti hain  

---

## ⚙️ Backend Setup

### 📦 Install Dependencies
```bash
pip install flask pyodbc pandas numpy
🗄 Database Setup
SQL Server install karein

Database create karein:

sql
Copy code
CREATE DATABASE Update_Database;
Tables SQL script se create karein

db.py mein credentials update karein

▶️ Run Flask Server
bash
Copy code
python app.py
🔌 API Endpoints
Endpoint	Method	Description
/student/getall	GET	Get all students
/student/getbyid/<sid>	GET	Get student profile
/student/allreports/<sid>	GET	Student stress history
/student/reportstop5/<sid>	GET	Last 5 reports
/question/getall	GET	Get all questions
/question/insert	POST	Add new question
/unattemptedforsid/<sid>	GET	Get one unattempted question
/reportbyqid/<qid>	GET	Aggregated stress report
/eeg/alpha/combined	GET	EEG Alpha visualization
