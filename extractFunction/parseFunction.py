import requests
from bs4 import BeautifulSoup
import subprocess
import os
from google import genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
load_dotenv()

CALIBRE_PATH = os.environ["CALIBRE_PATH"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
KINDLE_EMAIL = os.environ["KINDLE_EMAIL"]
SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
FROM_EMAIL = os.environ["FROM_EMAIL"]


def removeClasses(soup,include_classes, exclude_classes, unwrap=False, removeCSS=False):
    if exclude_classes:
        for div in soup.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
            div.decompose()

    # Optionally, if you want to also include certain classes and remove all others:
    if include_classes:
        # for div in soup.find_all("div", class_=lambda x: x and not any(cls in x for cls in include_classes)):
        #     div.decompose()
        pass;
    
    if unwrap:
        for a in soup.find_all("a"):
            if a:
                a.unwrap();
        for figure in soup.find_all("figure"):
            if figure:
                figure.unwrap();
    if removeCSS:
        for element in soup.find_all(["script", "style"]):
            element.decompose();

def saveImages(soup, img_path):
    os.makedirs(img_path, exist_ok=True)
    for img in soup.find_all("img"):
        img_url = img.get("src")
        if not img_url:
            img.decompose()
            continue
        # Handle relative URLs by prepending the base URL
        if img_url.startswith("/"):
            img.decompose()
            continue;

        # Generate a unique filename for each image
        # Extract the file extension (e.g., .png, .jpg)
        ext = os.path.splitext(img_url.split("?")[0])[1]
        # Extract the image filename after the last "/"
        img_filename = img_url.split("?")[0].split("/")[-1]
        if not ext:
            ext = ".jpg"  # Default extension if none found
        img_basename = img_filename
        img_file_path = os.path.join(img_path, img_basename)
        # Download image if not already downloaded
        if not os.path.exists(img_file_path):
            try:
                img_data = requests.get(img_url, timeout=10).content
                with open(img_file_path, "wb") as f_img:
                    f_img.write(img_data)
            except Exception as e:
                print(f"Failed to download image {img_url}", {e}, img_path)
                continue
        # Update img src to local path
        img["src"] = os.path.join(os.path.dirname(__file__), "..", img_file_path)
        img_tag = soup.new_tag("img");
        img_tag["src"] = img.get("src");
        img.insert_after(img_tag);
        img.decompose();

def convert_file_to_epub(INITIAL_FILE, EPUB_FILE):
        calibre_path = os.path.join(CALIBRE_PATH, "ebook-convert")
        try:
            subprocess.run([calibre_path, INITIAL_FILE, EPUB_FILE,"--language", "en", "--title", "Ajay Kumar"], check=True)
        except Exception as e:
            print(f"Calibre failed to convert: {e}")
        print(f"EPUB saved at: {os.path.abspath(EPUB_FILE)}")

def fetch_through_gemini(prompt, ans):
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model = "gemini-2.0-flash", contents = prompt)
    ans = response.text;   

def send_to_kindle(EPUB_FILE):
    full_path = f"{CALIBRE_PATH}/calibre-smtp"
    try:
        result = subprocess.run([
            full_path,
            "--port", "587",
            "--attachment", EPUB_FILE,
            "--relay", SMTP_SERVER,
            "--username", SMTP_USERNAME,
            "--password", SMTP_PASSWORD,
            FROM_EMAIL,
            KINDLE_EMAIL,
            EPUB_FILE
        ], check=True, capture_output=True, text=True)
        print(f"✅ Email sent to Kindle: {KINDLE_EMAIL}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to send email to Kindle: {KINDLE_EMAIL}")
        print("Error Output:", e.stderr)




    