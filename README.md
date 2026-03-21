# AI Bike Racing Simulator 2026

A modern, AI-driven bike racing simulator built with Python and Streamlit. The core game decisions and track generation are powered by Google Gemini (with robust offline fallbacks when the API is unavailable).

## Features
- AI Track Generator (Gemini) with difficulty and environment prompts
- AI Rider Decision Engine: step-by-step decisions with explainability
- Turn-based Simulation Engine: speed, position, crashes, progress, ranking
- Adaptive Difficulty: post-race performance feeds a new tailored track
- Explainability Panel: live action + reason from the AI
- Simple Track Visualization via matplotlib
- Optional second AI opponent and in-memory leaderboard

## Tech Stack
- Python 3.10+
- Streamlit (frontend + backend)
- Google Gemini API (google-generativeai)
- matplotlib, pandas

## Choose AI Engine
The simulator can run with **Google Gemini** (cloud) or **Ollama** (local LLM). Use the flags in `.env` (or any environment variable) to switch.

```
# .env example
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:latest   # any model you have pulled
OLLAMA_FLAG=True             # set to True to prefer Ollama

GOOGLE_API_KEY=your-key-here # optional
GEMINI_FLAG=True             # set to True to enable Gemini fallback
```
Priority order:
1. If `OLLAMA_FLAG` is true **and** Ollama is reachable, the app uses Ollama.
2. Else if `GEMINI_FLAG` is true and Gemini is healthy (or no Ollama), the app uses Gemini.
3. Otherwise it falls back to the built-in heuristic engine.

You can toggle these flags without changing code—restart Streamlit to apply.

## Local Setup
1. Create a virtual environment (recommended) and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional but recommended) Set your Gemini API key:
   - Obtain an API key from Google AI Studio.
   - Export the key in your shell before running the app:
     ```bash
     export GOOGLE_API_KEY="your-key-here"
     ```
   Without a key, the app will run fully offline using heuristic fallbacks.

## Run
```bash
streamlit run app.py
```
Then open the URL shown in your terminal (usually http://localhost:8501).

## Gameplay
1. Choose a difficulty and environment in the sidebar.
2. Click Generate Track.
3. Click Start Race.
4. Press Next Step to progress the simulation. The Explainability panel shows the AI decision and reason each step.
5. When you finish, generate an Adaptive Track to continue playing a personalized challenge. Results are recorded in the in-memory leaderboard.

## Data Models
- Track JSON (example):
  ```json
  {
    "segments": [
      {"type": "straight", "length": 100},
      {"type": "curve", "difficulty": 0.7},
      {"type": "obstacle", "severity": 0.5}
    ]
  }
  ```
- Decision JSON (example):
  ```json
  {
    "action": "accelerate",
    "reason": "Straight segment, safe to build speed."
  }
  ```

## File Structure
- app.py — Streamlit app (UI, controls, panels)
- gemini_service.py — All Gemini API calls, JSON parsing + retry, offline fallbacks
- simulation.py — Turn-based race engine, crashes, ranking, opponent logic
- utils.py — Helpers including matplotlib track plotting
- requirements.txt — Dependencies
- README.md — This guide

## Notes on AI Integration
- The app enforces JSON-only outputs using structured prompts and response_mime_type.
- Defensive parsing and retries attempt to recover from malformed responses.
- When the API is not available or returns invalid JSON, the simulator uses well-tuned offline heuristics and a deterministic fallback track generator.

## Deployment to Streamlit Community Cloud

### Prerequisites
1. GitHub account
2. Streamlit Community Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
3. (Optional) Google Gemini API key or local Ollama setup

### Step-by-Step Deployment

#### 1. Push to GitHub
```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit: AI Bike Racing Simulator"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

#### 2. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"New app"**
3. Select your repository: `YOUR_USERNAME/YOUR_REPO_NAME`
4. Set **Main file path**: `app.py`
5. Click **"Advanced settings"** (optional)

#### 3. Configure Secrets (Environment Variables)

In the **Advanced settings** or after deployment in **App settings → Secrets**:

```toml
# For Gemini (cloud AI)
GOOGLE_API_KEY = "your-gemini-api-key-here"
GEMINI_FLAG = "True"

# For Ollama (not recommended for cloud deployment)
# OLLAMA_FLAG = "False"
# OLLAMA_HOST = "http://localhost:11434"
# OLLAMA_MODEL = "llama3:latest"
```

**Note**: Ollama requires a local server, so it's not suitable for Streamlit Community Cloud. Use Gemini for cloud deployments.

#### 4. Deploy

Click **"Deploy"** and wait for the app to build and launch. Your app will be live at:
```
https://YOUR_APP_NAME.streamlit.app
```

### Updating Your Deployed App

Any push to your GitHub repository's main branch will automatically trigger a redeployment:

```bash
git add .
git commit -m "Update features"
git push origin main
```

### Alternative: Manual Deployment

To run on any machine (or a Codespace/VM):
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-key-here"
export GEMINI_FLAG="True"

streamlit run app.py
```

## Troubleshooting
- No API key set: The sidebar will say it is running with offline fallbacks.
- Matplotlib backend warnings: Safe to ignore; Streamlit renders figures via st.pyplot.
- Rate limits / transient API errors: The app will retry and then fallback automatically.

## Security Best Practices

1. **Never commit API keys** to GitHub
   - Add `.env` to `.gitignore`
   - Use Streamlit Secrets for cloud deployment
   - Use environment variables for local development

2. **Recommended `.gitignore`**:
   ```
   .env
   __pycache__/
   *.pyc
   .DS_Store
   .streamlit/secrets.toml
   ```

3. **For Streamlit Cloud**: Always use the built-in Secrets management (Settings → Secrets) instead of hardcoding keys.
