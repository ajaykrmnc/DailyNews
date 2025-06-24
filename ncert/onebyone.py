import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import time, datetime, timedelta
from extractFunction.parseFunction import send_to_kindle

def sendgeography():
    today = datetime.today().strftime("%Y-%m-%d");
    start = "2025-06-20";
    timegap = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days;
    timegap = int(timegap / 3)
    epub_file = f"ncert/GEOGRAPHY/File_{timegap}.epub"
    if epub_file:
        send_to_kindle(EPUB_FILE=epub_file)

# sendgeography();