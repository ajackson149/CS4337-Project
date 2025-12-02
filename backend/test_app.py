from pathlib import Path
from init_db import initDb, DB_PATH
from library_db import LibraryDB
import datetime

# ===========================
# Helpers
# ===========================

def reset_loans_and_fines(db: LibraryDB):
    """Clear BOOK_LOANS and FINES so each checkout/fine test starts clean."""
    cur = db.cur
    cur.execute("DELETE FROM FINES;")
    cur.execute("DELETE FROM BOOK_LOANS;")
    db.conn.commit()


def get_sample_book_and_borrower(db: LibraryDB):
    """Return (isbns, card_id) where isbns is a list of up to 3 existing ISBNs."""
    cur = db.cur

    cur.execute("SELECT Isbn FROM BOOK LIMIT 3;")
    book_rows = cur.fetchall()
    if len(book_rows) == 0:
        raise RuntimeError("No books in BOOK table")
    isbns = [r[0] for r in book_rows]

    cur.execute("SELECT Card_id, Ssn FROM BORROWER LIMIT 1;")
    borrower_row = cur.fetchone()
    if borrower_row is None:
        raise RuntimeError("No borrowers in BORROWER table")
    card_id = borrower_row[0]
    ssn = borrower_row[1]

    return isbns, card_id, ssn

# ===========================
# search_books TESTS
# ===========================

def test_search_no_results(db: LibraryDB):
    """Query that should return zero rows."""
    print("\n[SEARCH TEST] No results expected")
    query = "this_should_match_nothing"
    results = db.search_books(query)
    print(f"Query: {query!r}, results count = {len(results)}")


def test_search_empty_query(db: LibraryDB):
    """Empty string should not crash; show only first 5 results."""
    print("\n[SEARCH TEST] Empty string query (should return many results, but only show 5)")

    query = ""
    results = db.search_books(query)

    total = len(results)
    print(f"Total results returned: {total}")

    # Show only first 5
    print("\nShowing first 5 results:\n")
    for i, book in enumerate(results[:5], start=1):
        print(f"{i}. {book['isbn']} | {book['title']} | {book['authors']} | {book['status']}")


def test_search_case_insensitive(db: LibraryDB):
    """
    Show that search is case-insensitive by taking an existing title/ISBN and
    searching with different case.
    """
    print("\n[SEARCH TEST] Case-insensitive behavior")

    cur = db.cur
    cur.execute("SELECT Isbn, Title FROM BOOK LIMIT 1;")
    row = cur.fetchone()
    if row is None:
        print("No books in BOOK table – cannot run case-insensitive test.")
        return

    isbn, title = row
    query_lower = isbn.lower()

    print(f"Using existing ISBN={isbn}, query={query_lower!r}")
    results = db.search_books(query_lower)
    print(f"Results count = {len(results)}")

# ===========================
# create_borrower TESTS
# ===========================

def test_create_borrower_success_and_duplicate(db: LibraryDB):
    print("\n[BORROWER TEST] Create borrower and enforce unique SSN")

    cur = db.cur

    # Get an SSN that already exists
    cur.execute("SELECT Ssn FROM BORROWER LIMIT 1;")
    row = cur.fetchone()
    existing_ssn = row[0]

    # First: create a new borrower with a new SSN
    new_ssn = "999-99-0001"
    name = "Test User"
    address = "123 Test St, Dallas, TX"
    phone = "(000) 000-0000"

    card_id = db.create_borrower(new_ssn, name, address, phone)
    print("New borrower Card_id (should NOT be None):", card_id)

    # Verify row exists
    if card_id is not None:
        cur.execute("SELECT Ssn, Bname FROM BORROWER WHERE Card_id = ?", (card_id,))
        print("Borrower row:", cur.fetchone())

    # Second: attempt to create another borrower reusing an existing SSN
    dup_card_id = db.create_borrower(existing_ssn, "Dup User", "Somewhere", "(111) 111-1111")
    print("Duplicate SSN attempt Card_id (should be None):", dup_card_id)

# ===========================
# checkout_book TESTS (error paths)
# ===========================

