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
                
                include_classes = [
                    "div.storyline", "div.editorial", "div.opinion", "div.columns", "article-section"
                ]
                exclude_classes = [
                    "dfp-ad", "related-topics", "related-stories", "caption", "author", "update-publish-time", "comments-shares"
                ]
                # Find the main content div using the include_classes selectors
                content_div = None
                for selector in include_classes:
                    found = soup.select_one(selector)
                    if found:
                        content_div = found
                        break
                if not content_div:
                    print(f"Could not find main content for: {entry.title}")
                    continue
                for div in content_div.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
                    div.decompose()
                for div in content_div.find_all("div"):
                    if "class" in div.attrs:
                        del div.attrs["class"]
                    if "style" in div.attrs:
                        del div.attrs["style"]
                # Improve headline styling for better readability
                for h1 in content_div.find_all("h1"):
                    h1["style"] = "font-size: 1.5em; font-weight: bold; margin-bottom: 0.5em;"
                for h2 in content_div.find_all("h2"):
                    h2["style"] = "font-size: 1.2em; font-weight: bold; margin-bottom: 0.4em;"
                for h3 in content_div.find_all("h3"):
                    h3["style"] = "font-size: 1em; font-weight: bold; margin-bottom: 0.3em;"
                # Optional: Add some spacing to paragraphs for readability
                for p in content_div.find_all("p"):
                    p["style"] = "margin-bottom: 1em; line-height: 1.6;"

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
                img_folder = os.path.abspath(os.path.join(os.path.dirname(HTML_FILE4), "..", "images"))
                os.makedirs(img_folder, exist_ok=True)
                for img in content_div.find_all("img"):
                    img_url = img.get("src")
                    # Handle relative URLs by prepending the base URL
                    if not img_url or img_url.startswith("/"):
                        img.decompose()
                        continue
                    img_basename = os.path.basename(img_url.split("?")[0])
                    img_path = os.path.join(img_folder, img_basename)
                    try:
                        img_data = requests.get(img_url).content
                        with open(img_path, "wb") as f_img:
                            f_img.write(img_data)
                    except Exception as e:
                        print(f"Failed to download image {img_url}: {e}")
                    # Set src relative to the HTML file location
                    img["src"] = os.path.join(img_folder, img_basename)

                if content_div and response_html.status_code == 200:
                    with open(HTML_FILE4, "a", encoding="utf-8") as html_file:
                        html_file.write(str(content_div))
                else:
                    print(f"Failed to retrieve article: {entry.title}")
        print("The Hindu Editorial RSS feed saved successfully.")
    else:
        print(f"Failed to retrieve The Hindu Editorial RSS feed. Status code: {response.status_code}")
    return HTML_FILE4
# get_hindu_editorial()