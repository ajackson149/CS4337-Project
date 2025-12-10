import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from library_db import LibraryDB
from init_db import DB_PATH

class LibraryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("800x600")
        
        # Initialize database connection
        self.db = LibraryDB(DB_PATH)
        
        # Create main notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs for different operations
        self.create_search_tab()
        self.create_checkout_tab()
        self.create_checkin_tab()
        self.create_borrower_tab()
        self.create_fines_tab()
    
    def create_search_tab(self):
        """Tab for searching books"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Search Books")
        
        ttk.Label(frame, text="Search Query:").pack(pady=5)
        search_var = tk.StringVar()
        ttk.Entry(frame, textvariable=search_var, width=50).pack(pady=5)
        
        def search():
            results = self.db.search_books(search_var.get())
            result_text.config(state="normal")
            result_text.delete(1.0, tk.END)
            for book in results:
                result_text.insert(tk.END, 
                    f"{book['isbn']} | {book['title']} | {book['authors']} | {book['status']}\n")
            result_text.config(state="disabled")
        
        ttk.Button(frame, text="Search", command=search).pack(pady=5)
        
        result_text = tk.Text(frame, height=20, width=80, state="disabled")
        result_text.pack(pady=10)
    
    def create_checkout_tab(self):
        """Tab for checking out books"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Checkout Book")
        
        ttk.Label(frame, text="ISBN:").pack(pady=5)
        isbn_var = tk.StringVar()
        ttk.Entry(frame, textvariable=isbn_var, width=30).pack(pady=5)
        
        ttk.Label(frame, text="Card ID:").pack(pady=5)
        card_var = tk.StringVar()
        ttk.Entry(frame, textvariable=card_var, width=30).pack(pady=5)
        
        def checkout():
            if self.db.checkout_book(isbn_var.get(), card_var.get()):
                messagebox.showinfo("Success", "Book checked out successfully!")
            else:
                messagebox.showerror("Error", "Checkout failed. Check console for details.")
        
        ttk.Button(frame, text="Checkout", command=checkout).pack(pady=10)
    
    def create_checkin_tab(self):
        """Tab for checking in books"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Checkin Book")
        
        ttk.Label(frame, text="Search Query:").pack(pady=5)
        search_var = tk.StringVar()
        ttk.Entry(frame, textvariable=search_var, width=50).pack(pady=5)
        
        ttk.Button(frame, text="Find Loans", command=lambda: find_loans()).pack(pady=5)
        
        loans_frame = ttk.Frame(frame)
        loans_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        loans_listbox = tk.Listbox(loans_frame, height=10)
        loans_listbox.pack(fill="both", expand=True)
        
        selections_var = tk.StringVar()
        ttk.Label(frame, text="Selection numbers (comma-separated):").pack(pady=5)
        ttk.Entry(frame, textvariable=selections_var, width=30).pack(pady=5)
        
        def find_loans():
            loans = self.db.find_loans_for_checkin(search_var.get())
            loans_listbox.delete(0, tk.END)
            for i, loan in enumerate(loans, 1):
                loans_listbox.insert(tk.END, 
                    f"{i}. {loan['title']} - {loan['borrower_name']}")
        
        def checkin():
            try:
                selections = [int(x.strip()) for x in selections_var.get().split(",")]
                if self.db.checkin_book(search_var.get(), selections):
                    messagebox.showinfo("Success", "Books checked in successfully!")
                else:
                    messagebox.showerror("Error", "Checkin failed.")
            except ValueError:
                messagebox.showerror("Error", "Invalid selection format.")
        
        ttk.Button(frame, text="Checkin Selected", command=checkin).pack(pady=10)
    
    def create_borrower_tab(self):
        """Tab for creating borrowers"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="New Borrower")
        
        labels = ["SSN:", "Name:", "Address:", "Phone:"]
        entries = {}
        
        for label_text in labels:
            ttk.Label(frame, text=label_text).pack(pady=5)
            var = tk.StringVar()
            ttk.Entry(frame, textvariable=var, width=40).pack(pady=5)
            entries[label_text] = var
        
        def create():
            card_id = self.db.create_borrower(
                entries["SSN:"].get(),
                entries["Name:"].get(),
                entries["Address:"].get(),
                entries["Phone:"].get()
            )
            if card_id:
                messagebox.showinfo("Success", f"Borrower created! Card ID: {card_id}")
            else:
                messagebox.showerror("Error", "Failed to create borrower.")
        
        ttk.Button(frame, text="Create Borrower", command=create).pack(pady=10)
    
    def create_fines_tab(self):
        """Tab for managing fines"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Manage Fines")
        
        ttk.Label(frame, text="Card ID:").pack(pady=5)
        card_var = tk.StringVar()
        ttk.Entry(frame, textvariable=card_var, width=30).pack(pady=5)
        
        def update_fines():
            self.db.update_fines()
            messagebox.showinfo("Success", "Fines updated!")
        
        def pay_fines():
            amount = self.db.pay_fines(card_var.get())
            messagebox.showinfo("Success", f"Paid ${amount:.2f}")
        
        ttk.Button(frame, text="Update Fines", command=update_fines).pack(pady=10)
        ttk.Button(frame, text="Pay Fines", command=pay_fines).pack(pady=10)

def main():
    root = tk.Tk()
    gui = LibraryGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()