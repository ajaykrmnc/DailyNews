import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import subprocess
import google.generativeai as genai
import subprocess
import os
from dotenv import load_dotenv
from datetime import datetime
from datetime import timedelta
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
URL = f"https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{YESTERDAY}/"
EPUB_FILE = f"Prelims_Pointers_{DATE}.epub"
EPUB_FILE2 = f"Daily_News_{DATE}.epub"
HTML_FILE = f"prelims_{DATE}.html"


def fetch_and_convert_to_html():
    response = requests.get(URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    # content_div = soup.find("div", class_="article-content")
    content_div = soup.find("div", class_="list-category")
    if not content_div:
        raise Exception("Failed to find expected content on the page.")

    exclude_classes = {
        "border-bg", "tags-new", "mobile-ad-banner", "desktop-ad-banner",
        "starRating", "social-shares", "next-post", "recommendations-layout"
    }
    # Remove unwanted divs based on class names
    for div in content_div.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
        div.decompose()
    # Remove unwanted script and style tags
    for script in content_div.find_all("script"):
        script.decompose()
    
    for img in content_div.find_all("img"):
        img["class"] = "inline"
        img["style"] = "display: block; margin-left: auto; margin-right: auto;"
    for a in content_div.find_all("a"):
        a["style"] = "text-decoration: none; pointer-events: none; color: black;"
        a["href"] = None  # Disable links
    for h in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        pass
    for ifram in content_div.find_all("iframe"):
        # remove it
        ifram.decompose()
    for hr in content_div.find_all("hr"):
        hr.decompose()
    
    
    css = """
    <style>


    </style>
    """
    # Download images and replace their src with local filenames

    img_folder = f"images_{DATE}"
    os.makedirs(img_folder, exist_ok=True)

    for img in content_div.find_all("img"):
        img_url = img.get("src")
        if not img_url:
            continue
        # Handle relative URLs by prepending the base URL
        if img_url.startswith("/"):
            continue;

        # Generate a unique filename for each image
        ext = os.path.splitext(img_url)[1].split("?")[0] or ".jpg"
        img_basename = os.path.basename(img_url.split("?")[0])
        img_path = os.path.join(img_folder, img_basename)
        # Download image if not already downloaded
        if not os.path.exists(img_path):
            try:
                img_data = requests.get(img_url, timeout=10).content
                with open(img_path, "wb") as f_img:
                    f_img.write(img_data)
            except Exception as e:
                print(f"Failed to download image {img_url}: {e}")
                continue
        # Update img src to local path
        img["src"] = os.path.join(img_folder, img_basename)

    html_content = f"""
    <html>
      <head>
        <meta charset='utf-8'>
        {css}
      </head>
      <body>
        <h1>Prelims Pointers - {DATE}</h1>
        {str(content_div)}
      </body>
    </html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)



def convert_html_to_epub(output_path=None):
    epub_path = output_path if output_path else EPUB_FILE
    print(CALIBRE_PATH);
    full_calibre_path = f"{CALIBRE_PATH}/ebook-convert"
    print(full_calibre_path)
    subprocess.run([full_calibre_path, HTML_FILE, epub_path, "--language", "en", "--title", DATE, "--dont-split-on-page-breaks"], check=True)
    print(f"EPUB saved at: {os.path.abspath(epub_path)}")

def fetch_through_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")


    prompt = (
        f"You are an expert news analyst, UPSC mentor, historian, philosopher, and coding instructor. "
        f"Your role is to create a daily digest for Indian readers preparing for competitive exams.\n"
        f"Today is {DATE}.\n"
        "Compose a message to start the day that includes to the point \n"
        "- 1 essay for UPSC preparation in paragraph on current affairs in about 500-1000 words\n"
        "- 1 historical incident related to India and the world\n"
        "- 5 thoughts to ponder related to philosophy or maybe a quote from any book, so give me a book review; don't give generic but feels special for today\n"
        "- 1 Gita paragraph based on today nth day of year so it must be nth paragraph according to index such that I get daily unique paragraph; you don't have to be exact but you don't have to explain why you choose that paragraph\n"
        "- 5 advanced English vocabulary words (with meanings) for SSC CGL\n"
        "- Let suppose it's the nth day of the year and find the nth leetcode question with pseudo code solution, very little explanation\n"
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



def send_to_kindle():
    assert os.path.exists(EPUB_FILE), f"{EPUB_FILE} not found!"

    kindle_emails = ["pramodshah@kindle.com", "amritacs5566@gmail.com", "amankumarnetarhatiyan@gmail.com"]
    epubs = [EPUB_FILE, EPUB_FILE2]
    full_path = f"{CALIBRE_PATH}/calibre-smtp"
    for epub_file in epubs:
        for email in kindle_emails:
            try:
                result = subprocess.run([
                    full_path,
                    "--port", "587",
                    "--attachment", epub_file,
                    "--relay", SMTP_SERVER,
                    "--username", SMTP_USERNAME,
                    "--password", SMTP_PASSWORD,
                    FROM_EMAIL,
                    email,
                    epub_file
                ], check=True, capture_output=True, text=True)
                print(f"✅ Email sent to Kindle: {email}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to send email to Kindle: {email}")
                print("Error Output:", e.stderr)

if __name__ == "__main__":
    fetch_and_convert_to_html()
    convert_html_to_epub()
    fetch_through_gemini()
    send_to_kindle()