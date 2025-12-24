FYP Project: Student Stress Monitoring System
📄 Overview

Ye project ek Student Stress Monitoring System hai jo students ke physiological signals (EEG, PPG, BP) ko record karta hai, process karta hai, aur per session/per question stress reports generate karta hai.
System Flask + SQL Server par build hai aur students ki performance aur stress history track karta hai.

🔗 Database Structure
Tables & Relationships
Table Name	Description
Student	Student basic info (regno, name, cgpa, semester, password)
StudentSession	Records each student session with start/end time, sensor file paths, self-report
Question	Questions available for students to attempt
QuestionAttempt	Tracks which student attempted which question, time taken, answer
Reports	Stress reports per session/question including HR, BP, EEG features, stress score & level

Relationships:

Student → StudentSession (1:N)

StudentSession → QuestionAttempt (1:N)

Question → QuestionAttempt (1:N)

Student → QuestionAttempt (1:N)

StudentSession → Reports (1:N)

Question → Reports (1:N)

Student → Reports (1:N)

All foreign keys are set with ON DELETE CASCADE where necessary to maintain data integrity.

🧠 System Flow

Student Login: Regno + password authentication.

Session Start: New session is created.

Sensor Recording: EEG, PPG, BP signals captured and file paths stored.

Question Attempt: Student attempts questions; responses logged.

Session End & Self-Report: Student completes self-assessment.

Signal Processing: Extract features from EEG, PPG, BP.

Stress Calculation: Stress score (0–100) and stress level assigned.

Report Generation: Stores per session/per question reports.

Visualization: Students can view graphs and dashboards.

🧪 Extracted Features
Signal Type	Features
PPG	HR, SDNN, RMSSD
BP	SYS, DYS
EEG	CL, RI, SI
🟢 Normalization

1NF ✅

2NF ✅

3NF ✅ (controlled redundancy)

⚙️ Project Setup

Install required packages:

pip install flask pyodbc pandas numpy


Setup SQL Server and create FYP_update database (tables provided in SQL script).

Update db.py with your database credentials.

Run Flask server:

python app.py

🔌 Endpoints
Endpoint	Method	Description
/students	GET	Get list of all students
/unattemptedforsid/<sid>	GET	Get one unattempted question for a student
/reportbyqid/<qid>	GET	Get aggregated report for a question
/eeg/alpha/combined	GET	Get combined alpha EEG signal for visualization