from pathlib import Path
from init_db import initDb, DB_PATH
from library_db import LibraryDB

# ===========================
# Helpers
# ===========================

def reset_loans_and_fines(db: LibraryDB):
    """Clear BOOK_LOANS and FINES so each checkout test starts clean."""
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

    cur.execute("SELECT Card_id FROM BORROWER LIMIT 1;")
    borrower_row = cur.fetchone()
    if borrower_row is None:
        raise RuntimeError("No borrowers in BORROWER table")
    card_id = borrower_row[0]

    return isbns, card_id


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
    # Pick one: either lowercase isbn or title
    query_lower = isbn.lower()

    print(f"Using existing ISBN={isbn}, query={query_lower!r}")
    results = db.search_books(query_lower)
    print(f"Results count = {len(results)}")

# ===========================
# checkout_book TESTS (error paths)
# ===========================

def test_checkout_nonexistent_borrower(db: LibraryDB):
    print("\n[CHECKOUT TEST] Nonexistent borrower → expect False")
    reset_loans_and_fines(db)
    (isbns, _card) = get_sample_book_and_borrower(db)
    isbn = isbns[0]

    fake_card_id = "NON_EXISTENT_CARD_123"
    result = db.checkout_book(isbn, fake_card_id)
    print("Result:", result)


def test_checkout_unpaid_fines(db: LibraryDB):
    print("\n[CHECKOUT TEST] Borrower has unpaid fines → expect False")
    reset_loans_and_fines(db)
    (isbns, card_id) = get_sample_book_and_borrower(db)
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
    (isbns, card_id) = get_sample_book_and_borrower(db)

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
    (_isbns, card_id) = get_sample_book_and_borrower(db)

    fake_isbn = "FAKE_ISBN_123456"
    result = db.checkout_book(fake_isbn, card_id)
    print("Result:", result)


def test_checkout_book_already_out(db: LibraryDB):
    print("\n[CHECKOUT TEST] Book already checked out → expect False on 2nd checkout")
    reset_loans_and_fines(db)
    (isbns, card_id) = get_sample_book_and_borrower(db)
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
# MAIN
# ===========================

def main():
    initDb()

    db = LibraryDB(DB_PATH)

    print("=== search_books tests ===")
    test_search_no_results(db)
    test_search_empty_query(db)
    test_search_case_insensitive(db)

    print("\n=== checkout_book error-case tests ===")
    test_checkout_nonexistent_borrower(db)
    test_checkout_unpaid_fines(db)
    test_checkout_max_loans(db)
    test_checkout_nonexistent_book(db)
    test_checkout_book_already_out(db)

    db.conn.close()


if __name__ == "__main__":
    main()
