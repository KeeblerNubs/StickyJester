# StickyJester
Sticky Bot For The Windsor Discord Server

## Setup

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Provide your Discord bot token in `sticky_bot.py` or via environment variable handling of your choice.
3. Configure Firebase Realtime Database credentials:
   - `FIREBASE_DATABASE_URL`: The database URL (e.g., `https://your-project-id.firebaseio.com`).
   - `FIREBASE_CREDENTIALS`: Path to a service account JSON file. If omitted, the bot will attempt to use Application Default Credentials (ADC).
4. Run the bot:
   ```sh
   python sticky_bot.py
   ```

Sticky configurations are persisted in Firebase under the `/sticky_configs` path so they survive bot restarts.
