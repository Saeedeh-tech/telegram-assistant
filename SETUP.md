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
PLACEHOLDER-1234567:your-long-token-goes-here
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
postgres-URL://USER:PASSWORD@ep-your-endpoint.neon.tech/neondb?sslmode=require
```

**Copy it. Value 5 of 6.**

You get 0.5 GB of storage and 100 compute hours a month. Your notes and
reminders will use a tiny part of that.

---

## Part 4 — Put the code on GitHub

10 minutes. Choose **Route A** (GitHub Desktop app) or **Route B** (PowerShell).

Route A is a normal Windows app with buttons, so nothing is typed. Route B is
typed commands, and makes every future update a single line. Both handle folders
and hidden files correctly. Either one works.

Do **not** use the GitHub website upload page. It cannot add folders. There is an
explanation at the end of this part if you want to know why.

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

### Route A — GitHub Desktop (recommended, no terminal)

This is the reliable UI way. GitHub Desktop uploads folders and hidden files
correctly, which the website upload page often will not.

**A1. Install it**

Go to `desktop.github.com`, download for Windows, and install it. Open it and
click **Sign in to GitHub.com**. Sign in with your browser when it asks.

**A2. Add your folder**

In GitHub Desktop: **File** menu → **Add local repository** → **Choose...** →
pick your `telegram-assistant` folder (the one with `requirements.txt` in it).

It will say *"This directory does not appear to be a Git repository"*. That is
expected. Click the blue words **create a repository** in that message.

A window opens. Check these:

- **Name**: `telegram-assistant`
- **Git ignore**: leave as **None**. Your folder already has the right one.
- **License**: **None**

Click **Create repository**.

**A3. Commit**

You now see a list of about 21 files on the left. That is everything, including
the hidden ones.

At the bottom left there is a box that says **Summary (required)**. Type:

```
First version
```

Click **Commit to main**.

**A4. Publish**

Click the blue **Publish repository** button at the top.

**Important: leave "Keep this code private" ticked.**

Click **Publish repository**. Done.

**A5. Check it worked**

Go to `github.com` and open your `telegram-assistant` repository. You should see
`requirements.txt`, `render.yaml` and the `app` folder listed.

Click into `.github` → `workflows`. You should see `reminders.yml` there.

> Already made an empty `telegram-assistant` repository on the website earlier?
> Delete it first, or GitHub Desktop cannot publish under that name. On the
> website: your repository → **Settings** → scroll to the very bottom →
> **Delete this repository**.

---

### Route B — PowerShell

**B1. Make the empty repository on the website**

1. Go to `github.com` and sign in.
2. Click the **+** at the top right → **New repository**.
3. Name: `telegram-assistant`
4. Choose **Private**.
5. Do **not** tick "Add a README file". Leave it completely empty.
6. Click **Create repository**. Keep this page open.

**B2. Install Git**

In PowerShell:

```powershell
winget install --id Git.Git -e
```

Close PowerShell and open it again, then check:

```powershell
git --version
```

**B3. Tell Git who you are** (first time only)

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**B4. Go to your folder**

```powershell
cd $HOME\Downloads\telegram-assistant
dir
```

You should see `requirements.txt` and the `app` folder in the output. If not,
you are in the wrong folder. Look for the one with `requirements.txt` in it.

**B5. Upload**

```powershell
git init
git add .
git commit -m "First version"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/telegram-assistant.git
git push -u origin main
```

Replace `YOUR-USERNAME`. The exact line is on your GitHub page too.

On the first push a browser window opens to sign you in. Windows remembers it
after that.

**B6. Check it worked**

Refresh your GitHub page. You should see all the files, including a `.github`
folder.

---

### Why not the website upload page?

You may have tried **Add file → Upload files** and found you could not add the
`app` or `.github` folders. That is a real limitation, not your mistake:

- The **choose your files** button opens a normal Windows file picker, and file
  pickers cannot select folders at all. Only files.
- Folders can only be added by **dragging them from File Explorer onto the
  page**, and even that does not work in every browser.

GitHub Desktop has neither problem. That is why Route A uses it.

If you still want to try dragging: open your `telegram-assistant` folder, press
`Ctrl+A` inside it, and drag the selection onto the GitHub page. Drag the things
*inside* the folder, not the folder itself.

**Already uploaded most files and only the dot-names are missing?**

This is the usual outcome. The uploader skips anything starting with a dot, so
`.github` and `.gitignore` are the two that fail.

You can create a file inside a folder that does not exist yet, by **typing the
path**. Each `/` you type turns into a folder.

*File 1 of 2 — the reminder timer*

1. On your repository page, click **Add file** → **Create new file**
2. In the name box at the top, type exactly:

   ```
   .github/workflows/reminders.yml
   ```

3. Paste this into the big box:

```yaml
name: Deliver reminders

