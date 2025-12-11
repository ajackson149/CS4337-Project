import tkinter as tk
from tkinter import ttk, messagebox
from library_db import LibraryDB
from init_db import DB_PATH


class LibraryGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("1200x600")

        # Database
        self.db = LibraryDB(DB_PATH)

        # Logged-in borrower
        self.current_user = None

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.auth_frame = ttk.Frame(self.container)
        self.main_frame = ttk.Frame(self.container)
        self.build_auth_frame()
        self.build_main_frame()

        self.show_auth_screen()

    def show_auth_screen(self):
        self.main_frame.pack_forget()
        self.auth_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.root.title("Library - Login or Create Borrower")

    def show_main_screen(self):
        self.auth_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        if self.current_user:
            title = f"Library - {self.current_user['name']} ({self.current_user['card_id']})"
            self.root.title(title)
            self.user_label.config(
                text=f"Logged in as: {self.current_user['name']} ({self.current_user['card_id']})"
            )
            if hasattr(self, "fines_card_var"):
                self.fines_card_var.set(self.current_user["card_id"])
            if hasattr(self, "checkin_card_var"):
                self.checkin_card_var.set(self.current_user["card_id"])
        else:
            self.user_label.config(text="Not logged in")
            if hasattr(self, "fines_card_var"):
                self.fines_card_var.set("")
            if hasattr(self, "checkin_card_var"):
                self.checkin_card_var.set("")


    def build_auth_frame(self):

        self.auth_frame.columnconfigure(0, weight=1, uniform="col")
        self.auth_frame.columnconfigure(1, weight=1, uniform="col")

        # Login panel
        login_group = ttk.LabelFrame(self.auth_frame, text="Log In")
        login_group.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10),
            pady=10,
            ipadx=10,
            ipady=10,
        )

        ttk.Label(login_group, text="Card ID:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.login_card_var = tk.StringVar()
        ttk.Entry(
            login_group,
            textvariable=self.login_card_var,
            width=30,
        ).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(login_group, text="Password:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.login_password_var = tk.StringVar()
        ttk.Entry(
            login_group,
            textvariable=self.login_password_var,
            width=30,
            show="*",
        ).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Button(
            login_group,
            text="Log In",
            command=self.handle_login,
        ).grid(row=2, column=0, columnspan=2, pady=10)

        # Create borrower
        create_group = ttk.LabelFrame(self.auth_frame, text="Create New Borrower")
        create_group.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(10, 0),
            pady=10,
            ipadx=10,
            ipady=10,
        )

        labels = ["SSN:", "Name:", "Address:", "Phone:", "Password:"]
        self.new_entries = {}

        for i, label_text in enumerate(labels):
            ttk.Label(create_group, text=label_text).grid(
                row=i, column=0, sticky="w", pady=5
            )
            var = tk.StringVar()
            show_char = "*" if label_text == "Password:" else ""
            ttk.Entry(
                create_group,
                textvariable=var,
                width=35,
                show=show_char,
            ).grid(row=i, column=1, sticky="w", pady=5)
            self.new_entries[label_text] = var

        ttk.Button(
            create_group,
            text="Create Borrower",
            command=self.handle_create_borrower,
        ).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def handle_login(self):
        card_id = self.login_card_var.get().strip()
        password = self.login_password_var.get().strip()

        if not card_id or not password:
            messagebox.showerror(
                "Error",
                "Please enter both Card ID and Password.",
            )
            return

        # Authenticate the borrower
        self.db.cur.execute(
            """
            SELECT Card_id, Bname
            FROM BORROWER
            WHERE Card_id = ? AND Password = ?
            """,
            (card_id, password),
        )
        row = self.db.cur.fetchone()

        if row is None:
            messagebox.showerror(
                "Login failed",
                "Invalid Card ID or password.",
            )
            return

        # Successful login
        self.current_user = {"card_id": row[0], "name": row[1]}
        self.login_password_var.set("")  # clear password field
        self.show_main_screen()
        self.checkin_search_loans()
        self.perform_search()

    def handle_create_borrower(self):
        ssn = self.new_entries["SSN:"].get().strip()
        name = self.new_entries["Name:"].get().strip()
        address = self.new_entries["Address:"].get().strip()
        phone = self.new_entries["Phone:"].get().strip()
        password = self.new_entries["Password:"].get().strip()

        if not (ssn and name and address and phone and password):
            messagebox.showerror(
                "Error",
                "All fields, including password, are required.",
            )
            return

        # Create the borrower
        card_id = self.db.create_borrower(ssn, name, address, phone, password)
        if not card_id:
            messagebox.showerror(
                "Error",
                "Failed to create borrower. SSN already connected to an account.",
            )
            return

        # Clear the fields
        for var in self.new_entries.values():
            var.set("")

        messagebox.showinfo(
            "Borrower created",
            f"Borrower created!\n\n"
            f"Name: {name}\n"
            f"Card ID: {card_id}\n\n"
            f"You are now logged in.",
        )

        # Log in the borrower after creating
        self.current_user = {"card_id": card_id, "name": name}
        self.show_main_screen()

    # Main screen
    def build_main_frame(self):
        # SHow user info at the top
        top_bar = ttk.Frame(self.main_frame)
        top_bar.pack(fill="x", pady=(0, 10))

        self.user_label = ttk.Label(
            top_bar,
            text="Not logged in",
            font=("TkDefaultFont", 11, "bold"),
        )
        self.user_label.pack(side="left", padx=(0, 10))

        ttk.Button(
            top_bar,
            text="Log Out",
            command=self.logout,
        ).pack(side="right")

        # Separator
        ttk.Separator(self.main_frame, orient="horizontal").pack(
            fill="x",
            pady=5,
        )

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Search and check out
        search_tab = ttk.Frame(self.notebook)
        self.notebook.add(search_tab, text="Search & Checkout")
        self.build_search_tab(search_tab)

        # Check in the book
        checkin_tab = ttk.Frame(self.notebook)
        self.notebook.add(checkin_tab, text="Check In Book")
        self.build_checkin_tab(checkin_tab)

        # Fines tab
        fines_tab = ttk.Frame(self.notebook)
        self.notebook.add(fines_tab, text="Fines")
        self.build_fines_tab(fines_tab)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    # Search and CHeckout
    def build_search_tab(self, parent):
        search_frame = parent

        ttk.Label(search_frame, text="Search Query:").grid(
            row=0, column=0, sticky="w", pady=5, padx=5
        )
        self.search_var = tk.StringVar()
        ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=50,
        ).grid(row=0, column=1, sticky="w", pady=5, padx=5)

        ttk.Button(
            search_frame,
            text="Search",
            command=self.perform_search,
        ).grid(row=0, column=2, sticky="w", pady=5, padx=5)

        # Results table
        columns = ("isbn", "title", "authors", "status", "holder")
        self.results_tree = ttk.Treeview(
            search_frame,
            columns=columns,
            show="headings",
            height=15,
        )
        self.results_tree.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=5,
            padx=5,
        )

        self.results_tree.heading("isbn", text="ISBN")
        self.results_tree.heading("title", text="Title")
        self.results_tree.heading("authors", text="Authors")
        self.results_tree.heading("status", text="Status")
        self.results_tree.heading("holder", text = "Card ID")

        self.results_tree.column("isbn", width=120, anchor="w")
        self.results_tree.column("title", width=260, anchor="w")
        self.results_tree.column("authors", width=260, anchor="w")
        self.results_tree.column("status", width=80, anchor="center")
        self.results_tree.column("holder", width=120, anchor="center")

        # Make treeview expandable
        search_frame.rowconfigure(1, weight=1)
        search_frame.columnconfigure(1, weight=1)

        # Checkout button
        ttk.Button(
            search_frame,
            text="Checkout Selected Book",
            command=self.checkout_selected_book,
        ).grid(row=2, column=0, columnspan=3, pady=10)

    def perform_search(self):
        query = self.search_var.get().strip()
        results = self.db.search_books(query)

        # Clear old rows
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Insert new rows
        for book in results:
            holder = ""

            # If the book is OUT, find which Card_id currently has it
            if book["status"] == "OUT":
                self.db.cur.execute(
                    """
                    SELECT Card_id
                    FROM BOOK_LOANS
                    WHERE Isbn = ? AND Date_in IS NULL
                    ORDER BY Date_out DESC
                    LIMIT 1
                    """,
                    (book["isbn"],),
                )
                row = self.db.cur.fetchone()
                if row:
                    holder = row[0]

            self.results_tree.insert(
                "",
                "end",
                values=(
                    book["isbn"],
                    book["title"],
                    book["authors"],
                    book["status"],
                    holder,  # new column
                ),
            )


    def checkout_selected_book(self):
        if not self.current_user:
            messagebox.showerror(
                "Not logged in",
                "You must log in to checkout a book.",
            )
            return

        selected = self.results_tree.selection()
        if not selected:
            messagebox.showerror(
                "No selection",
                "Please select a book to checkout.",
            )
            return
        if len(selected) > 1:
            messagebox.showerror(
                "Multiple selections",
                "Please select only one book.",
            )
            return

        item_id = selected[0]
        values = self.results_tree.item(item_id, "values")
        isbn = values[0]
        status = values[3]

        if status == "OUT":
            messagebox.showerror(
                "Unavailable",
                "That book is already checked out.",
            )
            return

        success = self.db.checkout_book(isbn, self.current_user["card_id"])
        if success:
            messagebox.showinfo(
                "Success",
                f"Book {isbn} checked out successfully!",
            )
            self.perform_search()  # refresh status
        else:
            messagebox.showerror(
                "Error",
                "Checkout failed. Maximum loans reached.",
            )

    # Check In the book
    def build_checkin_tab(self, parent):
        frame = parent

        ttk.Label(
            frame,
            text="Logged In Card ID:",
        ).grid(row=0, column=0, sticky="w", pady=5, padx=5)

        self.checkin_card_var = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.checkin_card_var,
            width=40,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Treeview for showing loans (similar style to Search & Checkout)
        columns = (
            "isbn",
            "title",
            "authors",
            "borrower",
            "card_id",
            "date_out",
            "due_date",
        )
        self.checkin_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=12,
            selectmode="extended",  # allow multi-select check-in
        )
        self.checkin_tree.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=5,
            padx=5,
        )

        # Headings
        self.checkin_tree.heading("isbn", text="ISBN")
        self.checkin_tree.heading("title", text="Title")
        self.checkin_tree.heading("authors", text="Author(s)")
        self.checkin_tree.heading("borrower", text="Name")
        self.checkin_tree.heading("card_id", text="Card ID")
        self.checkin_tree.heading("date_out", text="Out")
        self.checkin_tree.heading("due_date", text="Due")

        # Column widths
        self.checkin_tree.column("isbn", width=110, anchor="w")
        self.checkin_tree.column("title", width=180, anchor="w")
        self.checkin_tree.column("authors", width=170, anchor="w")
        self.checkin_tree.column("borrower", width=150, anchor="w")
        self.checkin_tree.column("card_id", width=90, anchor="center")
        self.checkin_tree.column("date_out", width=80, anchor="center")
        self.checkin_tree.column("due_date", width=80, anchor="center")

        # Make treeview expandable
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Button(
            frame,
            text="Check In Selected Loans",
            command=self.checkin_selected_loans,
        ).grid(row=2, column=1, sticky="e", pady=5, padx=5)

        # Store last search query so we can pass it to checkin_book
        self.checkin_last_query = ""


        # Make listbox expandable
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        self.checkin_last_query = ""


    def checkin_search_loans(self):
        if not self.current_user:
            messagebox.showerror(
                "Not logged in",
                "You must log in to check in books.",
            )
            return

        # Use the logged-in borrower's Card ID as the search query
        query = self.current_user["card_id"]
        self.checkin_last_query = query

        # Clear the tree
        for item in self.checkin_tree.get_children():
            self.checkin_tree.delete(item)

        loans = self.db.find_loans_for_checkin(query)

        for loan in loans:
            isbn = loan["isbn"]

            # 🔹 Inline query to get authors for this ISBN
            self.db.cur.execute(
                """
                SELECT GROUP_CONCAT(A.Name, ', ')
                FROM BOOK_AUTHORS BA
                JOIN AUTHORS A ON BA.Author_id = A.Author_id
                WHERE BA.Isbn = ?
                """,
                (isbn,),
            )
            row = self.db.cur.fetchone()
            authors = row[0] if row and row[0] is not None else ""

            # Insert row into the check-in tree
            self.checkin_tree.insert(
                "",
                "end",
                values=(
                    isbn,
                    loan["title"],
                    authors,
                    loan["borrower_name"],
                    loan["card_id"],
                    loan["date_out"],
                    loan["due_date"],
                ),
            )


    def checkin_selected_loans(self):
        if not self.current_user:
            messagebox.showerror(
                "Not logged in",
                "You must be logged in to check in books.",
            )
            return

        selected_items = self.checkin_tree.selection()
        if not selected_items:
            messagebox.showerror(
                "Error",
                "Please select at least one loan to check in.",
            )
            return

        # Map selected tree rows to 1-based positions expected by checkin_book()
        all_items = list(self.checkin_tree.get_children())
        selections = []
        for item_id in selected_items:
            idx = all_items.index(item_id)  # 0-based
            selections.append(idx + 1)      # convert to 1-based

        query = self.checkin_last_query or self.current_user["card_id"]

        success = self.db.checkin_book(query, selections)
        if success:
            messagebox.showinfo(
                "Success",
                "Books successfully checked in.",
            )
            # Refresh list of OUT loans
            self.checkin_search_loans()
        else:
            messagebox.showerror(
                "Error",
                "Check-in failed. See console output for details.",
            )



    # Tab to pay fines
    def build_fines_tab(self, parent):
        frame = parent

        ttk.Label(frame, text="Borrower Card ID (logged in user):").grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
            padx=5,
        )

        self.fines_card_var = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.fines_card_var,
            width=30,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", pady=5, padx=5)

        ttk.Button(
            frame,
            text="Update All Fines",
            command=self.handle_update_fines,
        ).grid(row=1, column=0, sticky="w", pady=10, padx=5)

        ttk.Button(
            frame,
            text="Pay My Fines",
            command=self.handle_pay_fines,
        ).grid(row=1, column=1, sticky="w", pady=10, padx=5)

    def handle_update_fines(self):
        self.db.update_fines()
        messagebox.showinfo(
            "Fines Updated",
            "Fines have been recalculated.",
        )

    def handle_pay_fines(self):
        if not self.current_user:
            messagebox.showerror(
                "Not logged in",
                "You must be logged in to pay fines.",
            )
            return

        card_id = self.current_user["card_id"]
        amount = self.db.pay_fines(card_id)

        if amount is None or amount == 0.0:
            messagebox.showinfo(
                "No Fines",
                "You have no unpaid fines for returned books.",
            )
        else:
            messagebox.showinfo(
                "Fines Paid",
                f"Paid ${amount:.2f} in fines.",
            )
    def on_tab_changed(self, event):
        if not self.current_user:
            return
        self.checkin_search_loans()
        self.perform_search()
        

    # Log the use out
    def logout(self):
        self.current_user = None
        self.login_card_var.set("")
        self.login_password_var.set("")
        if hasattr(self, "fines_card_var"):
            self.fines_card_var.set("")
        self.show_auth_screen()


def main():
    root = tk.Tk()
    app = LibraryGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
