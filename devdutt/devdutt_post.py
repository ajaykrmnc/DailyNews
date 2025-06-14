import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import os

HTML_FILE5 = "devdutt/devdutt_posts.html"
def get_devdutt_posts():
    today = datetime.today().strftime("%Y-%m-%d")  # Get today's date
      # Adjust to get yesterday's date
    start = "2025-06-07"
    timegap = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days;
    # access the timegap'th element in the csv
    post_link = None
    with open("devdutt/devdutt_posts.csv", newline='', encoding='utf-8') as csvfile:
        reader = list(csv.reader(csvfile))
        if 0 <= timegap < len(reader):
            row = reader[timegap + 1]
            # Do something with the row, e.g., extract post info
            post_link = row[1]
            print(post_link)
        else:
            posts = []
    response = requests.get(post_link)
    if response.status_code != 200:
        print(f"Failed to fetch content. Status code: {response.status_code}")
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    content_div = soup.find("main")  # Adjust the class based on the actual HTML structure
    exclude_classes = ["sidebar", "my-acf-block"]
    for div in content_div.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
        div.decompose()
    for div in content_div.find_all("div"):
        div.attrs.pop("class", None)
        div.attrs.pop("style", None)
    for header in content_div.find_all(["header"]):
        header.decompose()
    for a in content_div.find_all(["a", "figure"]):
        a.unwrap();
    for script in content_div.find_all(["script","style"]):
        script.decompose()
    for img in content_div.find_all("img"):
        img_tag = soup.new_tag("img");
        img_tag["src"] = img.get("src");
        img.insert_after(img_tag)
        img.decompose()
    img_folder = os.path.abspath(os.path.join(os.path.dirname(HTML_FILE5), "..", "images"))
    for img in content_div.find_all("img"):
        img_url = img.get("src")
        img_basename = os.path.basename(img_url.split("?")[0]);
        img_path = os.path.join(img_folder, img_basename)
        img_data = requests.get(img_url, timeout=10).content
        try:
            with open(img_path, "wb") as f_img:
                f_img.write(img_data)
        except Exception as e:
            print(f"Failed to download image {img_url}: e")
            continue
        img["src"] = img_path;

        
    with open(HTML_FILE5, "w", encoding="utf-8") as html_file:
        html_file.write(str(content_div))
    
    return HTML_FILE5