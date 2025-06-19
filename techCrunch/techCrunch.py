import feedparser
from datetime import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import cloudscraper
import os
load_dotenv()
from readabilipy import simple_json_from_html_string
from playwright.sync_api import sync_playwright
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from extractFunction.parseFunction import saveImages, convert_file_to_epub, send_to_kindle
# Parse the RSS feed

headers = {
    "User-Agent": "Thunder Client (https://www.thunderclient.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def techCrunch():
    feed_url = "https://techcrunch.com/feed/"
    feed_url2 = "https://yourstory.com/feed"
    feed = feedparser.parse(feed_url2)

    # Format today's articles
    # today = datetime.today().strftime('%Y-%m-%d')
    html_file = f"techCrunch/tech.html"
    with open(html_file, "w", encoding="utf-8") as f:
        pass
    article = ""
    cnt = 0;
    for entry in feed.entries:
        # Truncate the file before writing (overwrite mode)
        cnt += 1;
        if(cnt >= 10):
            break;
        # fetch the content of the article
        yourStory = f"techCrunch/yourStory.html";

        
        scraper = cloudscraper.create_scraper()
        response = scraper.get(entry.link, timeout=20)
        
            
        
        
        # entry.content is usually a list of dicts with 'value' as the HTML content
        html_string = entry.content[0]['value'] if hasattr(entry, 'content') and entry.content else ""
        # print(html_string)
        article_data = simple_json_from_html_string(response.text, use_readability=True)
        html_content = f"<h2>{article_data['title']}</h2>{html_string}"
        soup = BeautifulSoup(html_content, "html.parser")
        for div in soup.find_all("div", class_="alsoread"):
            if div:
                div.decompose();
        for img in soup.find_all("img"):
            img_src = img.get("src");
            img_src_last = img_src.split("/")[-1];
            if(img_src_last == "analytics"):
                img.decompose();
        for svg in soup.find_all("svg"):
            if svg:
                svg.decompose()
        for a in soup.find_all("a"):
            if a:
                a.unwrap()

        img_path = f"techCrunch/images"
        img_full_path = os.path.abspath(img_path);
        saveImages(soup, img_full_path)
        # Append the processed HTML to the article string
        article += str(soup)
                
    html_content = f"""
        <html>
        <head>
            <meta charset='utf-8'>
        </head>
        <body>
            {article}
        </body>
        </html>
    """
    with open(yourStory, "w", encoding="utf-8") as f:
        f.write(html_content)
    epub_file = f"techCrunch/daily.epub"
    convert_file_to_epub(yourStory, epub_file, f"techCrunch/techCrunch.png")
    send_to_kindle(epub_file);
 
techCrunch();