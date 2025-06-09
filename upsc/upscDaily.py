from google import genai
from upsc.gs1 import gs1
from upsc.gs2 import gs2
from upsc.gs3 import gs3
from upsc.gs4 import gs4
import csv
from datetime import date, timedelta
import pandas as pd
from google import genai
import os
from datetime import datetime
import subprocess

# create a DataFrame for the UPSC daily exam questions
# create a csv from each gs1 gs2 gs3 gs4 list
# and save it to a file with date assigned to csv from each 

# upscDaily.py
def extract_topics():
    today = datetime.today().strftime("%d-%m-%Y") 
    gs = [gs1, gs2, gs3, gs4]
    for idx in range(4):
        # Write each subject to the csv
        file_name = f'upsc/gs_{idx}.csv'
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Subject"])

        for i in range(365):
            current_date = (today + datetime.timedelta(days=i)).strftime("%d-%m-%Y");
            # Choose 1 or 2 topics serially for each day
            if idx < 3:
                start_idx = i * 2
            else:
                start_idx = i;

            length = len(gs[idx])
            if start_idx + 1 >= length:
                break
            selected_topics = f"{gs[idx][start_idx]}"
            if idx < 3:
                selected_topics += f" and {gs[idx][start_idx + 1]}"
            # append this date and topic to the csv
            with open(file_name, mode = 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([current_date, selected_topics])


def upscDaily(CALIBRE_PATH, GEMINI_API_KEY, EPUB_FILE):
    today = datetime.today().strftime("%d-%m-%Y") 
    filename = f"UPSC-{today}.md"
    for i in range(4):
        upsc_path = f"upsc/gs_{i}.csv"
        df_upsc = pd.read_csv(upsc_path)
        # Get today's topic
        today = datetime.today().strftime("%d-%m-%Y")
        today_topic_row = df_upsc[df_upsc["Date"] == today]

        client = genai.Client(api_key=GEMINI_API_KEY);

        if not today_topic_row.empty:
            today_topic = today_topic_row.iloc[0]["Subject"]
            gemini_prompt = f"Describe this following UPSC Topic in interesting manner(feel good vibes) : '{today_topic}'. Cover this topic in interesting manner and not like only to memorise add stories or any recent development which can strengthen the concept"
            response = client.models.generate_content(model = "gemini-2.0-flash", contents = gemini_prompt)
            with open(filename, "a", encoding="utf-8") as f:
                f.write(response.text)
            
            # Convert to EPUB using Calibre
        else:
            print("No topic found for today.")
    prompt = (
            f"Your role is to create a daily digest for Indian readers\n"
            f"Today is {today}.\n"
            "Compose a message to start the day that includes to the point \n"
            "- 1 essay for UPSC preparation in paragraph in about 500-1000 words\n"
            "- 1 paragraph from any book which is much highlighted and important also interesting\n"
            "- 1 Gita paragraph with explanation based on today nth day of year so it must be nth paragraph according to index such that I get daily unique paragraph; you don't have to be exact but you don't have to explain why you choose that paragraph\n"
            "- 1 Tech news in about 500 words\n"
            "- 1 motivational message for the day in about 100 words\n"
            "- 1 story from a hindu mythology book like puran, vedas or upnishads"
            "Ensure the content is fresh, unique, and relevant to today's date. Format the response clearly and engagingly."
        )
    response2 = client.models.generate_content(model = "gemini-2.0-flash", contents = prompt)
    with open(filename, "a", encoding = "utf-8") as f:
        f.write(response2.text)
    calibre_full_path = f"{CALIBRE_PATH}/ebook-convert"
    def convert_md_to_epub(output_path=None):
        epub_path = output_path if output_path else EPUB_FILE
        subprocess.run([calibre_full_path, filename, epub_path,"--language", "en"], check=True)
        print(f"EPUB saved at: {os.path.abspath(epub_path)}")
    convert_md_to_epub()
    print(f"Today's finance topic saved to {filename} and converted to EPUB at {EPUB_FILE}.")
