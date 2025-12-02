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
    """Return (isbns, card_id, ssn) where isbns is a list of up to 3 existing ISBNs."""
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

    # Get all existing SSNs so we can generate a unique one
    cur.execute("SELECT Ssn FROM BORROWER;")
    existing_ssns = {row[0] for row in cur.fetchall()}

    # Generate a new SSN that is guaranteed not to exist yet
    base_ssn_num = 999990000
    new_ssn = None
    while True:
        candidate = f"{base_ssn_num:09d}"        # e.g. "999990000"
        formatted = f"{candidate[0:3]}-{candidate[3:5]}-{candidate[5:9]}"  # "999-99-0000"
        if formatted not in existing_ssns:
            new_ssn = formatted
            break
        base_ssn_num += 1

    name = "Test User"
    address = "123 Test St, Dallas, TX"
    phone = "(000) 000-0000"

    # First: create a new borrower with a truly new SSN
    card_id = db.create_borrower(new_ssn, name, address, phone)
    print("New borrower Card_id (should NOT be None):", card_id)

    # Verify row exists
    if card_id is not None:
        cur.execute("SELECT Ssn, Bname FROM BORROWER WHERE Card_id = ?", (card_id,))
        print("Borrower row:", cur.fetchone())

    # Second: attempt to create another borrower reusing an existing SSN
    cur.execute("SELECT Ssn FROM BORROWER LIMIT 1;")
    existing_ssn = cur.fetchone()[0]

    dup_card_id = db.create_borrower(existing_ssn, "Dup User", "Somewhere", "(111) 111-1111")
    print("Duplicate SSN attempt Card_id (should be None):", dup_card_id)


# ===========================
# checkout_book TESTS (error paths + implicit success)
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

    # First checkout should succeed (happy-path success)
    print("  First checkout (should be True):")
    first = db.checkout_book(isbn, card_id)
    print("  Result:", first)

    # Second checkout of the same book should fail
    print("  Second checkout of same book (should be False):")
    second = db.checkout_book(isbn, card_id)
    print("  Result:", second)

# ===========================
# checkin_book TESTS (query + selections) – SUCCESS CASES
# ===========================

def test_checkin_book_by_card_id(db: LibraryDB):
    print("\n[CHECKIN TEST] query by Card_id + selections")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    # Create 3 active loans (Date_in = NULL) for this borrower
    for i in range(3):
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-5 days'), DATE('now', '+9 days'), NULL)
        """, (isbns[i % len(isbns)], card_id))
    db.conn.commit()

    # Use Card_id as the search query so all 3 loans show up
    result = db.checkin_book(card_id, [1, 2, 3])
    print("  Result of 3-book check-in (should be True):", result)

    # Verify all loans for this borrower are checked in
    cur.execute("""
        SELECT Loan_id, Date_in
        FROM BOOK_LOANS
        WHERE Card_id = ?
        ORDER BY Loan_id
    """, (card_id,))
    rows = cur.fetchall()
    print("  Loan rows after check-in:", rows)

    all_checked_in = all(date_in is not None for (_loan_id, date_in) in rows)
    print("  All loans checked in:", all_checked_in)


def test_checkin_book_by_isbn(db: LibraryDB):
    print("\n[CHECKIN TEST] query by ISBN + selections")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    isbn = isbns[0]

    # Create 2 active loans for this borrower, same ISBN
    for _ in range(2):
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-5 days'), DATE('now', '+9 days'), NULL)
        """, (isbn, card_id))
    db.conn.commit()

    # Confirm these loans exist and capture their IDs for verification
    cur.execute("""
        SELECT Loan_id
        FROM BOOK_LOANS
        WHERE Card_id = ? AND Isbn = ? AND Date_in IS NULL
        ORDER BY Loan_id
    """, (card_id, isbn))
    loan_ids_before = [row[0] for row in cur.fetchall()]
    print("  Loan_ids before check-in (ISBN match):", loan_ids_before)

    # Use ISBN as the search query; both loans should appear in results
    result = db.checkin_book(isbn, [1, 2])
    print("  Result of ISBN-based check-in (should be True):", result)

    # Verify both of those specific Loan_ids are now checked in
    cur.execute("""
        SELECT Loan_id, Date_in
        FROM BOOK_LOANS
        WHERE Loan_id IN ({})
        ORDER BY Loan_id
    """.format(",".join("?" * len(loan_ids_before))), loan_ids_before)
    rows = cur.fetchall()
    print("  Loan rows after check-in by ISBN:", rows)

    all_checked_in = all(date_in is not None for (_loan_id, date_in) in rows)
    print("  All loans checked in (ISBN query):", all_checked_in)


