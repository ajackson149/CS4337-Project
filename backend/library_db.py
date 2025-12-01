

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
        print()
    def checkout_book(self, isbn, card_id):
        print()
    def checkin_book(self, loan_id):
        print()
    def update_fines(self):
        print()
    def pay_fines(self, card_id):
        print()
