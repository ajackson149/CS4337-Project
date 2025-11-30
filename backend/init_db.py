import sqlite3
import csv
from pathlib import Path

DB_PATH = Path(__file__).parent / "library.db"
DATA_DIR = Path(__file__).parent / "data"

#open database, run sql
def getConnection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

#creates tables
def createTables(conn):
    cur = conn.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS BOOK
                (Isbn TEXT PRIMARY KEY,
                 Title TEXT NOT NULL);""")

    cur.execute("""
                CREATE TABLE IF NOT EXISTS AUTHORS (
                Author_id INTEGER PRIMARY KEY,
                Name TEXT NOT NULL
                );""")
    
    cur.execute("""
                CREATE TABLE IF NOT EXISTS BOOK_AUTHORS(
                Isbn TEXT NOT NULL, Author_id INTEGER NOT NULL
                , PRIMARY KEY (Isbn, Author_id), FOREIGN KEY (Isbn) REFERENCES BOOK(Isbn),
                FOREIGN KEY (Author_id) REFERENCES AUTHORS(Author_id)
                );
                """)

    cur.execute("""
                
                CREATE TABLE IF NOT EXISTS BORROWER(

                Card_id TEXT PRIMARY KEY, Ssn TEXT NOT NULL UNIQUE,
                Bname TEXT NOT NULL, Address TEXT NOT NULL,
                Phone TEXT NOT NULL

                
                );""")
    conn.commit()


def isTableEmpty(conn, tableName):
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {tableName};")
    count = cur.fetchone()[0]
    return count == 0

def importCsv(conn, tableName, csvPath, columns):
    with csvPath.open("r", encoding ="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            [row[col] for col in columns]
            for row in reader
        ]

    placeholders = ",".join(["?"] * len(columns))
    col_list = ",".join(columns)

    conn.executemany(
        f"INSERT INTO {tableName} ({col_list}) VALUES ({placeholders
                                                        })", rows)
    
    conn.commit()

def importData(conn):
    if isTableEmpty(conn, "BOOK"):
        importCsv(conn, "BOOK", DATA_DIR/"book.csv", ["Isbn", "Title"])
    
    if isTableEmpty(conn, "AUTHORS"):
        importCsv(conn, "AUTHORS", DATA_DIR/"authors.csv", ["Author_id", "Name"])
    
    if isTableEmpty(conn, "BOOK_AUTHORS"):
        importCsv(conn, "BOOK_AUTHORS", DATA_DIR/"book_authors.csv", ["Isbn", "Author_id"])

    if isTableEmpty(conn, "BORROWER"):
        importCsv(conn, "BORROWER", DATA_DIR/"borrower.csv", 
                  ["Card_id", "Ssn", "Bname", "Address", "Phone"])
        
def initDb():
    conn = getConnection()
    createTables(conn)
    importData(conn)
    conn.close()
    print("test")

if __name__ == "__main__":
    initDb()