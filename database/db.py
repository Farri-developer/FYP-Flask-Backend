import pyodbc

def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=Victus;"
        "DATABASE=Update_Database;"
        "Trusted_Connection=yes;"
    )
    return conn




