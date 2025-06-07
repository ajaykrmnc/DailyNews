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
    soup = BeautifulSoup(response.content, "html.parser")
    content_div = soup.find("main")  # Adjust the class based on the actual HTML structure
    exclude_classes = ["sidebar", "my-acf-block"]
    for div in content_div.find_all("div"):
        div["class"] = None
        div["style"] = None
    for div in content_div.find_all("div", class_=lambda x: x and any(cls in x for cls in exclude_classes)):
        div.decompose()
    for header in content_div.find_all(["header"]):
        header.decompose()
    for script in content_div.find_all(["script","style"]):
        script.decompose()
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        with open(HTML_FILE5, "w", encoding="utf-8") as html_file:
            html_file.write(str(content_div))
    else:
        print("Failed to retrieve Devdutt's blog posts.")
    return HTML_FILE5
