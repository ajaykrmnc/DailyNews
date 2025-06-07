import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os


HTML_FILE4 = f"thehinduEditorial/thehindu_editorial.html"

def get_hindu_editorial():
    response = requests.get("https://www.thehindu.com/opinion/feeder/default.rss")
    # Clear the HTML file before inserting new content
    with open(HTML_FILE4, "w", encoding="utf-8") as html_file:
        html_file.truncate(0)
    # Check if the request was successful
    if response.status_code == 200:
        feed = feedparser.parse(response.content)
        today = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")  # Adjust to get yesterday's date
        for entry in feed.entries:
            published_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
            if published_date == today:
                response_html = requests.get(entry.link)
                soup = BeautifulSoup(response_html.content, "html.parser")
                for element in soup(["script", "style", "nav"]):
                    element.decompose()
                for tag in soup.find_all("a"):
                    tag.unwrap()
                # Define classes to exclude from the article content
                exclude_classes = [
                    "dfp-ad", "related-topics", "related-stories", "caption", "author", "update-publish-time", "comments-shares"
                ]
                for div in soup.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
                    div.decompose()
                for img in soup.find_all("img", class_="placeholder"):
                    img.decompose()
                for btn in soup.find_all("button"):
                    btn.decompose()
                img_folder = f"thehinduEditorial/images/"
                os.makedirs(img_folder, exist_ok=True)
                for img in soup.find_all("img"):
                    img_url = img.get("src")
                    if not img_url:
                        img.decompose()
                        continue
                    # Handle relative URLs by prepending the base URL
                    if img_url.startswith("/"):
                        img.decompose()
                        continue;
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
                
                content_div = soup.find("div", class_="container article-section")
                if content_div and response_html.status_code == 200:
                    with open(HTML_FILE4, "a", encoding="utf-8") as html_file:
                        html_file.write(str(content_div))
                else:
                    print(f"Failed to retrieve article: {entry.title}")
        print("The Hindu Editorial RSS feed saved successfully.")
    else:
        print(f"Failed to retrieve The Hindu Editorial RSS feed. Status code: {response.status_code}")

    return HTML_FILE4