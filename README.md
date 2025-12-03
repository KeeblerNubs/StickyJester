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

## Run with Docker Desktop (Windows 10 friendly)

These steps assume Docker Desktop is installed with WSL2 backend enabled and virtualization turned on in the BIOS. If Windows Defender Firewall prompts when Docker starts, allow access so containers can reach the network.

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
