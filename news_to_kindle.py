import os
import requests
from bs4 import BeautifulSoup
from bs4 import Tag
from datetime import datetime
import subprocess
import hashlib

KINDLE_EMAIL = os.environ["KINDLE_EMAIL"]
SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_PORT = os.environ["SMTP_PORT"]
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
FROM_EMAIL = os.environ["FROM_EMAIL"]

DATE = datetime.today().strftime('%d-%b-%Y')
URL = f"https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{DATE}/"
EPUB_FILE = f"Prelims_Pointers_{DATE}.epub"
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
        new_p = soup.new_tag("p")
        new_p.string = a.get_text(strip=True)
        a.replace_with(new_p)
    for h in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        pass
    for ifram in content_div.find_all("iframe"):
        ifram.decompose()

    css = """
    <style>
        h1 {
            text-align: justify;
            margin-bottom: 2%;
            font-size: 24px;
            text-decoration: none;
            border-bottom: 2px solid black;
            padding-bottom: 2px;
        }
        h2 {
            font-size: 20px;
        }
        h3, h4, h5, h6 {
            text-align: justify;
            font-size: 18px;
        }
        a {
         text-decoration: none;
        }
        dd, dt, dl {
            padding: 0;
            margin: 0;
        }
        .thumbcaption {
            display: block;
            font-size: 0.9em;
            padding-right: 5%;
            padding-left: 5%;
        }
        hr {
            color: black;
            background-color: black;
            height: 2px;
        }
        table {
            width: 90%;
            border-collapse: collapse;
        }
        table, th, td {
            border: 1px solid black;
        }

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
    subprocess.run(["/Applications/calibre.app/Contents/MacOS/ebook-convert", HTML_FILE, epub_path], check=True)
    print(f"EPUB saved at: {os.path.abspath(epub_path)}")


def send_to_kindle():
    subprocess.run([
        "calibre-smtp",
        "--port", SMTP_PORT,
        "--encryption-method", "TLS",
        "--username", SMTP_USERNAME,
        "--password", SMTP_PASSWORD,
        FROM_EMAIL,
        KINDLE_EMAIL,
        EPUB_FILE
    ], check=True)


if __name__ == "__main__":
    fetch_and_convert_to_html()
    convert_html_to_epub()
    # send_to_kindle()