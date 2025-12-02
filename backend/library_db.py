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

    # -------------------------------------------------
    # Borrower creation
    # -------------------------------------------------
    def create_borrower(self, ssn: str, name: str, address: str, phone: str):
        """
        Create a new borrower in BORROWER.

        - SSN must be unique.
        - Card_id is auto-generated in the form IDXXXXXX.
        Returns the new Card_id on success, or None on failure.
        """
        ssn = ssn.strip()
        name = name.strip()
        address = address.strip()
        phone = phone.strip()

        # Check SSN uniqueness
        self.cur.execute("SELECT 1 FROM BORROWER WHERE Ssn = ?", (ssn,))
        if self.cur.fetchone() is not None:
            print("ERROR: A borrower with this SSN already exists.")
            return None

        # Generate next Card_id based on max existing
        self.cur.execute("SELECT MAX(Card_id) FROM BORROWER;")
        row = self.cur.fetchone()
        max_card = row[0]

        if max_card is None:
            next_num = 1
        else:
            try:
                next_num = int(max_card[2:]) + 1
            except ValueError:
                # Fallback if existing IDs are weird
                next_num = 1

        card_id = f"ID{next_num:06d}"

        self.cur.execute(
            """
            INSERT INTO BORROWER (Card_id, Ssn, Bname, Address, Phone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (card_id, ssn, name, address, phone),
        )
        self.conn.commit()
        print(f"Borrower created with Card_id={card_id}")
        return card_id

    # -------------------------------------------------
    # Search books
    # -------------------------------------------------
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
        return results

    # -------------------------------------------------
    # Checkout
    # -------------------------------------------------
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
            return False

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

        # -------------------------------------------------
    # Check-in (interactive: search + select up to 3)
    # -------------------------------------------------
    def checkin_book(self, query, selections):
        search = f"%{query.lower()}%"

        sql = """
        SELECT BL.Loan_id, BL.Isbn, B.Title, BL.Card_id, BR.Bname, BL.Date_out, BL.Due_date
        FROM BOOK_LOANS BL
        JOIN BOOK B ON BL.Isbn = B.Isbn
        JOIN BORROWER BR ON BL.Card_id = BR.Card_id
        WHERE BL.Date_in IS NULL
        AND (LOWER(BL.Isbn) LIKE ?
            OR LOWER(BL.Card_id) LIKE ?
            OR LOWER(BR.Bname) LIKE ?)
        ORDER BY BL.Date_out;
        """

        self.cur.execute(sql, (search, search, search))
        rows = self.cur.fetchall()

        # No matching loans
        if len(rows) == 0:
            print("No active loans match this search.")
            return False

        # Convert rows to dictionaries
        results = []
        for row in rows:
            results.append({
                "loan_id": row[0],
                "isbn": row[1],
                "title": row[2],
                "card_id": row[3],
                "borrower_name": row[4],
                "date_out": row[5],
                "due_date": row[6]
            })

        # Validate selections are 1-based row numbers
        if len(selections) == 0:
            print("Error: No selections provided.")
            return False

        if len(selections) > 3:
            print("Error: Cannot check in more than 3 books.")
            return False

        if any(s < 1 or s > len(results) for s in selections):
            print("Error: Selection number out of range.")
            return False

        # Map selections (1-based index) to loan_ids
        loan_ids = [results[s-1]["loan_id"] for s in selections]

        # Check in each selected loan
        for loan_id in loan_ids:
            self.cur.execute("""
                UPDATE BOOK_LOANS
                SET Date_in = DATE('now')
                WHERE Loan_id = ?
            """, (loan_id,))
        self.conn.commit()

        # Update fines after check-in
        self.update_fines()

        print("Books successfully checked in.")
        return True

    
        # -------------------------------------------------
    # Check-in search helper (for locating loans)
    # -------------------------------------------------
    def find_loans_for_checkin(self, query):
        """
        Locate BOOK_LOANS tuples that are currently OUT (Date_in IS NULL)
        by searching on any of:
          - BOOK.Isbn
          - BORROWER.Card_id
          - any substring of BORROWER.Bname

        Returns a list of dicts:
          {
            "loan_id": int,
            "isbn": str,
            "title": str,
            "card_id": str,
            "borrower_name": str,
            "date_out": str,
            "due_date": str,
          }
        """
        search = f"%{query.lower()}%"

        sql = """
        SELECT
            BL.Loan_id,
            BL.Isbn,
            B.Title,
            BL.Card_id,
            BR.Bname,
            BL.Date_out,
            BL.Due_date
        FROM BOOK_LOANS BL
        JOIN BOOK B ON BL.Isbn = B.Isbn
        JOIN BORROWER BR ON BL.Card_id = BR.Card_id
        WHERE
            BL.Date_in IS NULL
            AND (
                LOWER(B.Isbn)   LIKE ?
                OR LOWER(BL.Card_id) LIKE ?
                OR LOWER(BR.Bname)   LIKE ?
            )
        ORDER BY BL.Date_out;
        """

        self.cur.execute(sql, (search, search, search))
        rows = self.cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "loan_id":       row[0],
                "isbn":          row[1],
                "title":         row[2],
                "card_id":       row[3],
                "borrower_name": row[4],
                "date_out":      row[5],
                "due_date":      row[6],
            })

        return results


    # -------------------------------------------------
    # Update fines
    # -------------------------------------------------
    def update_fines(self):
        """
        Recalculate fines for all overdue loans.

        Rules:
        - Returned late:
            fine = full_days_late * 0.25
        - Still out and overdue:
            fine = full_days_late * 0.25
        - If FINES row exists for a loan:
            - If Paid == 0, update Fine_amt.
            - If Paid == 1, leave it alone.
        - If no FINES row exists, insert one with Paid = 0.
        """

        # 1) Late books that have been returned
        self.cur.execute("""
            SELECT
                Loan_id,
                ROUND(
                    CAST(julianday(Date_in) - julianday(Due_date) AS INTEGER) * 0.25,
                    2
                ) AS Fine
            FROM BOOK_LOANS
            WHERE Date_in IS NOT NULL
            AND julianday(Date_in) > julianday(Due_date)
        """)
        returned_rows = self.cur.fetchall()

        # 2) Late books still out
        self.cur.execute("""
            SELECT
                Loan_id,
                ROUND(
                    CAST(julianday('now') - julianday(Due_date) AS INTEGER) * 0.25,
                    2
                ) AS Fine
            FROM BOOK_LOANS
            WHERE Date_in IS NULL
            AND julianday('now') > julianday(Due_date)
        """)
        out_rows = self.cur.fetchall()

        self._apply_fines(returned_rows)
        self._apply_fines(out_rows)

        self.conn.commit()
        print("Fines updated.")


    def _apply_fines(self, fine_rows):
        """
        Internal helper to apply fines rows: list of (loan_id, fine_amt)
        to the FINES table respecting Paid flag.
        """
        for loan_id, fine_amt in fine_rows:
            if fine_amt is None or fine_amt <= 0:
                continue

            self.cur.execute(
                "SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?",
                (loan_id,)
            )
            existing = self.cur.fetchone()

            if existing is None:
                # Create new fine
                self.cur.execute(
                    "INSERT INTO FINES (Loan_id, Fine_amt, Paid) VALUES (?, ?, 0)",
                    (loan_id, fine_amt)
                )
            else:
                existing_fine, paid = existing
                if paid == 0:
                    if existing_fine is None or float(existing_fine) != float(fine_amt):
                        self.cur.execute(
                            "UPDATE FINES SET Fine_amt = ? WHERE Loan_id = ?",
                            (fine_amt, loan_id)
                        )
                # If paid == 1: leave it unchanged

    # -------------------------------------------------
    # Pay fines
    # -------------------------------------------------
    def pay_fines(self, card_id: str):
        """
        Pay all unpaid fines for a borrower, but ONLY for loans that have been returned.

        - Does not allow partial payment: pays all such fines at once.
        - Still-out (Date_in IS NULL) loans are ignored (cannot be paid yet).
        Returns total amount paid (float).
        """
        card_id = card_id.strip()

        # Sum unpaid fines for this borrower where the book has been returned
        self.cur.execute("""
            SELECT SUM(F.Fine_amt)
            FROM FINES F
            JOIN BOOK_LOANS BL ON F.Loan_id = BL.Loan_id
            WHERE BL.Card_id = ?
              AND F.Paid = 0
              AND BL.Date_in IS NOT NULL
        """, (card_id,))
        total = self.cur.fetchone()[0]

        if total is None or total <= 0:
            print("No fines to pay for this borrower.")
            return 0.0

        # Mark those fines as paid
        self.cur.execute("""
            UPDATE FINES
            SET Paid = 1
            WHERE Loan_id IN (
                SELECT BL.Loan_id
                FROM BOOK_LOANS BL
                JOIN FINES F ON F.Loan_id = BL.Loan_id
                WHERE BL.Card_id = ?
                  AND F.Paid = 0
                  AND BL.Date_in IS NOT NULL
            )
        """, (card_id,))
        self.conn.commit()

        print(f"Paid ${total:.2f} in fines for Card_id={card_id}.")
        return float(total)
