import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = " https://devdutt.com/post-archive/"  # customize
all_posts = []
page_num = 1

# while True:
print(f"Scraping page {page_num}...")
url = BASE_URL.format(page_num=page_num)
res = requests.get(url)

if res.status_code != 200:
    print("No more pages or blocked.")
    # break

soup = BeautifulSoup(res.text, "html.parser")

with open("devdutt/page_num.html", "w", encoding= "utf-8") as f:
    f.write(soup.prettify())
for script in soup(["script"]):
    script.decompose()  # Remove scripts and styles for cleaner parsing
# Change selector based on site structure
# Try multiple selectors for robustness
print("Parsing articles...")
articles = []

selected = soup.select("div.wp-block-group a")
for article in selected:
    title = article.text.strip()
    link = article["href"]
    articles.append((title, link))
 # Select all <a> tags within the selected divs
# articles = soup.select("div.wp-block-group a")  # Select all <a> tags within the divs

print(articles)
# for article in soup.select_one("div.wp-blog-group a"):
#     articles.append(article)
# print(soup.prettify())
# # Filter out non-article links (e.g., pagination, category links)
# if not articles:
#     print("No articles found on this page.")
#     break

# for a in articles:
#     title = a.text.strip()
#     link = a["href"]
#     all_posts.append((title, link))

page_num += 1
time.sleep(1)  # Be polite with 1 sec delay
# # Save to CSV
with open("devdutt/devdutt_posts.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Title", "Link"])
    writer.writerows(articles)
# print(f"Scraped {len(all_posts)} posts from Devdutt's blog.")
# Note: The above code scrapes titles and links from Devdutt's blog and saves them to a CSV file.
