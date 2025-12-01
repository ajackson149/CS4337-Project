from library_db import LibraryDB

def main():
    db = LibraryDB("library.db")

    # test search
    results = db.search_books("harry potter")
    print("Search results:", results)

    # test checkout
    

    # test checkin
    

    # test fines
    

if __name__ == "__main__":
    main()