def test_checkout_nonexistent_borrower(db: LibraryDB):
    print("\n[CHECKOUT TEST] Nonexistent borrower → expect False")
    reset_loans_and_fines(db)
    (isbns, _card, _ssn) = get_sample_book_and_borrower(db)
    isbn = isbns[0]

    fake_card_id = "NON_EXISTENT_CARD_123"
    result = db.checkout_book(isbn, fake_card_id)
    print("Result:", result)


def test_checkout_unpaid_fines(db: LibraryDB):
    print("\n[CHECKOUT TEST] Borrower has unpaid fines → expect False")
    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn = isbns[0]

    cur = db.cur

    # Create an old loan for this borrower
    cur.execute(
        """
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now', '-20 days'), DATE('now', '-10 days'), DATE('now', '-5 days'))
        """,
        (isbn, card_id),
    )
    loan_id = cur.lastrowid

    # Create an unpaid fine for that loan
    cur.execute(
        """
        INSERT INTO FINES (Loan_id, Fine_amt, Paid)
        VALUES (?, ?, 0)
        """,
        (loan_id, 10),
    )
    db.conn.commit()

    # Now try to check out ANY book for this borrower
    result = db.checkout_book(isbn, card_id)
    print("Result:", result)


def test_checkout_max_loans(db: LibraryDB):
    print("\n[CHECKOUT TEST] Borrower already has 3 active loans → expect False")
    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)

    cur = db.cur

    # Ensure we have at least 3 different ISBNs; reuse last if fewer
    while len(isbns) < 3:
        isbns.append(isbns[-1])

    # Create 3 active loans (Date_in is NULL)
    for i in range(3):
        cur.execute(
            """
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-1 day'), DATE('now', '+13 days'), NULL)
            """,
            (isbns[i], card_id),
        )
    db.conn.commit()

    # Try to check out another book for this borrower
    result = db.checkout_book(isbns[0], card_id)
    print("Result:", result)


def test_checkout_nonexistent_book(db: LibraryDB):
    print("\n[CHECKOUT TEST] Nonexistent book → expect False")
    reset_loans_and_fines(db)
    (_isbns, card_id, _ssn) = get_sample_book_and_borrower(db)

    fake_isbn = "FAKE_ISBN_123456"
    result = db.checkout_book(fake_isbn, card_id)
    print("Result:", result)


def test_checkout_book_already_out(db: LibraryDB):
    print("\n[CHECKOUT TEST] Book already checked out → expect False on 2nd checkout")
    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn = isbns[0]

    # First checkout should succeed
    print("  First checkout (should be True):")
    first = db.checkout_book(isbn, card_id)
    print("  Result:", first)

    # Second checkout of the same book should fail
    print("  Second checkout of same book (should be False):")
    second = db.checkout_book(isbn, card_id)
    print("  Result:", second)

# ===========================
# checkin_book TESTS
# ===========================

