import pyodbc

def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=DESKTOP-Q604CE0;"
        "DATABASE=fyp;"
        "Trusted_Connection=yes;"
    )
    return conn




