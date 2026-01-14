import pyodbc

def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=Victus;"
        "DATABASE=FYP_update;"
        "Trusted_Connection=yes;"
    )
    return conn




