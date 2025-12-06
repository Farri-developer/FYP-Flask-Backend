from flask import Flask
from routes.student_routes import student_bp
from routes.question_routes import question_bp
from routes.session_routes import session_bp
from routes.stats_routes import stats_bp

app = Flask(__name__)

app.register_blueprint(student_bp, url_prefix="/api/student")
app.register_blueprint(question_bp, url_prefix="/api/question")
app.register_blueprint(session_bp, url_prefix="/api/session")
app.register_blueprint(stats_bp, url_prefix="/api/stats")

if __name__ == "__main__":
    app.run(debug=True)
