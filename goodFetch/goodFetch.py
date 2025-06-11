from readability.readability import Document
import requests
from bs4 import BeautifulSoup
from readabilipy import simple_json_from_html_string

url = "https://www.thehindu.com/business/Economy/world-bank-cuts-indias-fy26-growth-forecast-to-63-on-subdued-exports-investments/article69681724.ece"
html = requests.get(url).text
article = simple_json_from_html_string(html, use_readability=True)
simple_json = f"goodFetch/simpl.json"

with open(simple_json, "w", encoding="utf-8") as f:
    f.write(str(article))
doc = Document(html)
# List all properties and methods of Document
title = doc.short_title()
content_html = article["content"]
# Print the title
print("Title:", title)

# Extract the first image from the content, if any
soup = BeautifulSoup(content_html, "html.parser")
img_tag = soup.find("img")
if img_tag and img_tag.get("src"):
    print("Image URL:", img_tag["src"])
else:
    print("Image URL: None found")

# Print the content (as plain text)
text = soup.get_text()
html_file = f"goodFetch/file.html"
# Write the article title and content to the HTML file
with open(html_file, "w", encoding="utf-8") as f:
    f.write(f"<h2>{article.get('title', title)}</h2>\n")
    f.write(content_html)