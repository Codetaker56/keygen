# 🔐 Secure Key Generation & Validation System

A full-stack system for generating and validating access keys using:
- **Supabase** — cloud database
- **Flask API** — server-side key generation & validation (with rate limiting)
- **Discord Bot** — `/generate` slash command (ephemeral messages)
- **Python Client** — simple validation script with no embedded secrets

---

## 📁 Project Structure

```
key-system/
├── api/
│   ├── app.py              # Flask API
│   ├── requirements.txt
│   └── .env.example
├── bot/
│   ├── bot.py              # Discord bot
│   ├── requirements.txt
│   └── .env.example
├── client/
│   ├── validate.py         # Client validation script
│   └── requirements.txt
└── supabase/
    └── setup.sql           # Database setup script
```

---

## 1️⃣ Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Open the **SQL Editor** in your Supabase dashboard.
3. Paste and run the contents of `supabase/setup.sql`.
4. Collect your credentials from **Settings → API**:
   - `Project URL` → used as `SUPABASE_URL`
   - `service_role` secret key → used as `SUPABASE_SERVICE_KEY` (**never expose this**)

---

## 2️⃣ Flask API Setup

```bash
cd api

# Copy and fill in your environment variables
cp .env.example .env
# Edit .env with your SUPABASE_URL and SUPABASE_SERVICE_KEY

# Install dependencies
pip install -r requirements.txt

# Run the API
python app.py
```

The API will be available at `http://localhost:5000`.

### Endpoints

| Method | Endpoint    | Description                              |
|--------|-------------|------------------------------------------|
| POST   | `/generate` | Generates a 16-char key, stores in DB   |
| POST   | `/validate` | Checks if a key exists (`{key: "..."}`) |

#### Rate limits
- `/generate` — 10 requests per minute
- `/validate` — 30 requests per minute

#### Example requests
```bash
# Generate a key
curl -X POST http://localhost:5000/generate

# Validate a key
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{"key": "ABC123XYZ456DEFG"}'
```

---

## 3️⃣ Discord Bot Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application → add a Bot
3. Enable **"applications.commands"** scope and invite the bot to your server
4. Copy the bot token

```bash
cd bot

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your DISCORD_TOKEN and API_BASE_URL

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

Once running, use `/generate` in any server channel. The key will be sent as an **ephemeral** (private, only visible to you) message.

---

## 4️⃣ Client Validation Script

The client script contains **no secrets**. It only knows the API URL.

```bash
cd client

# Install dependencies
pip install -r requirements.txt

# Run (optionally set API URL via environment variable)
export API_BASE_URL=http://localhost:5000
python validate.py
```

You'll be prompted to enter your key. If valid, the application proceeds. If invalid, access is denied.

---

## 🔒 Security Notes

| Component        | Secret Stored | Notes |
|------------------|---------------|-------|
| Flask API        | ✅ Yes        | `SUPABASE_SERVICE_KEY` in `.env` only |
| Discord Bot      | ✅ Yes        | `DISCORD_TOKEN` in `.env` only |
| Client Script    | ❌ No         | Only knows the API URL |
| Supabase DB      | —             | No direct client access |

- The **service role key** is only ever used server-side in the Flask API.
- Clients never touch Supabase directly — all DB operations go through the API.
- The client script can safely be distributed; it contains no credentials.

---

## 🚀 Deploying to Production

For production, consider:
- Deploying the Flask API to **Railway**, **Render**, or **Fly.io**
- Using **gunicorn** instead of Flask's built-in server:
  ```bash
  pip install gunicorn
  gunicorn -w 4 app:app
  ```
- Setting `API_BASE_URL` in the client and bot `.env` to your deployed URL
- Using **Redis** for rate limiter storage instead of in-memory:
  ```python
  storage_uri="redis://localhost:6379"
  ```
