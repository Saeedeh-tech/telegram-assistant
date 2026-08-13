# Setup steps, in simple words

Everything here is free and no credit card is needed anywhere.

About 40 minutes. You use four websites: Telegram, Google, Neon, and Render.
Your code lives on GitHub.

Do the parts in order. Keep a notepad open — you will collect 6 values along the
way and paste them in at the end.

---

## Part 0 — Get the code onto your computer

2 minutes. Do this first.

**0.1** Download `telegram-assistant.zip` and save it to your **Downloads**
folder.

**0.2** Right-click the file, choose **Extract All**, then **Extract**.

**0.3** Open the folder you just extracted. Keep opening folders until you can
see `requirements.txt` sitting directly inside.

> Windows sometimes makes an extra folder, so you get
> `telegram-assistant\telegram-assistant\`. That is normal. The folder you want
> is the one with `requirements.txt` in it. Every later step means that folder
> when it says "your telegram-assistant folder".

**0.4** Check everything arrived. First turn on hidden files:

- **Windows 11**: **View** menu, then **Show**, then tick **Hidden items**
- **Windows 10**: **View** tab, then tick **Hidden items**

You should now see exactly this:

```
telegram-assistant\
    .github\
        workflows\
            reminders.yml
    app\
        tools\
            __init__.py
            calendar_tools.py
            messaging.py
            notes.py
        __init__.py
        agent.py
        config.py
        main.py
        security.py
        store.py
        telegram.py
        timeparse.py
    scripts\
        set_webhook.py
    .env.example
    .gitignore
    Dockerfile
    README.md
    SETUP.md
    render.yaml
    requirements.txt
