# 🔐 Secure Key Generation & Validation System (hopefully)

A full-stack system for generating and validating access keys using:
- **Supabase** — cloud database (fancy spreadsheet)
- **Flask API** — server-side key generation & validation (with rate limiting so you can't spam it, nice try)
- **Discord Bot** — `/generate` slash command that sends you a secret message like a spy
- **Python Client** — validation script so simple even your nan could run it

---

## 📁 Project Structure

```
key-system/
├── api/
│   ├── app.py              # The brain
│   ├── requirements.txt    # Shopping list for pip
│   └── .env.example        # Fill this in or it explodes
├── bot/
│   ├── bot.py              # beep boop discord robot
│   ├── requirements.txt
│   └── .env.example
├── client/
│   ├── validate.py         # Does the key work? Find out here
│   └── requirements.txt
└── supabase/
    └── setup.sql           # Run this once and pray
```

---

## 1️⃣ Supabase Setup (the boring but important bit)

1. Go to [supabase.com](https://supabase.com) and create a free account (yes it's actually free, no catch)
2. Click **New Project**, give it a cool name, pick a region close to you
3. Open the **SQL Editor** and paste in `supabase/setup.sql` — hit Run and hope for the best
4. Grab your credentials from **Settings → API**:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` secret key → `SUPABASE_SERVICE_KEY` (guard this with your life)

---

## 2️⃣ Flask API Setup

```bash
cd api
pip install -r requirements.txt  # go make a coffee, this takes a sec
cp .env.example .env             # fill in your secrets
python app.py                    # fingers crossed
```

Running at `http://localhost:5000`. Don't open it in your browser expecting something cool, it's just an API.

### Endpoints

| Method | Endpoint    | Description |
|--------|-------------|-------------|
| POST   | `/generate` | Makes a fresh key, stores it, hands it over |
| POST   | `/validate` | Is this key legit? Yes/no, no essay |

#### Rate limits (because people ruin everything)
- `/generate` — 10 per minute
- `/validate` — 30 per minute

---

## 3️⃣ Discord Bot Setup (the fun part)

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new app, add a bot, copy the token
3. Invite it to your server with `bot` + `applications.commands` scopes
4. Fill in `.env` and run it:

```bash
cd bot
pip install -r requirements.txt
python bot.py
```

Use `/generate` in Discord. Your key shows up as an ephemeral message — only you can see it, very mysterious, very cool.

---

## 4️⃣ Client Validation Script

Zero secrets inside. Just runs, asks for a key, tells you if you're in or not. Very bouncer like.

```bash
cd client
pip install -r requirements.txt
python validate.py
# or compile to exe and watch it balloon to 11MB somehow
```

---

##  Security blah blah

| Component     | Has Secrets | Notes |
|---------------|-------------|-------|
| Flask API     | ✅ Yes      | Locked in `.env`, server only |
| Discord Bot   | ✅ Yes      | Token in `.env`, don't leak it |
| Client Script | ❌ No       | Safe to share with randos |
| Supabase DB   | —           | Never touched by clients |

- Nobody touches the database except the API. Not the bot. Not the client. Nobody.
- The validate script can be handed to anyone — there's nothing in it to steal. like opening a safe with dead flies

---

## 🚀 Deploying (aka making it someone else's problem)

- Deploy the API to **Railway** — free, easy, just works
- Update `API_BASE_URL` in your bot and client to point to Railway
- Your Pi can just run the bot and chill
- Compile `validate.py` to an exe with PyInstaller and watch a 1KB file become 11MB

```bash
pip install pyinstaller
pyinstaller --onefile validate.py
# dist/validate.exe — an 11MB beast is born
```
