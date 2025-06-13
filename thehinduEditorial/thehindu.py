import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
from readabilipy import simple_json_from_html_string
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from extractFunction.parseFunction import send_to_kindle, saveImages, convert_file_to_epub
HTML_FILE4 = f"thehinduEditorial/thehindu_editorial.html"

def get_hindu_editorial():
    response = requests.get("https://www.thehindu.com/opinion/feeder/default.rss")
    # Clear the HTML file before inserting new content
    with open(HTML_FILE4, "w", encoding="utf-8") as html_file:
        pass;
    # Check if the request was successful
    if response.status_code == 200:
        feed = feedparser.parse(response.content)
        today = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")  # Adjust to get yesterday's date
        for entry in feed.entries:
            published_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
            if published_date == today:
                response_html = requests.get(entry.link)
                article = simple_json_from_html_string(response_html.text, use_readability=True)
                article_file = f"thehinduEditorial/thehindu.json";
                html_content = f"<h2>{article['title']}</h2>{article['content']}"
                soup = BeautifulSoup(html_content, "html.parser")
                for tag in soup.find_all(["a"]):
                    tag.unwrap()
                
                cnt = 0;
                for source in soup.find_all("source"):
                    cnt += 1
                    if cnt % 4 != 1:
                        source.decompose();
                        continue;
                    img_tag = soup.new_tag("img")
                    img_tag["src"] = source.get("srcset")
                    source.insert_after(img_tag)
                    source.decompose()
                
                img_folder = os.path.abspath(os.path.join(os.path.dirname(HTML_FILE4), "..", "images"))

                saveImages(soup, img_folder);

                if soup and response_html.status_code == 200:
                    with open(HTML_FILE4, "a", encoding="utf-8") as html_file:
                        html_file.write(str(soup))
                else:
                    print(f"Failed to retrieve article: {entry.title}")
        print("The Hindu Editorial RSS feed saved successfully.")
    else:
        print(f"Failed to retrieve The Hindu Editorial RSS feed. Status code: {response.status_code}")
    return HTML_FILE4