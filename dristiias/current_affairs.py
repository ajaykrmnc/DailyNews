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
from extractFunction.parseFunction import saveImages


DATE = datetime.today().strftime('%d-%b-%Y')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
URL = f"https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{YESTERDAY}/"
FEED_URL = "https://www.drishtiias.com/rss.rss"
HTML_FILE = f"dristiias/prelims_{DATE}.html"

def fetch_and_convert_to_html():
    response = requests.get(URL)

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
    # Replace all <a> tags with <span> tags, preserving their contents
    for a in content_div.find_all("a"):
        a.unwrap() # Remove all attributes (like href, class, etc.)
    # Remove all <b> and </b> tags but keep their contents
    for b in content_div.find_all("b"):
        b.unwrap()
    for ifram in content_div.find_all("iframe"):
        ifram.decompose()
    for hr in content_div.find_all("hr"):
        hr.decompose()
    
    img_folder = f"images"
    saveImages(content_div, img_folder)
    # Download images and replace their src with local filenames
    
    html_content = f"""
    <html>
      <head>
        <meta charset='utf-8'>
      </head>
      <body>
        <h1>Prelims Pointers - {DATE}</h1>
        {str(content_div)}
      </body>
    </html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    return HTML_FILE
fetch_and_convert_to_html()


