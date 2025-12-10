import tkinter as tk
from tkinter import ttk, messagebox
from library_db import LibraryDB
from init_db import DB_PATH


class LibraryGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("900x600")

        # Database
        self.db = LibraryDB(DB_PATH)

        # Logged-in borrower
        self.current_user = None

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.auth_frame = ttk.Frame(self.container)
        self.main_frame = ttk.Frame(self.container)
        self._build_auth_frame()
        self._build_main_frame()

        self.show_auth_screen()

    def show_auth_screen(self):
        """Show the login / create-account screen."""
        self.main_frame.pack_forget()
        self.auth_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.root.title("Library - Login or Create Borrower")

    def show_main_screen(self):
        """Show the main screen (tabs) after login."""
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
        else:
            self.user_label.config(text="Not logged in")
            if hasattr(self, "fines_card_var"):
                self.fines_card_var.set("")


    def _build_auth_frame(self):
        """Create the start page: login on the left, sign-up on the right."""

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
        """Handle login from the start screen."""
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

    def handle_create_borrower(self):
        """Handle creation of a new borrower from the start screen."""
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
                "Failed to create borrower (SSN may already exist).",
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
    def _build_main_frame(self):
        """Build the main app screen shown after login."""
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
        self._build_search_tab(search_tab)

        # Check in the book
        checkin_tab = ttk.Frame(self.notebook)
        self.notebook.add(checkin_tab, text="Check In Book")
        self._build_checkin_tab(checkin_tab)

        # Fines tab
        fines_tab = ttk.Frame(self.notebook)
        self.notebook.add(fines_tab, text="Fines")
        self._build_fines_tab(fines_tab)

    # Search and CHeckout
    def _build_search_tab(self, parent):
        """Build the Search & Checkout tab."""
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
        columns = ("isbn", "title", "authors", "status")
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

        self.results_tree.column("isbn", width=120, anchor="w")
        self.results_tree.column("title", width=260, anchor="w")
        self.results_tree.column("authors", width=260, anchor="w")
        self.results_tree.column("status", width=80, anchor="center")

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
        """Run a search and populate the results tree."""
        query = self.search_var.get().strip()
        results = self.db.search_books(query)

        # Clear old rows
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Insert new rows
        for book in results:
            self.results_tree.insert(
                "",
                "end",
                values=(
                    book["isbn"],
                    book["title"],
                    book["authors"],
                    book["status"],
                ),
            )

    def checkout_selected_book(self):
        """Checkout the currently selected book for the logged-in borrower."""
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
                "Checkout failed. See console for details.",
            )

    # Check In the book
    def _build_checkin_tab(self, parent):
        """Build the Check In Book tab."""
        frame = parent

        ttk.Label(
            frame,
            text="Search active loans (ISBN, Card ID, or Borrower Name):",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5, padx=5)

        self.checkin_search_var = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.checkin_search_var,
            width=40,
        ).grid(row=1, column=0, sticky="w", pady=5, padx=5)

        ttk.Button(
            frame,
            text="Find Loans",
            command=self.checkin_search_loans,
        ).grid(row=1, column=1, sticky="w", pady=5, padx=5)

        # Listbox for showing loans
        self.checkin_loans_listbox = tk.Listbox(
            frame,
            width=80,
            height=12,
        )
        self.checkin_loans_listbox.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=5,
            padx=5,
        )

        # Make listbox expandable
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        # Selections entry
        ttk.Label(
            frame,
            text=(
                "Selection numbers to check in "
                "(comma-separated, e.g., 1,2):"
            ),
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=5, padx=5)

        self.checkin_selections_var = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.checkin_selections_var,
            width=30,
        ).grid(row=4, column=0, sticky="w", pady=5, padx=5)

        ttk.Button(
            frame,
            text="Check In Selected Loans",
            command=self.checkin_selected_loans,
        ).grid(row=4, column=1, sticky="w", pady=5, padx=5)

        # Store last search query so we can pass it to checkin_book
        self.checkin_last_query = ""

    def checkin_search_loans(self):
        """Search for active (OUT) loans and populate the listbox."""
        query = self.checkin_search_var.get().strip()
        self.checkin_last_query = query

        self.checkin_loans_listbox.delete(0, tk.END)

        if not query:
            messagebox.showerror(
                "Error",
                "Please enter a search query.",
            )
            return

        loans = self.db.find_loans_for_checkin(query)

        if not loans:
            self.checkin_loans_listbox.insert(
                tk.END,
                "No active loans found.",
            )
            return

        for i, loan in enumerate(loans, start=1):
            line = (
                f"{i}. {loan['title']} - {loan['borrower_name']} "
                f"(Card {loan['card_id']})  "
                f"Out: {loan['date_out']}  Due: {loan['due_date']}"
            )
            self.checkin_loans_listbox.insert(tk.END, line)

    def checkin_selected_loans(self):
        """Check in loans by their selection numbers."""
        if not self.checkin_last_query:
            messagebox.showerror(
                "Error",
                "Please search for loans before trying to check them in.",
            )
            return

        raw = self.checkin_selections_var.get().strip()
        if not raw:
            messagebox.showerror(
                "Error",
                "Please enter selection number(s) to check in.",
            )
            return

        try:
            selections = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            messagebox.showerror(
                "Error",
                "Selections must be integer numbers (e.g., 1,2,3).",
            )
            return

        if not selections:
            messagebox.showerror(
                "Error",
                "No valid selections found.",
            )
            return

        success = self.db.checkin_book(self.checkin_last_query, selections)
        if success:
            messagebox.showinfo(
                "Success",
                "Books successfully checked in.",
            )
            # Refresh the search to update the list of OUT loans
            self.checkin_search_loans()
        else:
            messagebox.showerror(
                "Error",
                "Check-in failed. See console output for details.",
            )

    # Tab to pay fines
    def _build_fines_tab(self, parent):
        """Build the Fines tab."""
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
        """Recalculate fines for all borrowers."""
        self.db.update_fines()
        messagebox.showinfo(
            "Fines Updated",
            "Fines have been recalculated.",
        )

    def handle_pay_fines(self):
        """Pay all unpaid fines for the logged-in borrower (returned books only)."""
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

    # Log the use out
    def logout(self):
        """Log the current user out and return to the start screen."""
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
