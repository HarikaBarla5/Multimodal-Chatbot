# Multimodal Chatbot (Gemini + Pollinations.ai — 100% Free)

A CLI chatbot powered by Google's Gemini API, with automatic function
calling that lets it decide when to generate an image (or, later, a
video) instead of just replying with text. No paid API keys required.

## How it works

- **Gemini (Google's API)** drives the conversation and decides, via
  automatic function calling, whether to just talk or call
  `generate_image` / `generate_video`. Free tier: no credit card needed.
- **Pollinations.ai** actually generates the images — a free image API
  that needs no key or account at all.
- **Video** is stubbed out — swap in a real provider (Runway, Luma, etc.)
  in `video_gen.py` when you're ready.
- **Memory** has two layers:
  - *Short-term*: handled automatically by Gemini's chat session object
    for the current run.
  - *Long-term*: facts saved to `long_term_memory.json`, loaded back in
    every time you run the bot, so it remembers things across sessions.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Get a free Gemini API key:
   - Go to **aistudio.google.com/apikey**
   - Sign in with any Google account
   - Click "Create API Key" — no credit card, no billing setup
   - Copy the key (starts with `AIza...`)

3. Set it as an environment variable:

   **Mac/Linux:**
   ```
   export GEMINI_API_KEY="AIza..."
   ```

   **Windows (PowerShell):**
   ```
   setx GEMINI_API_KEY "AIza..."
   ```
   (Restart your terminal after using `setx`.)

   No key is needed for images — Pollinations.ai works with zero setup.

4. Run it:
   ```
   python main.py
   ```

## Usage

Just chat normally. Examples:

```
You: Hi, my name is Harika
Bot: Hi Harika! Nice to meet you.

You: /remember name = Harika
Remembered: name = Harika

You: Draw me a cat wearing sunglasses on a skateboard
Bot: Here's your skateboarding cat!
  [generated file: generated_images/image_1751234567.png]

You: Make a video of a sunset over the ocean
Bot: [Video generation isn't wired up yet...]
```

### In-chat commands

| Command | Effect |
|---|---|
| `/remember key = value` | Save a fact permanently (e.g. `/remember favorite_color = blue`) |
| `/forget key` | Remove a saved fact |
| `/memory` | Show everything currently remembered |
| `/exit` | Quit |

## File structure

```
chatbot/
├── main.py           # CLI loop
├── text_gen.py        # Gemini API + automatic function calling
├── image_gen.py        # Pollinations.ai image generation (free, no key)
├── video_gen.py         # Video generation stub
├── memory.py             # Long-term JSON persistence
├── config.py               # API keys, model names, settings
└── requirements.txt
```

## Free tier limits to know about

Gemini's free tier (as of when this was written) allows roughly 1,500
requests/day on the `gemini-2.5-flash` model with no billing required.
Pollinations.ai has no published hard limit but may rate-limit heavy use.
If you outgrow either, the code is structured so swapping providers only
means editing `text_gen.py` or `image_gen.py` — nothing else changes.

## Next steps / extending this

- **Add real video generation**: pick a provider (Runway ML API is the
  most mature right now), get an API key, and replace the body of
  `generate_video()` in `video_gen.py` with the submit → poll → download
  flow their API uses.
- **Add a web UI**: wrap `get_response()` from `text_gen.py` in a Flask
  or FastAPI app instead of the CLI loop in `main.py` — the core logic
  doesn't need to change.
- **Upgrade to a paid tier later**: if you outgrow Gemini's free limits,
  the same `text_gen.py` structure works with Claude or GPT — you'd just
  swap the client and tool-calling pattern (see the earlier version of
  this project if you want a reference for the Claude tool-use pattern).

  # Multimodal Chatbot (Gemini + Pollinations.ai — 100% Free)

A web chatbot powered by Google's Gemini API with a Streamlit interface,
deployable for free with no credit card. Supports text chat and image
generation, with a stub ready for video.

## Project structure

```
chatbot/
├── app.py                        # Streamlit WEB APP (deploy this)
├── main.py                        # CLI version (for local testing)
├── text_gen.py                     # Gemini API + automatic function calling
├── image_gen.py                     # Pollinations.ai image generation (free, no key)
├── video_gen.py                      # Video generation stub
├── memory.py                          # Long-term JSON persistence
├── config.py                           # API key handling (env var or Streamlit secrets)
├── requirements.txt
├── .gitignore                           # keeps secrets & generated files out of git
└── .streamlit/secrets.toml.example       # template for local Streamlit secrets
```

Both `app.py` (web) and `main.py` (CLI) share the same underlying
`text_gen.py` / `image_gen.py` / `memory.py` logic — only the interface
differs.

---

## Part 1 — Run it locally as a web app first

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up your key for local Streamlit testing:
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
   - Open the new file and paste your real Gemini key in place of the placeholder
   - (This file is git-ignored, so it's safe — it never gets pushed)

3. Run the app:
   ```
   streamlit run app.py
   ```
   Your browser should open automatically to `http://localhost:8501`.

4. Test it: say hi, ask it to remember your name, ask for an image.

---

## Part 2 — Deploy for free on Streamlit Community Cloud

### Step 1: Put your project on GitHub
1. Create a new **public** or **private** repo on github.com (e.g. `multimodal-chatbot`)
2. In your project folder, run:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/multimodal-chatbot.git
   git push -u origin main
   ```
   **Important:** because of the `.gitignore` file, your real API key
   (`.streamlit/secrets.toml`) will NOT be pushed. Double check by
   visiting your repo on GitHub afterward — you should NOT see that file
   listed. Only `secrets.toml.example` (with the placeholder) should appear.

### Step 2: Deploy on Streamlit Cloud
1. Go to **share.streamlit.io** and sign in with your GitHub account
2. Click "Create app" (or "New app")
3. Select your repository, branch (`main`), and set the main file path to `app.py`
4. Click "Advanced settings" → "Secrets" and paste:
   ```
   GEMINI_API_KEY = "AIza-your-real-key-here"
   ```
5. Click "Deploy"

Streamlit will install your `requirements.txt` and launch the app. First
deploy takes a couple of minutes. You'll get a public URL like:
```
https://your-app-name.streamlit.app
```

### Step 3: Share or bookmark your URL
Anyone with the link can use your chatbot — no login required on their
end. Every request still uses your Gemini free-tier quota, so keep that
in mind if you share it widely.

---

## Updating your deployed app later

Streamlit Cloud auto-redeploys whenever you push to `main`:
```
git add .
git commit -m "describe your change"
git push
```
Changes usually go live within a minute or two.

---

## Free tier limits to know about

Gemini's free tier allows roughly 1,500 requests/day on
`gemini-3.5-flash`, no billing required. Pollinations.ai has no published
hard limit but may rate-limit heavy use. Streamlit Community Cloud apps
are free but may "sleep" after inactivity and take a few seconds to wake
back up on the next visit — this is normal for free hosting.

## Next steps

- **Add real video generation**: pick a provider (Runway ML, Luma AI) and
  wire it into `video_gen.py` — both `app.py` and `main.py` will pick it
  up automatically since they share the same tool-calling logic.
- **Custom domain**: Streamlit Cloud supports custom domains on paid
  tiers if you want something other than `*.streamlit.app` later.
- **Restrict access**: Streamlit Cloud supports viewer authentication if
  you don't want the app to be fully public — check Settings → Sharing
  in your app's dashboard.