```

That is 21 files. If `.github` or `.gitignore` are missing, hidden items are
still switched off. Go back and tick that box.

**You do not need to edit any of these files.** Everything you change happens on
a website: GitHub, Render, Neon, or Google.

---

## Part 1 — Make the bot in Telegram

On your iPhone. 5 minutes.

**1.1** Open Telegram. Search for `BotFather` and open the account with the blue
tick. Send this message:

```
/newbot
```

It asks for a name (anything, like `My Assistant`) and a username (must end with
`bot`, like `sade_helper_bot`).

It replies with a long token:

```
8012345678:AAHf9x2QwErTyUiOpAsDfGhJkLzXcVbNm00
```

**Write this down. Value 1 of 6.** Anyone with this token can control your bot.

**1.2** Search for `userinfobot` and send it any message. It replies with your
number, like `585739201`.

**Write it down. Value 2 of 6.** This is how the bot knows you are you. Nobody
else will get an answer from it.

---

## Part 2 — Google (calendar and the AI)

On a computer browser. 15 minutes. **You will not be asked for a card.**

**2.1 Make a project**

Go to `console.cloud.google.com`. Click the project name at the top, then
**New Project**. Call it `my-assistant`.

Google may show a banner asking you to start a free trial. **Ignore it.** You do
not need billing. Only Cloud Run needs billing, and we are not using Cloud Run.

**2.2 Turn on the Calendar API**

In the search bar at the top, type `Google Calendar API`, open it, and click
**Enable**.

**2.3 Make a service account**

This is a robot account that is allowed to edit your calendar.

Go to **IAM and admin → Service accounts → Create service account**.
Name it `assistant-calendar` and click Done.

Click the account you just made → **Keys** tab → **Add key → Create new key →
JSON**. A file downloads.

Open that file in a text editor. Copy **everything**, the whole thing, starting
with `{` and ending with `}`.

**That whole text is Value 3 of 6.**

**2.4 Share your calendar with the robot**

Look inside that JSON file for the line saying `client_email`. It looks like:

```
assistant-calendar@my-assistant-123.iam.gserviceaccount.com
```

> **The Google Calendar phone app cannot do this.** Sharing settings only exist
> on the desktop website. Use a computer browser.

Open `calendar.google.com` on a computer, then:

1. Click the **gear icon** at the top right → **Settings**.
2. In the left sidebar, scroll to **Settings for my calendars**.
3. Click your calendar's name. It expands.
4. Click **Share with specific people or groups**.
5. Click **Add people and groups** and paste the robot address.
6. Set permission to **Make changes to events**. This exact level. "See all
   event details" is not enough.
7. Click Send. Ignore any warning about sharing outside your organisation.

Your calendar must be under **My calendars**, not **Other calendars**. You can
only share calendars that you own.

**This step is where most people get stuck.** If you skip it, the bot will say
"Permission denied" later.

### Cleaner option: a separate calendar for the bot

Instead of sharing your main calendar, make a new one just for the bot. Bot
events stay separate, and you can delete the whole thing if you want to start
again.

1. In the left sidebar, click **+** next to "Other calendars" → **Create new
   calendar**.
2. Name it `Assistant` → **Create calendar**.
3. Share it with the robot address using the 7 steps above.
4. In that calendar's settings, scroll to **Integrate calendar** and copy the
   **Calendar ID**. It looks like `c_a1b2c3@group.calendar.google.com`.

If you do this, use that Calendar ID as `CALENDAR_ID` later, not your Gmail
address. It still appears in your iPhone Calendar app the same way.

**2.5 Get the AI key**

Go to `aistudio.google.com/apikey` → **Create API key** → choose your project.

**Copy it. Value 4 of 6.**

**Which model to use**

The code is already set to `gemini-3.5-flash`, which is free today. You do not
need to change anything. Skip to Part 3.

If one day the bot says it cannot answer, the model name may have changed. Here
is how to check in 30 seconds:

1. Open `ai.google.dev/gemini-api/docs/pricing`
2. Press Ctrl+F (or Cmd+F) and search for `Flash`
3. Under each model you will see a table with a **Free Tier** column. If the
   Input price row says **Free of charge**, that model is free.
4. The exact model ID is written under the heading in grey code text, like
   `gemini-3.5-flash`.

Free Flash models as of August 2026, best first:

| Model ID | Note |
| --- | --- |
| `gemini-3.5-flash` | good balance, the current default |
| `gemini-3.6-flash` | newest |
| `gemini-3.5-flash-lite` | use this if you hit the daily limit often |
| `gemini-2.5-flash` | older, still free, still works |

Avoid `gemini-2.0-flash`. Google shut it down on 1 June 2026, so older tutorials
that mention it will not work.

You can also see your own project's live limits at
`aistudio.google.com/rate-limit`. That page shows your real numbers, which is
more reliable than any guide.

---

## Part 3 — The database (Neon)

5 minutes. No card.

Go to `neon.com` and sign up with your GitHub or Google account.

Create a project. Pick the region closest to you — **Singapore** or **Sydney**.

Neon shows you a connection string:

```
postgresql://neondb_owner:abc123@ep-cool-name.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

**Copy it. Value 5 of 6.**

You get 0.5 GB of storage and 100 compute hours a month. Your notes and
reminders will use a tiny part of that.

---

## Part 4 — Put the code on GitHub

10 minutes. Choose **Route A** (website, no install) or **Route B** (terminal).

### First: make your two random passwords

Open **PowerShell**. Press the Windows key, type `powershell`, press Enter.

Run this line twice:

```powershell
-join (1..32 | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
```

It prints a long random string each time, like:

```
9f3c1a7e04b28d65fa1c9370e5b8d24a7c06e1f9b3428da5017cf6e29b4d8a35
```

The first one is your `TELEGRAM_WEBHOOK_SECRET`.
The second one is your `TASKS_SECRET`.

**Write both down. Value 6 of 6.** Paste them into a text file for now.

### Make the empty repository

Both routes need this first.

1. Go to `github.com` and sign in.
2. Click the **+** at the top right → **New repository**.
3. Name: `telegram-assistant`
4. Choose **Private**.
5. Do **not** tick "Add a README file". Leave it completely empty.
6. Click **Create repository**.

You now see a mostly empty page with some setup commands. Keep this page open.

---

### Route A — GitHub website, no install needed

**A1. Make hidden files visible in Windows**

Two important files start with a dot, and Windows hides them by default:
`.gitignore` and the `.github` folder. Without them, reminders will not work.

Open the folder in File Explorer. Then:

- **Windows 11**: click **View** → **Show** → tick **Hidden items**
- **Windows 10**: click the **View** tab → tick **Hidden items**

