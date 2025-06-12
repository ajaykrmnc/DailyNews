import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import os
load_dotenv()
from readabilipy import simple_json_from_html_string
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from extractFunction.parseFunction import send_to_kindle, removeClasses, saveImages, convert_file_to_epub
# Parse the RSS feed
def techCrunch():
    feed_url = "https://techcrunch.com/feed/"
    feed = feedparser.parse(feed_url)

    # Format today's articles
    today = datetime.today().strftime('%Y-%m-%d')
    html_file = f"techCrunch/tech.html"
    with open(html_file, "w", encoding="utf-8") as f:
        pass
    article = ""
    for entry in feed.entries:
        published = (datetime(*entry.published_parsed[:6]).date()).strftime('%Y-%m-%d')
        yesterday = ((datetime.now() - timedelta(days=1)).date()).strftime('%Y-%m-%d')
        # Truncate the file before writing (overwrite mode)
        
        if published == yesterday:
            # fetch the content of the article
            response = requests.get(entry.link)
            if response.status_code == 200:
                content = response.text
                article_data = simple_json_from_html_string(content, use_readability=True)
                html_content = f"<h2>{article_data['title']}</h2>{article_data['content']}"
                soup = BeautifulSoup(html_content, "html.parser")

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
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    epub_file = f"techCrunch/daily.epub"
    convert_file_to_epub(html_file, epub_file)
    send_to_kindle(epub_file);
# techCrunch();

   