def test_checkin_book_by_borrower_name(db: LibraryDB):
    print("\n[CHECKIN TEST] query by borrower name substring + selections")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    # Get this borrower's name so we can use a substring
    cur.execute("SELECT Bname FROM BORROWER WHERE Card_id = ?", (card_id,))
    row = cur.fetchone()
    if row is None:
        print("  No borrower found for Card_id; cannot run name test.")
        return

    full_name = row[0]
    # take a substring, e.g., first 3 characters, lowercased
    name_substring = full_name[:3].lower()
    print(f"  Using borrower name='{full_name}', substring query='{name_substring}'")

    # Create 2 active loans for this borrower, possibly different books
    for i in range(2):
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-3 days'), DATE('now', '+11 days'), NULL)
        """, (isbns[i % len(isbns)], card_id))
    db.conn.commit()

    # Confirm the active loans for this borrower
    cur.execute("""
        SELECT Loan_id
        FROM BOOK_LOANS
        WHERE Card_id = ? AND Date_in IS NULL
        ORDER BY Loan_id
    """, (card_id,))
    loan_ids_before = [row[0] for row in cur.fetchall()]
    print("  Loan_ids before check-in (name match):", loan_ids_before)

    # Use the borrower name substring as the search query
    # Both loans for this borrower should appear in results
    result = db.checkin_book(name_substring, [1, 2])
    print("  Result of name-based check-in (should be True):", result)

    # Verify those loan_ids are now checked in
    if loan_ids_before:
        cur.execute("""
            SELECT Loan_id, Date_in
            FROM BOOK_LOANS
            WHERE Loan_id IN ({})
            ORDER BY Loan_id
        """.format(",".join("?" * len(loan_ids_before))), loan_ids_before)
        rows = cur.fetchall()
        print("  Loan rows after check-in by name:", rows)

        all_checked_in = all(date_in is not None for (_loan_id, date_in) in rows)
        print("  All loans checked in (name query):", all_checked_in)
    else:
        print("  No loans found to verify after name-based check-in.")

# ===========================
# checkin_book TESTS – FAILURE PATHS
# ===========================

def test_checkin_book_no_matching_loans(db: LibraryDB):
    """
    No BOOK_LOANS rows exist or none match the query → should return False.
    """
    print("\n[CHECKIN FAIL TEST] no matching loans for query")

    reset_loans_and_fines(db)
    # No loans at all; any query should yield "No active loans match this search."
    result = db.checkin_book("does_not_match_anything", [1])
    print("  Result (should be False):", result)


def test_checkin_book_no_selections(db: LibraryDB):
    """
    There are matching loans but selections list is empty → should return False.
    """
    print("\n[CHECKIN FAIL TEST] no selections provided")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    # Create 1 active loan
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, DATE('now', '-2 days'), DATE('now', '+12 days'), NULL)
    """, (isbns[0], card_id))
    db.conn.commit()

    # Query by card_id (will match), but pass empty selections
    result = db.checkin_book(card_id, [])
    print("  Result (should be False):", result)

    # Ensure loan is still out
    cur.execute("SELECT Date_in FROM BOOK_LOANS WHERE Card_id = ?;", (card_id,))
    row = cur.fetchone()
    print("  Loan Date_in after failed check-in (should be None):", row[0])


