import os
import subprocess
from datetime import datetime
from google import genai
from dotenv import load_dotenv  

DATE = datetime.today().strftime('%d-%b-%Y')
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"];
CALIBRE_PATH = os.environ["CALIBRE_PATH"];

def fetch_through_gemini(EPUB_FILE2):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        f"Your role is to create a daily digest for Indian readers\n"
        f"Today is {DATE}.\n"
        "Compose a message to start the day that includes to the point \n"
        "- 1 essay for UPSC preparation in paragraph in about 500-1000 words\n"
        "- 1 paragraph from any book which is much highlighted and important also interesting\n"
        "- 1 Gita paragraph with explanation based on today nth day of year so it must be nth paragraph according to index such that I get daily unique paragraph; you don't have to be exact but you don't have to explain why you choose that paragraph\n"
        "- 1 Tech news in about 500 words\n"
        "- 1 motivational message for the day in about 100 words\n"
        "- 1 story from a hindu mythology book like puran, vedas or upnishads"
        "Ensure the content is fresh, unique, and relevant to today's date. Format the response clearly and engagingly."
    )

    response = client.models.generate_content(model = "gemini-2.0-flash", contents = prompt)
    filename = f"gemini_ai/News-{DATE}.md"
    calibre_path = f"{CALIBRE_PATH}/ebook-convert"

    print(calibre_path)
    def convert_html_to_epub(output_path=None):
        epub_path = output_path if output_path else EPUB_FILE2
        try:
            subprocess.run([calibre_path, filename, epub_path,"--language", "en"], check=True)
        except Exception as e:
            print(f"Gemini_ai failed to convert: {e}")
        print(f"EPUB saved at: {os.path.abspath(epub_path)}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)

    convert_html_to_epub()