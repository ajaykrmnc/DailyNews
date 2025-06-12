import os
from datetime import datetime
import subprocess
import google.generativeai as genai
import subprocess
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from finance.financeDaily import financeDaily
from upsc.upscDaily import upscDaily
from devdutt.devdutt_post import get_devdutt_posts
from thehinduEditorial.thehindu import get_hindu_editorial
from dristiias.current_affairs import dristiIAS
from techCrunch.techCrunch import techCrunch
from extractFunction.parseFunction import send_to_kindle, convert_file_to_epub

load_dotenv()

KINDLE_EMAIL = os.environ["KINDLE_EMAIL"]
SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
FROM_EMAIL = os.environ["FROM_EMAIL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CALIBRE_PATH = os.environ["CALIBRE_PATH"]

DATE = datetime.today().strftime('%d-%b-%Y')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
MERGED_HTML = f"Editorial_Dev.html"
EPUB_FILE3 = f"Finance-{DATE}.epub"
EPUB_FILE5 = f"Editorial_Dev-{DATE}.epub"



def get_html_merget(HTML_FILE4, HTML_FILE5):
    with open(HTML_FILE4, "r", encoding="utf-8") as file1, open(HTML_FILE5, "r", encoding="utf-8") as file2:
        content1 = file1.read()
        content2 = file2.read()

    merged_content = f"""
    <html>
      <head>
        <meta charset='utf-8'>
      </head>
      <body>
        {content1}
        {content2}
      </body>
    </html>
    """
    return merged_content

if __name__ == "__main__":
    dristiIAS()
    # # financeDaily(CALIBRE_PATH=CALIBRE_PATH, GEMINI_API_KEY=GEMINI_API_KEY, EPUB_FILE3=EPUB_FILE3)
    upscDaily(GEMINI_API_KEY)
    HTML_FILE4 = get_hindu_editorial()
    HTML_FILE5 = get_devdutt_posts()
    merge_content = get_html_merget(HTML_FILE4, HTML_FILE5)
    with open(MERGED_HTML, "w", encoding="utf-8") as f:
        f.write(merge_content)
    convert_file_to_epub(MERGED_HTML, EPUB_FILE5)
    send_to_kindle(EPUB_FILE5)
    techCrunch();


