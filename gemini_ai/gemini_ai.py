import os
import subprocess
from datetime import datetime
from google import genai
from dotenv import load_dotenv  



DATE = datetime.today().strftime('%d-%b-%Y')

def fetch_through_gemini(GEMINI_API_KEY, CALIBRE_PATH, EPUB_FILE2):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")


    prompt = (
        f"You are an expert news analyst, UPSC mentor, historian, philosopher, and coding instructor. "
        f"Your role is to create a daily digest for Indian readers preparing for competitive exams.\n"
        f"Today is {DATE}.\n"
        "Compose a message to start the day that includes to the point \n"
        "- 1 essay for UPSC preparation in paragraph on current affairs in about 500-1000 words\n"
        "- 1 book review book and key learnings should be around 250-500 words\n"
        "- 1 Gita paragraph with explanation based on today nth day of year so it must be nth paragraph according to index such that I get daily unique paragraph; you don't have to be exact but you don't have to explain why you choose that paragraph\n"
        "- 1 Tech news and concept explanation in about 500 words\n"
        "- 1 motivational message for the day in about 100 words\n"
        "- 1 story from a hindu mythology book like puran, "
        "Ensure the content is fresh, unique, and relevant to today's date. Format the response clearly and engagingly."
    )

    response = model.generate_content(prompt)
    filename = f"motivational_message_{DATE}.md"
    calibre_path = f"{CALIBRE_PATH}/ebook-convert"

    print(calibre_path)
    def convert_html_to_epub(output_path=None):
        epub_path = output_path if output_path else EPUB_FILE2
        subprocess.run([calibre_path, filename, epub_path,"--language", "en"], check=True)
        print(f"EPUB saved at: {os.path.abspath(epub_path)}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)

    convert_html_to_epub()