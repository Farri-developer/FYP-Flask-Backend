from flask import Flask
from routes.student_routes import student_bp
from routes.question_routes import question_bp
from routes.admin_routes import admin_BP
from routes.report_routes import report_bp
from routes.EEG_PPG import health_api  # << Add this
from routes.deviceApi.session import devices_api
from routes.deviceApi.eeg_api import eeg_api
from  routes.deviceApi.Model import Model
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

app.register_blueprint(student_bp, url_prefix="/api/student")
app.register_blueprint(question_bp, url_prefix="/api/question")
app.register_blueprint(admin_BP, url_prefix="/api/admin")
app.register_blueprint(report_bp, url_prefix="/api/report")

app.register_blueprint(health_api, url_prefix="/api/muse")  # << Add this
app.register_blueprint(devices_api, url_prefix="/api/devices")
app.register_blueprint(eeg_api, url_prefix="/api/devices/eeg")
app.register_blueprint(Model, url_prefix="/api/devices/Model")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
