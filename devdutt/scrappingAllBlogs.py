import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = " https://devdutt.com/post-archive/"  # customize
all_posts = []
page_num = 1

while page_num <= 154:  # Adjust the range as needed
    print(f"Scraping page {page_num}...")
    url = BASE_URL.format(page_num=page_num)
    res = requests.get(url)

    if res.status_code != 200:
        print("No more pages or blocked.")
        break

    soup = BeautifulSoup(res.text, "html.parser")

    for script in soup(["script"]):
        script.decompose()  # Remove scripts and styles for cleaner parsing
    # Change selector based on site structure
    # Try multiple selectors for robustness
    print("Parsing articles...", page_num)

    selected = []
    for li in soup.select("li.wp-block-post.post.type-post"):
        a_tag = li.find("a", recursive=False)
        if a_tag:
            selected.append(a_tag)
    for article in selected:
        title = article.text.strip()
        links = article["href"]
        all_posts.append((title, links))
        

    page_num += 1
    time.sleep(1)  # Be polite with 1 sec delay

# # Save to CSV
with open("devdutt/devdutt_posts.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Title", "Link"])
    writer.writerows(all_posts)
# print(f"Scraped {len(all_posts)} posts from Devdutt's blog.")
# Note: The above code scrapes titles and links from Devdutt's blog and saves them to a CSV file.
