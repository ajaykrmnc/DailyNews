from datetime import date, timedelta
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import subprocess

def financeDaily(CALIBRE_PATH, GEMINI_API_KEY, EPUB_FILE3):
    finance_only_path = "finance/365_day_precise_finance_topics.csv"
    df_finance = pd.read_csv(finance_only_path)
    # Get today's topic
    today = datetime.today().strftime("%Y-%m-%d")
    today_topic_row = df_finance[df_finance["Date"] == today]

    client = genai.Client(api_key=GEMINI_API_KEY);

    if not today_topic_row.empty:
        today_topic = today_topic_row.iloc[0]["Finance Topic"]
        gemini_prompt = f"Provide a clear, and full exam-focused content of the following CFA Level 1 finance topic: '{today_topic}'. Include key concepts, formulas, and a practical example if possible but cover entirely."
        response = client.models.generate_content(model = "gemini-2.0-flash", contents = gemini_prompt)
        filename = f"finance_daily_{today}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        # Convert to EPUB using Calibre
        calibre_full_path = f"{CALIBRE_PATH}/ebook-convert"
        def convert_md_to_epub(output_path=None):
            epub_path = output_path if output_path else EPUB_FILE3
            subprocess.run([calibre_full_path, filename, epub_path,"--language", "en"], check=True)
            print(f"EPUB saved at: {os.path.abspath(epub_path)}")
        convert_md_to_epub()
        print(f"Today's finance topic saved to {filename} and converted to EPUB at {EPUB_FILE3}.")
    else:
        print("No topic found for today.")