on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:

jobs:
  sweep:
    runs-on: ubuntu-latest
    steps:
      - name: Wake the service and deliver due reminders
        env:
          SERVICE_URL: ${{ secrets.SERVICE_URL }}
          TASKS_SECRET: ${{ secrets.TASKS_SECRET }}
        run: |
          set -euo pipefail
          curl --silent --show-error --fail \
               --retry 3 --retry-delay 15 --retry-all-errors \
               --max-time 120 \
               -X POST "${SERVICE_URL%/}/tasks/due-reminders" \
               -H "X-Tasks-Secret: ${TASKS_SECRET}"
```

4. Click **Commit changes**, then **Commit changes** again.

*File 2 of 2 — the private file list*

1. **Add file** → **Create new file**
2. Name it exactly `.gitignore`
3. Paste this:

```
__pycache__/
*.pyc
sa-key.json
.env
.env.yaml
setup.env
.secrets
```

4. Click **Commit changes**.

**Then check these three things on GitHub**

1. `requirements.txt` is in the top-level list, not inside a folder
2. `app/tools/notes.py` opens and has text in it
3. `app/__init__.py` exists

Number 3 catches a second trap: that file is very short, and some browsers skip
it. If it is missing, create it the same way, named `app/__init__.py`, with this
single line inside:

```python
"""Telegram personal assistant: calendar, notes, reminders and messaging."""
```

Repeat for any other missing file. Tedious for 21 files, which is why Route A
exists, but fine for filling two or three holes.

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
repository.

> Note: this page does **not** read `render.yaml`. That file is only used by
> **New → Blueprint**. You are filling these in by hand, which is fine and takes
> two minutes.

Fill in the form:

| Field | Value |
| --- | --- |
| **Name** | `telegram-assistant` |
| **Language** | `Python 3` |
| **Branch** | `main` |
| **Region** | Singapore (closest to Perth) |
| **Root Directory** | leave empty |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | see below |
| **Instance Type** | **Free** |

Start Command, all on one line:

```
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app.main:app
```

**5.3 The secret values**

Keep scrolling **down the same page**. There is a section called **Environment
Variables**. This is what you were looking for. It is on the creation form, not
a separate screen.

The fastest way is the **Add from .env** button. Click it, then paste this whole
block after replacing each `PASTE_...` part:

```
TELEGRAM_BOT_TOKEN=PASTE_VALUE_1
ALLOWED_TELEGRAM_USER_IDS=PASTE_VALUE_2
GEMINI_API_KEY=PASTE_VALUE_4
DATABASE_URL=PASTE_VALUE_5
TELEGRAM_WEBHOOK_SECRET=PASTE_FIRST_RANDOM_STRING
TASKS_SECRET=PASTE_SECOND_RANDOM_STRING
CALENDAR_ID=PASTE_YOUR_GMAIL_ADDRESS
GEMINI_MODEL=gemini-3.7-flash
THINKING_LEVEL=low
TIMEZONE=Australia/Perth
TELEGRAM_CONTACTS={}
PYTHON_VERSION=3.12.8
```

Then add the last one **separately**, using **Add Environment Variable**:

- **Key**: `SERVICE_ACCOUNT_JSON`
- **Value**: the entire contents of the JSON file you downloaded in step 2.3

Add it on its own because it contains `=` and `{` characters that can confuse
the bulk paste box.

**The safest way to copy it.** In PowerShell, replace the file name with yours:

```powershell
Get-Content "$HOME\Downloads\YOUR-FILE.json" -Raw | Set-Clipboard
```

Now paste straight into Render. This avoids missing a character, which is easy to
do when selecting a long file by hand.

Not sure which file it is? It is in your **Downloads** folder with a name like
`my-assistant-472103-a1b2c3d4e5f6.json`. Check it is the right one:

```powershell
Get-Content "$HOME\Downloads\YOUR-FILE.json" -Raw | ConvertFrom-Json |
    Select-Object type, project_id, client_email
```

You should see `type` is `service_account`, and a `client_email` ending in
`.iam.gserviceaccount.com`. That email is the same one you shared your calendar
with in step 2.4.

**What it should look like.** It begins with `{` and ends with `}`, roughly 700
to 2500 characters, something like this (values here are fake):

```json
{
  "type": "service_account",
  "project_id": "my-assistant-472103",
  "private_key_id": "a1b2c3d4e5f6a7b8c9d0",
  "private_key": "PLACEHOLDER - a long block starting with BEGIN PRIVATE KEY",
  "client_email": "assistant-calendar@my-assistant-472103.iam.gserviceaccount.com",
  "client_id": "112233445566778899000",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

**Four things that will break it:**

- pasting only the `client_email` line
- pasting the file path instead of the file contents
- adding your own quotes around the whole thing
- copying only part of it

Any of these makes Render fail on startup with `JSONDecodeError` in the Logs tab.
If you see that word, this variable is the cause.

Do not change anything inside the file. The `\n` marks inside `private_key` must
stay exactly as they are.

**Lost the file?** Go back to step 2.3 and create a new key. Old keys keep
working, and you can delete them later from the same page.

**5.4** Open **Advanced** and set **Health Check Path** to:

```
/healthz
```

**5.5** Click **Deploy Web Service**. The first build takes about 5 minutes.

When it finishes, Render shows your address at the top:

```
https://telegram-assistant-abcd.onrender.com
```

**Copy it.** You need it twice below.

> Forgot one? You can add or fix any of these later in the **Environment** tab.
> Render redeploys automatically when you save.

**5.6 Connect Telegram to it**

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

Something has to poke your service every so often so due reminders get sent.
Pick **one** of the two options below.

> **If GitHub Actions gave you a billing error**, that is expected and not your
> fault. GitHub's free Actions minutes only cover **public** repositories.
> Private repositories need a paid plan or a spending limit above zero. Your repo
> is private, so Actions is blocked. Both options below solve it.

### Option 1 — Make the repository public (simplest)

Public repositories get unlimited free Actions minutes, so the workflow already
in your repo starts working immediately.

1. On your repository, go to **Settings**
2. Scroll to the bottom, **Danger Zone** → **Change repository visibility**
3. Choose **Make public** and confirm

Then add the two secrets: **Settings → Secrets and variables → Actions → New
repository secret**

| Name | Value |
| --- | --- |
| `SERVICE_URL` | your Render address |
| `TASKS_SECRET` | the second random string from Value 6 |

Open the **Actions** tab, click **Deliver reminders**, then **Run workflow**.

**Is public safe here?** Yes. Nothing secret is in these files. Your tokens and
keys live in Render and in GitHub Secrets, never in the code. GitHub keeps
Secrets encrypted, hides them from logs, and does not give them to anyone who
copies your repository. Someone reading your code learns nothing useful.

If you would still rather keep it private, use Option 2.

### Option 2 — cron-job.org (keeps your repo private)

A free scheduling website. No credit card, no GitHub billing.

1. Go to `cron-job.org` and create a free account
2. Click **Create cronjob**
3. Fill it in:

| Field | Value |
| --- | --- |
| **Title** | `telegram assistant reminders` |
| **URL** | `https://YOUR-RENDER-ADDRESS/tasks/due-reminders` |
| **Schedule** | Every 30 minutes |

4. Open the **Advanced** tab:
   - **Request method**: `POST`
   - **Headers**: add one, name `X-Tasks-Secret`, value = your second random
     string
   - **Request timeout**: set it as high as it allows, around 300 seconds

That timeout matters. Your Render service sleeps when idle and takes 30 to 60
seconds to wake. With a short timeout, cron-job.org marks every run as failed and
switches the job off after about 15 failures.

5. Click **Create** and then **Test run**. You want a green result and a body
   like `{"delivered":0,"failed":0}`.

If you use this option, you can delete `.github/workflows/reminders.yml` from
your repository. It will never run.

### Either way, check it works

Send your bot a message: *remind me to test this in 2 minutes*

The reply confirms it is scheduled. The reminder itself arrives on the next
sweep, so up to 30 minutes later. That is normal and expected.

> If you chose Option 1: GitHub switches off scheduled workflows in a repository
> with no activity for 60 days. If reminders stop one day, open the Actions tab
> and press the enable button.

## Part 7 — See your events on your iPhone

**On your iPhone.** This cannot be done from a computer.

Your events are already safe in Google Calendar the moment the bot creates them.
This part is only about seeing them on your phone. Pick whichever app you
actually use.

### Route A — Google Calendar app (easiest, nothing to configure)

Best if you do not use Apple's Calendar app.

1. Open the **App Store**, search **Google Calendar**, install it
2. Sign in with the same Gmail account you used for `CALENDAR_ID`

Done. Bot events appear straight away. There are no settings to change.

### Route B — Apple's built-in Calendar app

Best if you already use Apple's Calendar for other things.

**Do not have it?** It can be deleted, so it may be missing. First swipe down on
your home screen and search `Calendar`, since it may only be in the App Library.
If it is truly gone, open the **App Store**, search **Calendar**, and look for
the one by **Apple**. Reinstalling is free.

**Already have it?** Open it and tap **Calendars** at the bottom. If your Gmail
address is listed, you are done, skip the rest.

Otherwise connect your account:

**Settings → Apps → Calendar → Calendar Accounts → Add Account → Google**

On older iOS the path is shorter:

**Settings → Calendar → Accounts → Add Account → Google**

Sign in with the same Gmail account as `CALENDAR_ID`, and make sure the
**Calendars** switch is on. Mail, Contacts and Notes can stay off.

Events appear after about a minute.

### Route C — skip it

Open `calendar.google.com` in your phone browser whenever you want to look. You
can add it to your home screen from the share menu.

The bot works exactly the same either way. Nothing later in this guide depends
on Part 7.

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

**It replies "Something went wrong on my side"**

Your message reached the bot, so Telegram, Render and the allowlist are all
working. One of the three services behind it is failing.

Send the bot `/diag`. It tests each one and names the broken one:

```
Self check:

Database:  OK
Gemini:    FAILED — ClientError: 400 API key not valid
Calendar:  OK
```

Then match the message here:

| What /diag says | What to fix |
| --- | --- |
| `API key not valid` | `GEMINI_API_KEY` in Render is wrong. Copy it again from AI Studio. |
| `models/... is not found` | `GEMINI_MODEL` is wrong or no longer free. See step 2.5. |
| `RESOURCE_EXHAUSTED` or `429` | Free daily requests used up. Wait until tomorrow, or set `GEMINI_MODEL` to `gemini-3.5-flash-lite`. |
| `Service account info was not in the expected format` | `SERVICE_ACCOUNT_JSON` is incomplete. Paste the whole file again, see step 5.3. |
| `Permission denied` on Calendar | Step 2.4 was missed, or the permission is not **Make changes to events**. |
| `Calendar not found` | `CALENDAR_ID` is wrong. It must be your Gmail address exactly. |
| `has not been used in project` | The Calendar API is not switched on. Do step 2.2. |
| `Database: FAILED` | `DATABASE_URL` is wrong, or your Neon project is paused. Open Neon and check. |

The full error is also in Render under the **Logs** tab. Newest lines are at the
bottom.

**An error mentioning `thought_signature`**

Gemini 3 models will not accept a tool conversation unless each function call
carries a signature, and signatures only exist when the model actually thinks.
The code now forces thinking on and drops unsigned extra calls, so this should
not happen. If it does:

1. In Render, **Environment**, set `THINKING_LEVEL` to `medium`
2. If that does not help, try a different model in `GEMINI_MODEL`

Send `/diag` in the chat to list the models your key can use. Note that
`gemini-2.5-*` appears in that list but is closed to new API keys, so it will
return 404.

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

If you used Route A, do it in GitHub Desktop instead: it lists your changes,
type a summary, click **Commit to main**, then click **Push origin**.

You can also edit any single file on the GitHub website: open the file, click the
pencil icon, change it, then click **Commit changes**.

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