def test_checkin_book_too_many_selections(db: LibraryDB):
    """
    More than 3 selections → should return False, no books checked in.
    """
    print("\n[CHECKIN FAIL TEST] too many selections (>3)")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    # Create exactly 3 active loans
    for i in range(3):
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-3 days'), DATE('now', '+11 days'), NULL)
        """, (isbns[i % len(isbns)], card_id))
    db.conn.commit()

    # Pass 4 selections (invalid); function should reject before mapping them
    result = db.checkin_book(card_id, [1, 2, 3, 4])
    print("  Result (should be False):", result)

    # Verify all loans are still out
    cur.execute("""
        SELECT Loan_id, Date_in
        FROM BOOK_LOANS
        WHERE Card_id = ?
        ORDER BY Loan_id
    """, (card_id,))
    rows = cur.fetchall()
    print("  Loan rows after failed too-many selection:", rows)
    all_out = all(date_in is None for (_loan_id, date_in) in rows)
    print("  All loans still OUT (should be True):", all_out)


def test_checkin_book_selection_out_of_range(db: LibraryDB):
    """
    A selection index is outside 1..len(results) → should return False.
    """
    print("\n[CHECKIN FAIL TEST] selection number out of range")

    reset_loans_and_fines(db)
    (isbns, card_id, _ssn) = get_sample_book_and_borrower(db)
    cur = db.cur

    # Create 2 active loans
    for i in range(2):
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
            VALUES (?, ?, DATE('now', '-4 days'), DATE('now', '+10 days'), NULL)
        """, (isbns[i % len(isbns)], card_id))
    db.conn.commit()

    # There will be 2 rows; selections [1, 3] → 3 is out of range
    result = db.checkin_book(card_id, [1, 3])
    print("  Result (should be False):", result)

    # Verify loans are still out
    cur.execute("""
        SELECT Loan_id, Date_in
        FROM BOOK_LOANS
        WHERE Card_id = ?
        ORDER BY Loan_id
    """, (card_id,))
    rows = cur.fetchall()
    print("  Loan rows after out-of-range selection:", rows)
    all_out = all(date_in is None for (_loan_id, date_in) in rows)
    print("  All loans still OUT (should be True):", all_out)

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

    # Use fixed dates so the expected fine amounts are stable and easy to reason about.
    # Returned late: Due 2025-01-10, returned 2025-01-15 => 5 full days late => 5 * 0.25 = 1.25
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, '2025-01-01', '2025-01-10', '2025-01-15')
    """, (isbn1, card_id))
    loan_returned = cur.lastrowid

    # Still out and overdue: Due 2025-01-10 and still out on 'now' when update_fines runs.
    # The exact fine depends on current date but should be > 0 if today > 2025-01-10.
    cur.execute("""
        INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
        VALUES (?, ?, '2025-01-01', '2025-01-10', NULL)
    """, (isbn2, card_id))
    loan_out = cur.lastrowid

    db.conn.commit()

    # Run the fine calculation
    db.update_fines()

    # Check the returned-late loan fine: should be exactly 1.25, Paid = 0
    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_returned,))
    returned_row = cur.fetchone()
    print("  Returned-late loan FINES row:", returned_row)

    # Check the still-out overdue loan fine: should be positive, Paid = 0
    cur.execute("SELECT Fine_amt, Paid FROM FINES WHERE Loan_id = ?", (loan_out,))
    out_row = cur.fetchone()
    print("  Still-out overdue loan FINES row:", out_row)


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


def test_pay_fines_no_fines(db: LibraryDB):
    """
    Borrower has no unpaid, return-eligible fines → pay_fines should return 0.0.
    """
    print("\n[PAY FINES FAIL-LIKE TEST] no fines to pay")

    reset_loans_and_fines(db)
    (_isbns, card_id, _ssn) = get_sample_book_and_borrower(db)

    # No BOOK_LOANS / FINES created; this borrower has nothing to pay.
    total_paid = db.pay_fines(card_id)
    print("  Total paid (should be 0.0):", total_paid)

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

    print("\n=== checkout_book tests (error paths + success) ===")
    test_checkout_nonexistent_borrower(db)
    test_checkout_unpaid_fines(db)
    test_checkout_max_loans(db)
    test_checkout_nonexistent_book(db)
    test_checkout_book_already_out(db)

    print("\n=== checkin_book tests (success cases) ===")
    test_checkin_book_by_card_id(db)
    test_checkin_book_by_isbn(db)
    test_checkin_book_by_borrower_name(db)

    print("\n=== checkin_book tests (failure cases) ===")
    test_checkin_book_no_matching_loans(db)
    test_checkin_book_no_selections(db)
    test_checkin_book_too_many_selections(db)
    test_checkin_book_selection_out_of_range(db)

    print("\n=== update_fines tests ===")
    test_update_fines_returned_and_out(db)
    test_update_fines_respects_paid_and_updates_unpaid(db)

    print("\n=== pay_fines tests ===")
    test_pay_fines_behavior(db)
    test_pay_fines_no_fines(db)

    db.conn.close()


if __name__ == "__main__":
    main()
