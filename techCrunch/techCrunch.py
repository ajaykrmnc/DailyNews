import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import os
load_dotenv()
# Parse the RSS feed

feed_url = "https://techcrunch.com/feed/"
feed = feedparser.parse(feed_url)

# Format today's articles
today = datetime.today().strftime('%Y-%m-%d')
articles = []
HTML_FILE = f"techCrunch/TheHindu-{today}.html"

for entry in feed.entries:
    published = (datetime(*entry.published_parsed[:6]).date()).strftime('%Y-%m-%d')
    yesterday = ((datetime.now() - timedelta(days=1)).date()).strftime('%Y-%m-%d')
    if published == today:
        articles.append(f"📰 {entry.title}\n🔗 {entry.link}\n\n")
        # fetch the content of the article
        response = requests.get(entry.link)
        if response.status_code == 200:
            content = response.text
            # Extract the main content using BeautifulSoup
            # with open("HTML_FILE", mode = "a", encoding ="utf-8") as f:
            #     soup = BeautifulSoup(content, "html.parser")
            #     main_content = soup.find("div", class_="article-content")
            #     if main_content:
            #         # Clean up the content
            #         for script in main_content.find_all("script"):
            #             script.decompose()
            #         for style in main_content.find_all("style"):
            #             style.decompose()
            #         content = main_content.get_text(separator="\n").strip()
            #     else:
            #         content = "No main content found."
            # # Save to the file
            # f.write(main_content)
        else:
            articles.append(f"Failed to fetch content for {entry.title}\n\n")
    # Try to get the image URL from the entry (common RSS fields: media_content, media_thumbnail, or image in summary)
    image_url = None
    cnt = 0
    if 'media_content' in entry and entry.media_content:
        image_url = entry.media_content[0].get('url')
        # check for correct url or not
        
        if image_url:
            # Ensure the directory exists
            os.makedirs("techCrunch/images", exist_ok=True)
            # Download and save the image locally
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                img_ext = image_url.split('.')[-1].split('?')[0]
                print(img_ext)
                img_filename = f"techCrunch/images/{cnt}.{img_ext}"
                with open(img_filename, "wb") as img_file:
                    img_file.write(img_response.content)
                cnt += 1
                image_url = img_filename  # Update to local path


    # Prepare Markdown content with image if available
    md_content = f"## {entry.title}\n"
    if image_url:
        md_content += f"![Image]({image_url})\n"
    md_content += f"{entry.description if 'description' in entry else 'No summary available.'}\n\n"

    articles.append(md_content)
        

# Save to text or EPUB
with open("techcrunch_today.md", "w", encoding="utf-8") as f:
    f.write("".join(articles) if articles else "No articles found for today.\n")


