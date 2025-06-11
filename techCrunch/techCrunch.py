import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import os
load_dotenv()
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
    for entry in feed.entries:
        published = (datetime(*entry.published_parsed[:6]).date()).strftime('%Y-%m-%d')
        yesterday = ((datetime.now() - timedelta(days=1)).date()).strftime('%Y-%m-%d')
        # Truncate the file before writing (overwrite mode)
        
        print(entry.title);
        if published == yesterday:
            # fetch the content of the article
            response = requests.get(entry.link)
            if response.status_code == 200:
                content = response.text
                soup = BeautifulSoup(content, "html.parser");

                exclude_classes = [
                    "article-sidebar", "ad-unit__ad", "ad-unit", "footer-units", "article-bottom-section", "article--brief", "wp-block-techcrunch-social-share"
                    ,"wp-block-techcrunch-inline-cta", "wp-block-techcrunch-post-authors", "wp-block-techcrunch-menu-utility"
                ]
                for footer in soup.select("footer"):
                    footer.decompose();
                removeClasses(soup, None, exclude_classes, True, True)

                img_path = f"images"
                saveImages(soup, img_path)
                # Write the collected content to the HTML file (overwrite each time)
                with open(html_file, "a", encoding="utf-8") as f:
                    f.write(str(soup))

    epub_file = f"techCrunch/daily.epub"
    convert_file_to_epub(html_file, epub_file)
    send_to_kindle(epub_file);


   

