import subprocess
import os
from datetime import datetime, timedelta
import requests
import feedparser
import sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")));
from extractFunction.parseFunction import send_to_kindle, removeClasses, saveImages, convert_file_to_epub


DATE = datetime.today().strftime('%d-%b-%Y')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
URL = f"https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{YESTERDAY}/"
FEED_URL = "https://www.drishtiias.com/rss.rss"
HTML_FILE = f"dristiias/prelims_{DATE}.html"

def dristiIAS():
    response = requests.get(URL)

    soup = BeautifulSoup(response.content, "html.parser")
    content_div = soup.find("div", class_="list-category")
    if not content_div:
        raise Exception("Failed to find the main content div.")
    soup = BeautifulSoup(str(content_div), "html.parser");
    # Work directly with content_div as a soup fragment
    if not soup:
        raise Exception("Failed to find expected content on the page.")

    exclude_classes = {
        "border-bg", "tags-new", "mobile-ad-banner", "desktop-ad-banner",
        "starRating", "social-shares", "next-post", "recommendations-layout"
    }
    # Remove unwanted divs based on class names
    for div in soup.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
        div.decompose()
    # Remove unwanted script and style tags
    for script in soup.find_all("script"):
        script.decompose()
    
    for img in soup.find_all("img"):
        img["class"] = "inline"
        img["style"] = "display: block; margin-left: auto; margin-right: auto;"
    # Replace all <a> tags with <span> tags, preserving their contents
    for a in soup.find_all("a"):
        a.unwrap() # Remove all attributes (like href, class, etc.)
    # Remove all <b> and </b> tags but keep their contents
    for b in soup.find_all("b"):
        b.unwrap()
    for ifram in soup.find_all("iframe"):
        ifram.decompose()
    for hr in soup.find_all("hr"):
        hr.decompose()
    
    img_folder = f"dristiias/images"
    saveImages(soup, img_folder)
    # Download images and replace their src with local filenames
    
    html_content = f"""
    <html>
      <head>
        <meta charset='utf-8'>
      </head>
      <body>
        <h1>Prelims Pointers - {DATE}</h1>
        {str(soup)}
      </body>
    </html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    epub_file = f"dristiias/DristiIAS-{DATE}.epub"
    convert_file_to_epub(HTML_FILE, epub_file);
    send_to_kindle(epub_file);
    


