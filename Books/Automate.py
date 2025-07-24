import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import time, datetime, timedelta
from Utils.parseFunction import send_to_kindle, convert_file_to_epub

def sendgeography():
    today = datetime.today().strftime("%Y-%m-%d");
    start = "2025-07-24";
    timegap = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days;
    timegap = int(timegap / 1)
    assert timegap >= 0, "Time gap cannot be negative"
    # Adjust the path to your epub file accordingly
    # This is a placeholder path; ensure it matches your directory structure
    # Example: if you have a series of epub files named SapiensPart_0.epub, SapiensPart_1.epub, etc.
    # You can modify the logic to suit your naming convention
    # For example, if you have a series of epub files named SapiensPart_{timegap}.epub
    # Ensure that the epub file exists before sending it to Kindle      
    
    
    epub_file = f"Books/Sapiens/SapiensPart_{timegap}.epub"
    convert_file_to_epub(epub_file, epub_file, f"Books/Sapiens/coverpage.jpeg")
    if not os.path.exists(epub_file):
        print(f"EPUB file {epub_file} does not exist.")
    else:
        send_to_kindle(EPUB_FILE=epub_file)

    theKiteRunner = f"Books/thekiterunner/Chapter_{timegap}.epub"
    convert_file_to_epub(theKiteRunner, theKiteRunner, f"Books/thekiterunner/coverpage.png")
    if not os.path.exists(theKiteRunner):
        print(f"EPUB file {theKiteRunner} does not exist.")
    else:
        send_to_kindle(EPUB_FILE=theKiteRunner)
    
