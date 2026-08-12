# 🤖 Manga/Manhwa Telegram Downloader Bot

A Python Telegram bot for searching manga/manhwa, downloading chapters as compressed PDFs, caching generated files, and notifying subscribers about new chapters.

> **Important:** Scraping websites may be subject to their terms of service, robots rules, copyright law, and local law. Only use sources/content you are legally allowed to access.

## ✨ Features

- 🔍 Search across configured manga sources
- 📖 View manga details and chapters
- 📄 Download chapters as compressed PDFs
- ⚡ Cache generated Telegram files for faster re-downloads
- 🔔 Subscribe to manga update notifications
- 🔄 Periodic chapter checking with duplicate-alert prevention
- 🎯 Concurrency control for lower-memory deployments
- 🧹 Temporary-file cleanup support
- 📱 Inline-button interface

## 🛠 Tech Stack

- **Python:** 3.10+
- **Telegram:** python-telegram-bot 20.x
- **HTTP/Scraping:** httpx + BeautifulSoup4
- **Database:** MongoDB + Motor
- **PDF:** img2pdf + Pillow
- **Scheduler:** APScheduler
- **Configuration:** python-dotenv

## 📁 Project Structure

```text
manga_downloader_bot/
├── core/
│   ├── pdf_worker.py
│   └── scraper.py
├── data/
│   └── database.py
├── handlers/
│   ├── callbacks.py
│   └── commands.py
├── scheduler/
│   └── update_checker.py
├── tests/
├── utils/
│   ├── logger.py
│   └── queue_manager.py
├── config.py
├── main.py
├── requirements.txt
├── Dockerfile
├── Procfile
└── docker-compose.yml
```

## ⚙️ Local Setup

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate it:

**Linux/macOS**
```bash
source venv/bin/activate
```

**Windows**
```powershell
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and set:

```env
BOT_TOKEN=your_bot_token
MONGODB_URI=your_mongodb_connection_string
DATABASE_NAME=manga_bot_db
ADMIN_USER_ID=your_telegram_user_id
```

5. Start the bot:

```bash
python main.py
```

## 🐳 Docker

```bash
docker compose up --build
```

The included Compose file starts both the bot and MongoDB.

## 🤖 Commands

- `/start` — Register and show bot instructions
- `/help` — Show help
- `/manga <name>` — Search for a manga
- `/mysubscriptions` — Show active subscriptions
- `/stats` — Show personal statistics
- `/admin` — Show admin statistics (admin ID only)

## 🧪 Tests

The database tests require a reachable MongoDB instance configured through `.env`.

```bash
pytest -q
```

The scraper tests contact the configured source websites, so they can fail when a site is unavailable or changes its HTML structure.

## 🔐 Security Notes

- Never publish a real `.env` file or bot token.
- Keep `.env` out of Git; it is already listed in `.gitignore`.
- Replace placeholder usernames in bot messages before deployment.
- Do not expose MongoDB publicly without proper authentication and network restrictions.
