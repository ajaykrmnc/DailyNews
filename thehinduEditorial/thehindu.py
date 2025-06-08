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
                for tag in soup.find_all(["a", "picture"]):
                    tag.unwrap()
                # Define classes to exclude from the article content
                
                content_div = soup.find("div", class_="container article-section")
                exclude_classes = [
                    "dfp-ad", "related-topics", "related-stories", "caption", "author", "update-publish-time", "comments-shares"
                ]
                for div in content_div.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
                    div.decompose()
                for div in content_div.find_all("div"):
                    if "class" in div.attrs:
                        del div.attrs["class"]
                    if "style" in div.attrs:
                        del div.attrs["style"]
                for img in content_div.find_all("img"):
                    img.decompose()
                cnt = 0;
                for source in content_div.find_all("source"):
                    cnt += 1
                    if cnt % 4 != 1:
                        source.decompose();
                        continue;
                    img_tag = soup.new_tag("img")
                    img_tag["src"] = source.get("srcset")
                    source.insert_after(img_tag)
                    source.decompose()
                for btn in content_div.find_all("button"):
                    btn.decompose()
                img_folder = f"images/"
                os.makedirs(img_folder, exist_ok=True)
                for img in content_div.find_all("img"):
                    img_url = img.get("src")
                    # Handle relative URLs by prepending the base URL
                    if not img_url or img_url.startswith("/"):
                        img.decompose()
                        continue;
                    img_basename = os.path.basename(img_url.split("?")[0])
                    img_path = os.path.join(img_folder, img_basename)
                    try:
                        img_data = requests.get(img_url).content
                        with open(img_path, "wb") as f_img:
                            f_img.write(img_data)
                    except Exception as e:
                        print(f"Failed to download image {img_url}: {e}")
                    img["src"] = img_path

                if content_div and response_html.status_code == 200:
                    with open(HTML_FILE4, "a", encoding="utf-8") as html_file:
                        html_file.write(str(content_div))
                else:
                    print(f"Failed to retrieve article: {entry.title}")
        print("The Hindu Editorial RSS feed saved successfully.")
    else:
        print(f"Failed to retrieve The Hindu Editorial RSS feed. Status code: {response.status_code}")
    epub_path = f"thehinduEditorial/thehindu.epub"
    return HTML_FILE4

get_hindu_editorial()