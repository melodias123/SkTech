# SK TECH — Puter.js AI Stable Build

This build deliberately restores the original SK TECH architecture:

- **AI:** Puter.js in the browser.
- **PC Builder:** Puter AI generates the build directly; the backend is not the AI layer.
- **Ask SK:** Puter AI handles the response, with optional live retailer context.
- **Shop:** backend `/api/search` handles connected retailer feeds.
- **eBay/EPN:** supported by the backend configuration.
- **Amazon:** optional. Missing Amazon credentials never stop AI PC building.
- **YouTube:** optional `/api/youtube` integration.

## Run locally

1. Copy `local.env.example` to `local.env`.
2. Add your existing retailer/YouTube credentials as appropriate.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the backend:

```bash
uvicorn main:app --reload
```

5. Open `http://127.0.0.1:8000`.

## Important

The browser loads Puter.js from `https://js.puter.com/v2/` in `frontend/index.html`. The PC Builder does **not** require an Amazon credential and does **not** call `/api/build` for AI generation.

The backend remains responsible for retailer searching and affiliate/retailer links.
