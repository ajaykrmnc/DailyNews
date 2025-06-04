# DailyNews to Kindle

Wake up Daily with a good newsletter tailored with AI also scraped by your favourite site daily directly on your favorite EPUB reading device KINDLE or to your inbox daily morning without any hustle of doing it manually. Automate this process of fetching daily news, current affairs, finance, or tech news or any content of your choice, parsing and converting them into Kindle-friendly EPUB files, and sending them directly to your Kindle device via authorised and permissible emails daily morning @7:00 AM through github action workflow cron job with calibre-smtp email server without any hustle of opening daily laptop, connecting with internet and doing the cron job which feels kinda boring and It helps avoid this friction of manual work.

---

## Features

- **Current Affairs Scraper:** Fetches daily news from [drishtiias.com](https://www.drishtiias.com) and processes it for Kindle through beautifull soup python library.
- **AI-Generated Content:** Uses Google Gemini to generate daily essays, book reviews, Gita paragraphs, tech news, and motivational messages.
- **Finance & UPSC Schedules:** Generates daily finance and UPSC topics from curated lists and CSVs which contains all the topics and subtopics mapped with the .
- **EPUB Conversion:** Converts HTML/Markdown content to EPUB using Calibre Ebook Convert CLI Tool.
- **Formatting:** Format the EPUB in such a way that it looks good on the Kindle Device by formatting correctly and embedding the css to the and chanding the language in it.
- **Kindle Delivery:** Emails the generated EPUB files to your Kindle device automatically daily. The email which is use to send to the Kindle should be allowed and can be changed through www.amazon.in/myk

---

## Project Structure

```
DailyNews/
├── news_to_kindle.py
├── requirements.txt
├── .env
├── finance/
│   └── financeDaily.py
├── upsc/
│   └── upscDaily.py
│   └── gs1.py
│   └── gs2.py
│   └── gs3.py
│   └── gs4.py
├── images_<date>/
│   └── ...downloaded images...
```

---

## Setup

### 1. Install Dependencies

```sh
pip install -r requirements.txt
```

### 2. Install Calibre

Download and install [Calibre](https://calibre-ebook.com/download).  
Note the installation path (e.g., `/Applications/calibre.app/Contents/MacOS` on Mac).

### 3. Configure Environment Variables

Create a `.env` file in the project root with the following keys:

```
KINDLE_EMAIL=your_kindle_email@kindle.com
SMTP_SERVER=smtp.yourprovider.com
SMTP_USERNAME=your_email_username
SMTP_PASSWORD=your_email_password
FROM_EMAIL=your_email_address
GEMINI_API_KEY=your_gemini_api_key
CALIBRE_PATH=/path/to/calibre
```

### 4. Prepare Data

- Ensure `finance/financeDaily.py` and `upsc/upscDaily.py` exist and are up to date.
- Place your GS1, GS2, GS3, GS4 topic lists in the `upsc/` directory as Python lists.

---

## Usage

Run the main script:

```sh
python news_to_kindle.py
```

This will:
- Fetch and process daily news and content
- Generate EPUB files for Current Affairs, News, Finance, and UPSC
- Email the EPUBs to your Kindle device

---

## Customization

- **News Source:** Edit the `URL` in `news_to_kindle.py` to change the news source.
- **AI Prompts:** Modify the prompt in `fetch_through_gemini()` for different content.
- **Kindle Recipients:** Edit the `kindle_emails` list in `send_to_kindle()` to add more recipients.
- **Topics:** Update the GS1–GS4 lists in `upsc/` for new UPSC topics.

---

## Requirements

- Python 3.7+
- Calibre (for `ebook-convert` and `calibre-smtp`)
- Google Gemini API key

---

## Troubleshooting

- **KeyError for Environment Variables:** Ensure your `.env` file is present and all keys are set.
- **Calibre Not Found:** Double-check the `CALIBRE_PATH` in your `.env`.
- **Email Issues:** Make sure your SMTP credentials are correct and your email provider allows SMTP access.

---

## License

This project is for personal and educational use only.

---

**Note:** Use responsibly and respect the terms of service of all third-party content providers.