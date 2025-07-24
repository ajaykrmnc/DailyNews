import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def preview_chapters(epub_path):
    book = epub.read_epub(epub_path)
    documents = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    
    print(f"\n📚 Found {len(documents)} chapters:")
    for idx, doc in enumerate(documents):
        soup = BeautifulSoup(doc.get_content(), 'html.parser')
        title = soup.find(['h1', 'h2', 'title'])
        heading = title.get_text().strip() if title else 'No heading found'
        print(f"{idx}: {heading}")

def extract_chapter(epub_path, chapter_index):
    book = epub.read_epub(epub_path)
    documents = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    if chapter_index >= len(documents):
        print("❌ Chapter index out of range.")
        return None

    doc = documents[chapter_index]
    soup = BeautifulSoup(doc.get_content(), 'html.parser')
    return str(soup)  # or soup.get_text() for plain text

# Step 1: Preview chapters
preview_chapters(f"ncert/Geography.epub")

# Step 2: Extract chapter 0 (or any other index)
html_content = extract_chapter(f"ncert/Geography.epub", 10)

# Step 3: Save it to an HTML file
with open("chapter0.html", "w", encoding="utf-8") as f:
    f.write(html_content)