You should now see `.github` and `.gitignore` in the folder.

**A2. Upload**

On your empty GitHub page, click the link **uploading an existing file**.

Now open your `telegram-assistant` folder in File Explorer. **Go inside the
folder**, press `Ctrl+A` to select everything inside it, and drag it all onto the
GitHub page.

> This part matters. Drag the **things inside** the folder, not the folder
> itself. If you drag the folder, GitHub puts everything one level too deep and
> Render will not find your code.

Wait for the file list to appear, then scroll down and click **Commit changes**.

**A3. Check it worked**

Your repository page should show `requirements.txt`, `render.yaml` and `README.md`
in the top-level list. If instead you see a single folder named
`telegram-assistant`, the drag went wrong. Delete the repository and try again
from A2.

Then click into `.github` → `workflows`. You should see `reminders.yml`. If that
folder is missing, hidden items were still off in step A1.

---

### Route B — Windows terminal

**B1. Install Git**

In PowerShell:

```powershell
winget install --id Git.Git -e
```

Close PowerShell and open it again, then check it worked:

```powershell
git --version
```

If you see a version number, Git is ready.

**B2. Tell Git who you are** (first time only)

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**B3. Go to your folder**

```powershell
cd $HOME\Downloads\telegram-assistant
```

Change the path if you saved it somewhere else. Check you are in the right place:

```powershell
dir
```

You should see `requirements.txt`, `render.yaml` and the `app` folder.

**B4. Upload**

```powershell
git init
git add .
git commit -m "First version"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/telegram-assistant.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. The exact line is also on
your GitHub page, so you can copy it from there.

On the first push a browser window opens and asks you to sign in to GitHub.
Sign in and it continues by itself. Windows remembers it after that.

**B5. Check it worked**

Refresh your GitHub page. You should see all the files listed.

---

### About your secrets

Nothing secret goes to GitHub. The two passwords you just made are only typed
into Render and into GitHub Settings later, never into a file in this folder.

The `.gitignore` file also blocks `.env` and `sa-key.json`, in case you create
them later while testing.

Do not paste your bot token or the JSON key into any file in this folder.

## Part 5 — Deploy on Render

10 minutes. No card.

**5.1** Go to `render.com` and sign up with GitHub.

**5.2** Click **New → Web Service** and pick your `telegram-assistant`
repository. Render reads `render.yaml` and fills in most settings by itself.

Check that **Instance type** says **Free**.

**5.3** Render asks you for the secret values. Paste them in:

| Name | What to paste |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Value 1 |
| `ALLOWED_TELEGRAM_USER_IDS` | Value 2 |
| `SERVICE_ACCOUNT_JSON` | Value 3, the whole JSON text |
| `GEMINI_API_KEY` | Value 4 |
| `DATABASE_URL` | Value 5 |
| `TELEGRAM_WEBHOOK_SECRET` | first random string from Value 6 |
| `TASKS_SECRET` | second random string from Value 6 |
| `CALENDAR_ID` | your Gmail address, or the Calendar ID from step 2.4 |
| `GEMINI_MODEL` | the model ID from step 2.5 |

**5.4** Click **Create Web Service**. The first build takes about 5 minutes.

When it finishes, Render shows your address at the top:

```
https://telegram-assistant-abcd.onrender.com
```

**Copy it.** You need it twice below.

**5.5 Connect Telegram to it**

This tells Telegram where to send your messages. The easiest way is your browser.

Take this line, replace the three parts in capitals, and paste the whole thing
into your browser address bar:

```
https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=https://YOUR-RENDER-ADDRESS/telegram/webhook&secret_token=YOUR_WEBHOOK_SECRET&drop_pending_updates=true
```

- `YOUR_BOT_TOKEN` is Value 1. Keep the word `bot` in front of it, so it reads
  `.../bot8012345678:AAHf...`
- `YOUR-RENDER-ADDRESS` is your Render address without `https://`
- `YOUR_WEBHOOK_SECRET` is the first random string from Value 6

Press Enter. You should see:

