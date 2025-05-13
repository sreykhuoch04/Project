import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='19062004@khuoch',
        database='MySystem'
    )
