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
from dristiias.current_affairs import fetch_and_convert_to_html
from gemini_ai.gemini_ai import fetch_through_gemini

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
EPUB_FILE = f"DristiIAS-{DATE}.epub"
EPUB_FILE3 = f"Finance-{DATE}.epub"
EPUB_FILE4 = f"UPSC_AI-{DATE}.epub"
EPUB_FILE5 = f"Editorial_Dev-{DATE}.epub"

def convert_html_to_epub(HTML_FILE=None, output_path=None):
    epub_path = output_path if output_path else EPUB_FILE
    print(CALIBRE_PATH);
    full_calibre_path = f"{CALIBRE_PATH}/ebook-convert"
    print(full_calibre_path)
    subprocess.run([full_calibre_path, HTML_FILE, epub_path, "--language", "en", "--title", DATE, "--level1-toc", "//h1", "--level2-toc", "//h2","--authors", "Ajay Kumar"], check=True)
    print(f"EPUB saved at: {os.path.abspath(epub_path)}")

def send_to_kindle():
    assert os.path.exists(EPUB_FILE), f"{EPUB_FILE} not found!"

    epubs = [EPUB_FILE, EPUB_FILE5, EPUB_FILE4]
    full_path = f"{CALIBRE_PATH}/calibre-smtp"
    for epub_file in epubs:
        try:
            result = subprocess.run([
                full_path,
                "--port", "587",
                "--attachment", epub_file,
                "--relay", SMTP_SERVER,
                "--username", SMTP_USERNAME,
                "--password", SMTP_PASSWORD,
                FROM_EMAIL,
                KINDLE_EMAIL,
                epub_file
            ], check=True, capture_output=True, text=True)
            print(f"✅ Email sent to Kindle: {KINDLE_EMAIL}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to send email to Kindle: {KINDLE_EMAIL}")
            print("Error Output:", e.stderr)

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
    HTML_FILE = fetch_and_convert_to_html()
    convert_html_to_epub(HTML_FILE=HTML_FILE, output_path=EPUB_FILE)
    # # financeDaily(CALIBRE_PATH=CALIBRE_PATH, GEMINI_API_KEY=GEMINI_API_KEY, EPUB_FILE3=EPUB_FILE3)
    upscDaily(CALIBRE_PATH=CALIBRE_PATH, GEMINI_API_KEY=GEMINI_API_KEY, EPUB_FILE=EPUB_FILE4)
    HTML_FILE4 = get_hindu_editorial()
    # with open(HTML_FILE4, "r", encoding="utf-8") as f:
    #     html_content = f.read()
    HTML_FILE5 = get_devdutt_posts()
    MERGED_HTML = get_html_merget(HTML_FILE4, HTML_FILE5)
    convert_html_to_epub(HTML_FILE="merged_content.html", output_path=EPUB_FILE5)
    send_to_kindle()