```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

If you prefer PowerShell instead:

```powershell
$token   = "YOUR_BOT_TOKEN"
$url     = "https://YOUR-RENDER-ADDRESS/telegram/webhook"
$secret  = "YOUR_WEBHOOK_SECRET"

Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$token/setWebhook" `
  -ContentType "application/json" `
  -Body (@{ url = $url; secret_token = $secret; allowed_updates = @("message"); drop_pending_updates = $true } | ConvertTo-Json)
```

> Note: this puts your secret in the browser address bar, so it is saved in your
> browser history. For a personal bot that is fine. If it bothers you, use the
> PowerShell version, or clear that one history entry afterwards.

## Part 6 — Turn on reminders

2 minutes.

In your GitHub repository: **Settings → Secrets and variables → Actions →
New repository secret**. Add two:

| Name | Value |
| --- | --- |
| `SERVICE_URL` | your Render address |
| `TASKS_SECRET` | the same second random string |

Then open the **Actions** tab, click **Deliver reminders**, and click **Run
workflow** once to test it.

From now on it runs by itself every 30 minutes.

> GitHub switches off scheduled workflows in a repository that has had no
> activity for 60 days. If reminders stop one day, open the Actions tab and press
> the enable button.

---

## Part 7 — Connect the calendar to your iPhone

**Settings → Apps → Calendar → Accounts → Add Account → Google**

Sign in with the same Gmail account and turn **Calendars** on.

Now events the bot creates appear in your normal Calendar app after about a
minute.

---

## Part 8 — Try it

Open Telegram, find your bot, press Start. Send these one at a time:

```
/help
Book dentist next Tuesday at 9am
What is on my calendar this week?
Note: my bike lock code is 4271
What notes do I have about the bike?
Remind me to water the plants tomorrow at 8am
```

**The first message will be slow**, about 30 to 60 seconds. The free host puts
your service to sleep when nobody is using it, and it has to wake up. After that
it answers quickly until you leave it alone again.

---

## If something does not work

**No reply at all**

In Render, open the **Logs** tab and read the newest lines at the bottom.

Then ask Telegram what it thinks. Paste this in your browser address bar:

```
https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo
```

Look for `last_error_message`. If it has text in it, that text is your problem.
If `url` is empty, step 5.5 did not work.

**"Permission denied" for the calendar**

Step 2.4 was skipped, or the permission is not **Make changes to events**.

**"Calendar not found"**

`CALENDAR_ID` is wrong. It is either your Gmail address exactly, or the Calendar
ID of the separate calendar you made in step 2.4.

**Cannot find "Share with specific people"**

You are on the phone app. It is not there. Use a computer browser. Also check the
calendar is under **My calendars**, since you cannot share one you do not own.

**"Sorry, I could not finish that"**

Usually the Gemini free daily limit, or a model name that is no longer free.
Check the Render logs, then check `GEMINI_MODEL`.

**Reminders never arrive**

Open the GitHub Actions tab and look at the last run. A red cross shows the
error. Usually `SERVICE_URL` or `TASKS_SECRET` does not match Render.

**Check the database is reachable**

Paste this in your browser address bar:

```
https://YOUR-RENDER-ADDRESS/healthz?deep=1
```

`{"database":"ok","status":"ok"}` means the database is fine. If it says
`unreachable`, your `DATABASE_URL` in Render is wrong.

---

## Changing things later

Edit the code, then in PowerShell:

```powershell
git add .
git commit -m "what changed"
git push
```

If you used Route A and have no Git installed, you can edit any file directly on
the GitHub website: open the file, click the pencil icon, change it, then click
**Commit changes**.

Render rebuilds and redeploys by itself. That is the whole deploy process now.

To change a setting instead of code, use the **Environment** tab in Render.

---

## Keeping it safe

- Your repository is private, and `.gitignore` blocks `.env`, `sa-key.json` and
  the downloaded JSON key.
- Never paste your bot token into a chat, an issue, or a screenshot.
- If the token leaks, send `/revoke` to BotFather and redo step 5.5.
- Only your Telegram user ID gets answers. Everyone else is ignored silently.

## Two honest notes

On the Gemini free tier, Google may read your messages to improve their models.
For personal notes and calendar events most people accept this.

Free tiers have hard limits, not gentle ones. If you somehow used all 100
database compute hours in a month, the database stops until the next month. A
personal bot will not come close, but now you know what would happen.
