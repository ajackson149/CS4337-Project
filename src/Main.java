import java.io.*;
import java.nio.file.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        String booksFile = "src/books.csv";
        String borrowersFile = "src/borrowers.csv";
        String outputDir = "output";
        Files.createDirectories(Paths.get(outputDir));
        normalize(booksFile, borrowersFile, outputDir);
    }

    public static void normalize(String booksFile, String borrowersFile, String outDir) throws IOException {
        Map<String, String> books = new LinkedHashMap<>();
        Map<String, Integer> authors = new LinkedHashMap<>();
        Set<String> bookAuthors = new LinkedHashSet<>();
        Map<String, Borrower> borrowers = new LinkedHashMap<>();
        int nextAuthorId = 1;

        // gets the ISBN, title, and author names from booksFile
        try (BufferedReader br = Files.newBufferedReader(Paths.get(booksFile))) {
            br.readLine(); // skip header (has unneeded tokens)
            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String[] c = line.split("\t", -1);
                if (c.length < 4) { 
                    continue;
                }

                String isbn = c[0].trim().toUpperCase();
                String title = c[2].trim();
                books.putIfAbsent(isbn, title);

                String[] names = c[3].split(",");
                for (String name : names) {
                    name = name.trim();
                    if (name.isEmpty()) {
                        continue;
                    }
                    Integer id = authors.get(name);
                    if (id == null) {
                        authors.put(name, id = nextAuthorId++);
                    }
                    bookAuthors.add(isbn + "#" + id);
                }
            }
            //System.out.println("bookAuthors: " + bookAuthors); // for testing
            /*System.out.println("Current bookAuthors entries:");
            for (String entry : bookAuthors) {
                System.out.println("  " + entry);
            }*/
        }

        // gets ID, SSN, name, address, and phone from borrowersFile
        try (BufferedReader br = Files.newBufferedReader(Paths.get(borrowersFile))) {
            br.readLine(); // skip header (has unneeded tokens)
            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String[] c = line.split(",", -1);
                if (c.length < 9) {
                    continue;
                }

                String id = c[0].trim();
                String ssn = c[1].trim();
                String name = c[2].trim() + " " + c[3].trim();
                //String email = c[4].trim(); // not used (yet)
                String address = c[5].trim() + ", " + c[6].trim() + ", " + c[7].trim();
                String phone = c[8].trim();

                borrowers.putIfAbsent(id, new Borrower(id, ssn, name, address, phone));
            }
        }

        writeCsv(Paths.get(outDir, "book.csv").toString(), "Isbn,Title", books.entrySet(), e -> e.getKey() + "," + quote(e.getValue()));
        writeCsv(Paths.get(outDir, "authors.csv").toString(), "Author_id,Name", authors.entrySet(), e -> e.getValue() + "," + quote(e.getKey()));
        writeCsv(Paths.get(outDir, "book_authors.csv").toString(), "Isbn,Author_id", bookAuthors, key -> { int i = key.lastIndexOf('#'); return key.substring(0, i) + "," + key.substring(i + 1);});
        writeCsv(Paths.get(outDir, "borrower.csv").toString(), "Card_id,Ssn,Bname,Address,Phone", borrowers.values(), b -> String.join(",", b.id, b.ssn, quote(b.name), quote(b.address), quote(b.phone)));
    }

    static interface ToCSV<T> {
        String row(T t); 
    }

    static <T> void writeCsv(String path, String header, Collection<T> data, ToCSV<T> fn) throws IOException {
        Path p = Paths.get(path);
        try (BufferedWriter bw = Files.newBufferedWriter(p)) {
            bw.write(header + "\n");
            for (T t : data) {
                bw.write(fn.row(t) + "\n");
            }
        }
    }

    static String quote(String s) {
        if (s.contains(",") || s.contains("\"")) {
            return "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }

    static class Borrower {
        String id, ssn, name, address, phone;
        Borrower(String id, String ssn, String name, String address, String phone) {
            this.id = id;
            this.ssn = ssn;
            this.name = name;
            this.address = address;
            this.phone = phone;
        }
    }
}
