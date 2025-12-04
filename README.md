# StickyJester
Sticky Bot For The Windsor Discord Server

## Setup

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Copy the sample environment file and fill in your secrets:
   ```powershell
   copy .env.example .env
   ```

3. Configure the required environment variables in `.env`:
   - `DISCORD_BOT_TOKEN` **(required):** Your Discord bot token.
   - `FIREBASE_DATABASE_URL` **(required):** The database URL (e.g., `https://your-project-id.firebaseio.com`).
   - `FIREBASE_CREDENTIALS` (optional): Absolute path to a service account JSON file. If omitted, the bot attempts to use Google Application Default Credentials (ADC).

4. Run the bot (ensure your environment variables are loaded first):
   - PowerShell: `setx DISCORD_BOT_TOKEN "<token>"` then restart the shell, or use `Get-Content .env | foreach { if ($_ -and $_ -notmatch '^#') { $name,$value = $_ -split '=',2; [System.Environment]::SetEnvironmentVariable($name,$value) } }`
   - WSL2/Linux: `set -a && source .env && set +a`
   - Start the bot:
     ```sh
     python sticky_bot.py
     ```

Sticky configurations are persisted in Firebase under the `/sticky_configs` path so they survive bot restarts.

## Discord portal walkthrough (Windows-friendly)

1. **Create the application and bot user** (https://discord.com/developers/applications):
   - **New Application → Name it** (e.g., "StickyJester").
   - **Bot → Add Bot**.
   - Under **Privileged Gateway Intents**, **enable**:
     - **Message Content Intent** (required because the bot watches channel messages).  
     - Presence/Server Member intents are optional for this bot.
   - Under **Bot Permissions**, grant at minimum:
     - **Send Messages**, **Embed Links**, **Read Message History** (core for stickies).
     - **Manage Messages** (needed to delete/replace the sticky and purge on inactivity).
     - **Attach Files** (if you expect images in embeds).
   - Click **Reset Token** and copy the token into your `.env` (`DISCORD_BOT_TOKEN`).

2. **Invite link** (OAuth2 → URL Generator):
   - Scopes: `bot` and `applications.commands`.
   - Bot Permissions: select the permissions above; Discord will append a permission integer to the invite link.
   - Copy the generated URL and open it in your browser to add the bot to your server.

3. **Firebase prep**:
   - Create a Realtime Database and note the **Database URL** (`https://<project-id>.firebaseio.com`).
   - Create a **Service Account JSON** and store it somewhere safe (see Docker notes below for mounting).

4. **Windows 10/.env tips**:
   - PowerShell: `copy .env.example .env` then `notepad .env`. Use double quotes around values with symbols.
   - If you use **WSL2**, run `cp .env.example .env && nano .env` inside the repo; export variables with `set -a && source .env && set +a` before starting the bot.
   - Keep tokens out of PowerShell history by using `setx` or editing the file directly instead of inline `set`.

## Run with Docker Desktop (Windows 10 friendly)

These steps assume Docker Desktop is installed with WSL2 backend enabled and virtualization turned on in the BIOS. If Windows Defender Firewall prompts when Docker starts, allow access so containers can reach the network.

### Docker Compose (recommended full setup)

1. Copy the env file and edit secrets:
   ```powershell
   copy .env.example .env
   notepad .env
   ```

2. Place your Firebase service account JSON next to the repo (default name `firebase-service-account.json`). If you keep it elsewhere, set an override path:
   - PowerShell/CMD: `setx FIREBASE_CREDENTIALS_PATH "C:\path\to\firebase-service-account.json"`
   - WSL2: `export FIREBASE_CREDENTIALS_PATH=/mnt/c/path/to/firebase-service-account.json`

3. Start the stack (from the repo root):
   ```powershell
   docker compose up --build -d
   ```
   - Uses `docker-compose.yml` to build the image, load `.env`, and bind-mount the service account to `/app/firebase-service-account.json` (matching the default `FIREBASE_CREDENTIALS` path).
   - Stop and clean up with `docker compose down`.

4. View logs and check health:
   ```powershell
   docker compose logs -f
   docker compose ps
   ```
   - If Discord token/Firebase URL are missing, the container will exit with an error.

### Manual Docker run (alternative)

1. Copy and edit environment variables (if you have not already):
   ```powershell
   copy .env.example .env
   notepad .env
   ```

2. Place your Firebase service account JSON alongside the project (e.g., `firebase-service-account.json`).

3. Build the image (PowerShell or CMD from the project root):
   ```powershell
   docker build -t stickyjester:latest .
   ```

4. Run the container with your environment file and mount the service account securely (PowerShell syntax shown):
   ```powershell
   docker run --rm ^
     --env-file .env ^
     -v ${PWD}\firebase-service-account.json:/app/firebase-service-account.json:ro ^
     stickyjester:latest
   ```
   - For WSL2/Ubuntu shells, swap the volume flag to `-v $(pwd)/firebase-service-account.json:/app/firebase-service-account.json:ro`.
   - If you rely on Google ADC instead of a service account file, omit the `-v` flag and leave `FIREBASE_CREDENTIALS` empty.

5. To run detached:
   ```powershell
   docker run -d --name stickyjester --env-file .env stickyjester:latest
   ```

Common Windows notes:
- Use absolute Windows paths when mounting files (e.g., `C:\path\to\firebase-service-account.json`).
- Ensure the mounted path is within a directory that Docker Desktop is allowed to access (check Settings → Resources → File Sharing).

## Firebase Realtime Database rules

- A hardened rule set for the bot lives in `firebase.rules.json`. The bot runs with a service account (bypassing these rules), but they block public client access.
- Deploy with the Firebase CLI (install via `npm i -g firebase-tools`):
  ```powershell
  firebase deploy --only database --project <your-project-id> --token <ci-token-if-needed>
  ```
- The rules enforce:
  - `.read`/`.write` locked down globally unless authenticated.
  - Validation for `sticky_configs/*` fields (`text`, `interval_seconds` bounds, and optional color/footer/thumbnail fields).

## Command cheat sheet

- `/pin`
  - Ephemeral prompt asks you to post the content to pin (text and optional attachment).
  - After **1 hour of channel inactivity**, the bot purges the channel and reposts the saved content.
- `/sticky set`
  - Creates or updates a sticky embed in a channel. Arguments: target channel (optional, defaults to current), text, interval in seconds (5–3600), optional color hex, footer text/icon URL, and thumbnail URL.
  - The sticky is refreshed on the configured interval and whenever pins change.
- `/sticky remove`
  - Deletes the sticky for the chosen/current channel and removes the config from Firebase.
- `/sticky info`
  - Shows the current sticky configuration for the channel.
