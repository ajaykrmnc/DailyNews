import subprocess
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()


DATE = datetime.today().strftime('%d-%b-%Y')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
URL = f"https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{YESTERDAY}/"
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

    
    for h in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        pass
    for ifram in content_div.find_all("iframe"):
        ifram.decompose()
    for hr in content_div.find_all("hr"):
        hr.decompose()
    
    img_folder = f"images_{DATE}"
    os.makedirs(img_folder, exist_ok=True)

    for img in content_div.find_all("img"):
        img_url = img.get("src")
        if not img_url:
            img.decompose()
            continue
        # Handle relative URLs by prepending the base URL
        if img_url.startswith("/"):
            img.decompose()
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
