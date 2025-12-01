import sqlite3

class LibraryDB:
    def __init__(self, db_path):
        # Save the DB file path
        self.db_path = db_path

        # Connect to SQLite database
        self.conn = sqlite3.connect(self.db_path)

        # Create a cursor for executing SQL queries
        self.cur = self.conn.cursor()

        # Enable foreign key enforcement
        self.conn.execute("PRAGMA foreign_keys = ON;")
        
    def search_books(self, query):
        search = f"%{query.lower()}%"

        sql = """
        SELECT
            B.Isbn,
            B.Title,
            GROUP_CONCAT(A.Name, ', ') AS Authors,
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM BOOK_LOANS BL
                    WHERE BL.Isbn = B.Isbn
                    AND BL.Date_in IS NULL
                ) THEN 'OUT'
                ELSE 'IN'
            END AS Status
        FROM BOOK B
        LEFT JOIN BOOK_AUTHORS BA ON B.Isbn = BA.Isbn
        LEFT JOIN AUTHORS A ON BA.Author_id = A.Author_id
        WHERE
            LOWER(B.Isbn) LIKE ?
            OR LOWER(B.Title) LIKE ?
            OR LOWER(A.Name) LIKE ?
        GROUP BY B.Isbn;
        """

        self.cur.execute(sql, (search, search, search))
        rows = self.cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "isbn": row[0],
                "title": row[1],
                "authors": row[2] if row[2] else "",
                "status": row[3]
            })

        print(f"{'NO':<3} {'ISBN':<12} {'TITLE':<40} {'AUTHORS':<30} {'STATUS':<6}")
    
        # Separator (optional)
        # print("-" * 100)

        for i, book in enumerate(results, start=1):
            no = f"{i:02}"  # formats 1 as 01, 2 as 02, etc.
            isbn = book["isbn"][:12]
            title = book["title"][:40]
            authors = book["authors"][:30]
            status = book["status"]

            print(f"{no:<3} {isbn:<12} {title:<40} {authors:<30} {status:<6}")
            
        return results


    def checkout_book(self, isbn, card_id):
        isbn = isbn.strip().upper()
        card_id = card_id.strip()

        # make sure the borrower exists
        self.cur.execute("""
            SELECT * 
            FROM BORROWER
            WHERE Card_id = ?;
        """, (card_id,))
        borrower = self.cur.fetchone()
        if borrower is None:
            print("ERROR: Borrower does not exist")
            return False;
    
        # checking if the borrower has fines due
        self.cur.execute("""
            SELECT SUM(Fine_amt)
            FROM FINES F
            JOIN BOOK_LOANS BL ON F.Loan_id = BL.Loan_id
            WHERE BL.Card_id = ?
                AND F.Paid = 0
        """, (card_id,))
        due_fines = self.cur.fetchone()[0]
        if due_fines is not None and due_fines > 0:
            print(f"ERROR: Borrower has fines due (${due_fines:.2f})")
            return False
        
        # checking if the borrower has less than 3 active loans
        self.cur.execute("""
        SELECT COUNT(*)
        FROM BOOK_LOANS
        WHERE Card_id = ? 
            AND Date_in IS NULL
        """, (card_id,))
        active_loans = self.cur.fetchone()[0]
        if active_loans >= 3:
            print("ERROR: Borrower has reached the maximum loans permissible")
            return False
        
        # checking if the book exists
        self.cur.execute("SELECT * FROM BOOK WHERE Isbn = ?", (isbn,))
        book = self.cur.fetchone()
        if book is None:
            print("ERROR: Book does not exist.")
            return False
        
        # checking the book's availability
        self.cur.execute("""
        SELECT * FROM BOOK_LOANS
        WHERE Isbn = ? 
            AND Date_in IS NULL
        """, (isbn,))
        loan = self.cur.fetchone()
        if loan is not None:
            print("ERROR: Book has been checked out.")
            return False
        
        # the book is checked out and a 14 day due date is assigned
        self.cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now'), DATE('now', '+14 days'), NULL)
        """, (isbn, card_id))
        self.conn.commit()
        print("Checkout successful")
        return True
        
    def checkin_book(self, loan_id):
        print()
    def update_fines(self):
        print()
    def pay_fines(self, card_id):
        print()