def test_checkin_book_success_and_errors(db: LibraryDB):
    print("\n[CHECKIN TEST] Check-in success, non-existent loan, and already checked-in")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn = isbns[0]
    cur = db.cur

    # Create a loan that is currently out
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now', '-5 days'), DATE('now', '+9 days'), NULL)
    """, (isbn, card_id))
    loan_id = cur.lastrowid
    db.conn.commit()

    # 1) Successful check-in
    result1 = db.checkin_book(loan_id)
    print("  Check-in result (should be True):", result1)

    # 2) Attempt to check in again (already checked in)
    result2 = db.checkin_book(loan_id)
    print("  Second check-in (should be False):", result2)

    # 3) Non-existent loan id
    fake_loan_id = loan_id + 9999
    result3 = db.checkin_book(fake_loan_id)
    print("  Non-existent Loan_id check-in (should be False):", result3)

# ===========================
# update_fines TESTS
# ===========================

def test_update_fines_returned_and_out(db: LibraryDB):
    print("\n[FINES TEST] update_fines on returned-late and still-out loans")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn1 = isbns[0]
    isbn2 = isbns[1] if len(isbns) > 1 else isbns[0]
    cur = db.cur

    # 1) Returned late: Due 10 days ago, returned 5 days ago => 5 days late => 1.25
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now', '-20 days'), DATE('now', '-10 days'), DATE('now', '-5 days'))
    """, (isbn1, card_id))
    loan_returned = cur.lastrowid

    # 2) Still out and overdue: Due 4 days ago => ~4 * 0.25 = 1.00
    today = datetime.date.today()
    due_date = today - datetime.timedelta(days=4)
    date_out = due_date - datetime.timedelta(days=10)

    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, ?, ?, NULL)
    """, (isbn2, card_id, date_out.isoformat(), due_date.isoformat()))
    loan_out = cur.lastrowid
    db.conn.commit()

    db.update_fines()

    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_returned,))
    print("  Returned-late loan FINES row:", cur.fetchone())

    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_out,))
    print("  Still-out overdue loan FINES row:", cur.fetchone())


def test_update_fines_respects_paid_and_updates_unpaid(db: LibraryDB):
    print("\n[FINES TEST] update_fines respects Paid flag and updates unpaid fines")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn = isbns[0]
    cur = db.cur

    # Loan returned 10 days late -> fine should be 10 * 0.25 = 2.50
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, '2025-01-01', '2025-01-10', '2025-01-20')
    """, (isbn, card_id))
    loan_id = cur.lastrowid
    db.conn.commit()

    # Existing Paid=1 fine (should not change)
    cur.execute(
        "INSERT INTO FINES (Loan_id, Fine_amt, Paid) VALUES (?, ?, 1)",
        (loan_id, 0.50)
    )
    db.conn.commit()

    db.update_fines()
    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_id,))
    print("  After update_fines, Paid=1 fine row (should stay 0.50,1):", cur.fetchone())

    # Now mark as unpaid with wrong amount and run again
    cur.execute("UPDATE FINES SET Fine_amt = ?, Paid = 0 WHERE Loan_id = ?", (1.00, loan_id))
    db.conn.commit()

    db.update_fines()
    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_id,))
    print("  After update_fines, unpaid fine row (should be updated to correct amount):", cur.fetchone())

# ===========================
# pay_fines TESTS
# ===========================

def test_pay_fines_behavior(db: LibraryDB):
    print("\n[PAY FINES TEST] pay_fines on various loans")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    isbn1 = isbns[0]
    isbn2 = isbns[1] if len(isbns) > 1 else isbns[0]
    cur = db.cur

    # Loan 1: returned late (should be payable)
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, '2025-01-01', '2025-01-10', '2025-01-20')
    """, (isbn1, card_id))
    loan1 = cur.lastrowid

    # Loan 2: still out overdue (should NOT be payable yet)
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now', '-15 days'), DATE('now', '-5 days'), NULL)
    """, (isbn2, card_id))
    loan2 = cur.lastrowid
    db.conn.commit()

    # Compute fines first
    db.update_fines()

    print("  Before pay_fines:")
    cur.execute("SELECT Loan_id, Fine_amt, Paid FROM FINES")
    print("   FINES rows:", cur.fetchall())

    total_paid = db.pay_fines(card_id)
    print("  Total paid (should match only returned-loan fines):", total_paid)

    print("  After pay_fines:")
    cur.execute("SELECT Loan_id, Fine_amt, Paid FROM FINES")
    print("   FINES rows:", cur.fetchall())

# ===========================
# MAIN
# ===========================

def main():
    initDb()

    db = LibraryDB(DB_PATH)

    print("=== search_books tests ===")
    test_search_no_results(db)
    test_search_empty_query(db)
    test_search_case_insensitive(db)

    print("\n=== create_borrower tests ===")
    test_create_borrower_success_and_duplicate(db)

    print("\n=== checkout_book error-case tests ===")
    test_checkout_nonexistent_borrower(db)
    test_checkout_unpaid_fines(db)
    test_checkout_max_loans(db)
    test_checkout_nonexistent_book(db)
    test_checkout_book_already_out(db)

    print("\n=== checkin_book tests ===")
    test_checkin_book_success_and_errors(db)

    print("\n=== update_fines tests ===")
    test_update_fines_returned_and_out(db)
    test_update_fines_respects_paid_and_updates_unpaid(db)

    print("\n=== pay_fines tests ===")
    test_pay_fines_behavior(db)

    db.conn.close()


if __name__ == "__main__":
    main()
