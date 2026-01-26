from flask import Flask
from routes.student_routes import student_bp
from routes.question_routes import question_bp
from routes.admin_routes import admin_BP
from routes.report_routes import report_bp
from routes.EEG_PPG import muse_bp  # << Add this

app = Flask(__name__)

app.register_blueprint(student_bp, url_prefix="/api/student")
app.register_blueprint(question_bp, url_prefix="/api/question")
app.register_blueprint(admin_BP, url_prefix="/api/admin")
app.register_blueprint(report_bp, url_prefix="/api/report")
app.register_blueprint(muse_bp, url_prefix="/api/muse")  # << Add this

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
