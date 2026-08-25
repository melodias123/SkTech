
import os
import base64
import time
import asyncio
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / "local.env")
load_dotenv(ROOT / ".env")


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="SK TECH",
    version="2.2",
)


# ============================================================
# FRONTEND
# ============================================================

FRONTEND = ROOT / "frontend"

if FRONTEND.exists():
    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND),
        name="static",
    )


@app.get("/")
async def homepage():
    index = FRONTEND / "index.html"

    if not index.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "frontend/index.html not found"
            },
        )

    return FileResponse(index)


# ============================================================
# ENV HELPERS
# ============================================================

def env_bool(
    name: str,
    default: bool = False,
) -> bool:

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


# ============================================================
# EBAY
# ============================================================

EBAY_ENABLED = env_bool(
    "EBAY_ENABLED",
    True,
)

EBAY_CLIENT_ID = os.getenv(
    "EBAY_CLIENT_ID",
    "",
).strip()

EBAY_CLIENT_SECRET = os.getenv(
    "EBAY_CLIENT_SECRET",
    "",
).strip()

EBAY_ENV = os.getenv(
    "EBAY_ENV",
    "production",
).strip().lower()

EBAY_MARKETPLACE = os.getenv(
    "EBAY_MARKETPLACE",
    "EBAY_GB",
).strip()


# ============================================================
# EBAY EPN
# ============================================================

EBAY_EPN_ENABLED = env_bool(
    "EBAY_EPN_ENABLED",
    False,
)

EBAY_EPN_CAMPAIGN_ID = os.getenv(
    "EBAY_EPN_CAMPAIGN_ID",
    "",
).strip()

EBAY_EPN_REFERENCE_ID = os.getenv(
    "EBAY_EPN_REFERENCE_ID",
    "SKTECH",
).strip()


# ============================================================
# AMAZON
# ============================================================

AMAZON_ENABLED = env_bool(
    "AMAZON_ENABLED",
    False,
)

AMAZON_ACCESS_KEY = os.getenv(
    "AMAZON_ACCESS_KEY",
    "",
).strip()

AMAZON_SECRET_KEY = os.getenv(
    "AMAZON_SECRET_KEY",
    "",
).strip()

AMAZON_PARTNER_TAG = os.getenv(
    "AMAZON_PARTNER_TAG",
    "",
).strip()

AMAZON_PARTNER_TYPE = os.getenv(
    "AMAZON_PARTNER_TYPE",
    "Associates",
).strip()

AMAZON_REGION = os.getenv(
    "AMAZON_REGION",
    "eu-west-1",
).strip()

AMAZON_HOST = os.getenv(
    "AMAZON_HOST",
    "webservices.amazon.co.uk",
).strip()


# ============================================================
# YOUTUBE
# ============================================================

YOUTUBE_ENABLED = env_bool(
    "YOUTUBE_ENABLED",
    True,
)

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    "",
).strip()

YOUTUBE_CHANNEL_ID = os.getenv(
    "YOUTUBE_CHANNEL_ID",
    "",
).strip()

YOUTUBE_MAX_RESULTS = int(
    os.getenv(
        "YOUTUBE_MAX_RESULTS",
        "9",
    )
)


# ============================================================
# GEMINI AI
# ============================================================

GEMINI_API_KEYS = []
for _name in (
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "GEMINI_API_KEY_4",
):
    _value = os.getenv(_name, "").strip()
    if _value and not _value.startswith("PASTE_YOUR_"):
        GEMINI_API_KEYS.append(_value)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
).strip()
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "45"))
_gemini_cursor = 0


# ============================================================
# EBAY TOKEN CACHE
# ============================================================

_ebay_token: str | None = None
_ebay_expiry: float = 0


def ebay_token_url() -> str:

    if EBAY_ENV == "sandbox":
        return (
            "https://api.sandbox.ebay.com/"
            "identity/v1/oauth2/token"
        )

    return (
        "https://api.ebay.com/"
        "identity/v1/oauth2/token"
    )


def ebay_api_url(
    path: str,
) -> str:

    if EBAY_ENV == "sandbox":
        base = "https://api.sandbox.ebay.com"
    else:
        base = "https://api.ebay.com"

    return base + path


# ============================================================
# EBAY ACCESS TOKEN
# ============================================================

async def get_ebay_token() -> str | None:

    global _ebay_token
    global _ebay_expiry

    if not EBAY_ENABLED:
        return None

    if not EBAY_CLIENT_ID:
        return None

    if not EBAY_CLIENT_SECRET:
        return None

    if (
        _ebay_token
        and time.time()
        < _ebay_expiry - 60
    ):
        return _ebay_token

    credentials = (
        f"{EBAY_CLIENT_ID}:"
        f"{EBAY_CLIENT_SECRET}"
    )

    encoded = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": (
            f"Basic {encoded}"
        ),
        "Content-Type":
            "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type":
            "client_credentials",

        "scope":
            "https://api.ebay.com/"
            "oauth/api_scope",
    }

    try:

        async with httpx.AsyncClient(
            timeout=20,
        ) as client:

            response = await client.post(
                ebay_token_url(),
                headers=headers,
                data=data,
            )

        if response.status_code != 200:

            print(
                "eBay token error:",
                response.status_code,
                response.text,
            )

            return None

        payload = response.json()

        _ebay_token = payload.get(
            "access_token"
        )

        expires_in = int(
            payload.get(
                "expires_in",
                7200,
            )
        )

        _ebay_expiry = (
            time.time()
            + expires_in
        )

        return _ebay_token

    except Exception as exc:

        print(
            "eBay token exception:",
            repr(exc),
        )

        return None


# ============================================================
# EBAY HEADERS
# ============================================================

def ebay_headers(
    token: str,
) -> dict[str, str]:

    headers = {
        "Authorization":
            f"Bearer {token}",

        "Accept":
            "application/json",

        "X-EBAY-C-MARKETPLACE-ID":
            EBAY_MARKETPLACE,
    }

    if (
        EBAY_EPN_ENABLED
        and EBAY_EPN_CAMPAIGN_ID
    ):

        epn_context = (
            "affiliateCampaignId="
            f"{EBAY_EPN_CAMPAIGN_ID}"
        )

        if EBAY_EPN_REFERENCE_ID:

            epn_context += (
                ",affiliateReferenceId="
                f"{EBAY_EPN_REFERENCE_ID}"
            )

        headers[
            "X-EBAY-C-ENDUSERCTX"
        ] = epn_context

    return headers


# ============================================================
# EBAY SEARCH
# ============================================================

async def search_ebay(
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:

    token = await get_ebay_token()

    if not token:
        return []

    query = query.strip()

    if not query:
        return []

    limit = max(
        1,
        min(int(limit), 20),
    )

    url = ebay_api_url(
        "/buy/browse/v1/"
        "item_summary/search"
    )

    params = {
        "q": query,
        "limit": limit,
        "filter": (
            "buyingOptions:{FIXED_PRICE},"
            "itemLocationCountry:GB"
        ),
    }

    try:

        async with httpx.AsyncClient(
            timeout=25,
        ) as client:

            response = await client.get(
                url,
                headers=ebay_headers(token),
                params=params,
            )

        if response.status_code != 200:

            print(
                "eBay search error:",
                response.status_code,
                response.text,
            )

            return []

        data = response.json()

    except Exception as exc:

        print(
            "eBay search exception:",
            repr(exc),
        )

        return []

    items = data.get(
        "itemSummaries",
        [],
    )

    results = []

    for item in items:

        normal_url = item.get(
            "itemWebUrl"
        )

        affiliate_url = item.get(
            "itemAffiliateWebUrl"
        )

        # Normal eBay URL works without EPN.
        # Affiliate URL wins automatically when EPN
        # is configured and eBay returns one.

        buy_url = (
            affiliate_url
            or normal_url
        )

        if not buy_url:
            continue

        price = (
            item.get("price")
            or {}
        )

        image = (
            item.get("image")
            or {}
        )

        seller = (
            item.get("seller")
            or {}
        )

        results.append({
            "retailer": "eBay",

            "title": item.get(
                "title",
                "eBay item",
            ),

            "price": price.get(
                "value"
            ),

            "currency": price.get(
                "currency",
                "GBP",
            ),

            "url": buy_url,

            "normal_url":
                normal_url,

            "affiliate_url":
                affiliate_url,

            "affiliate":
                bool(affiliate_url),

            "item_id":
                item.get("itemId"),

            "image":
                image.get("imageUrl"),

            "condition":
                item.get("condition"),

            "seller":
                seller.get("username"),

            "source":
                "ebay",
        })

    return results


# ============================================================
# AMAZON
#
# Safe placeholder until Amazon PA-API request signing is
# implemented. Amazon being unavailable cannot break eBay.
# ============================================================

async def search_amazon(
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:

    if not AMAZON_ENABLED:
        return []

    if not (
        AMAZON_ACCESS_KEY
        and AMAZON_SECRET_KEY
        and AMAZON_PARTNER_TAG
    ):

        print(
            "Amazon enabled but credentials "
            "are incomplete."
        )

        return []

    print(
        "Amazon credentials detected. "
        "Amazon PA-API integration requires "
        "signed requests."
    )

    return []


# ============================================================
# UNIFIED RETAILER SEARCH
# ============================================================

async def retailer_search(
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:

    ebay_results, amazon_results = (
        await asyncio.gather(
            search_ebay(
                query,
                limit,
            ),
            search_amazon(
                query,
                limit,
            ),
        )
    )

    return (
        ebay_results
        + amazon_results
    )[:limit]


# ============================================================
# SEARCH REQUEST
# ============================================================

class SearchRequest(BaseModel):
    q: str
    limit: int = 8


# ============================================================
# SEARCH API
# ============================================================

@app.get("/api/search")
async def api_search(
    q: str = Query(
        ...,
        min_length=1,
    ),
    limit: int = Query(
        8,
        ge=1,
        le=20,
    ),
):

    products = await retailer_search(
        q,
        limit,
    )

    return {
        "query": q,
        "count": len(products),
        "products": products,

        "retailers": {
            "ebay": {
                "enabled":
                    EBAY_ENABLED,

                "configured": bool(
                    EBAY_CLIENT_ID
                    and EBAY_CLIENT_SECRET
                ),

                "epn_enabled":
                    EBAY_EPN_ENABLED,
            },

            "amazon": {
                "enabled":
                    AMAZON_ENABLED,

                "configured": bool(
                    AMAZON_ACCESS_KEY
                    and AMAZON_SECRET_KEY
                    and AMAZON_PARTNER_TAG
                ),
            },
        },
    }


@app.post("/api/search")
async def api_search_post(
    request: SearchRequest,
):

    products = await retailer_search(
        request.q,
        request.limit,
    )

    return {
        "query": request.q,
        "count": len(products),
        "products": products,
    }


# ============================================================
# YOUTUBE HELPERS
# ============================================================

async def youtube_get_uploads_playlist(
) -> str | None:

    if not YOUTUBE_ENABLED:
        return None

    if not YOUTUBE_API_KEY:
        return None

    if not YOUTUBE_CHANNEL_ID:
        return None

    url = (
        "https://www.googleapis.com/"
        "youtube/v3/channels"
    )

    params = {
        "part": "contentDetails",
        "id": YOUTUBE_CHANNEL_ID,
        "key": YOUTUBE_API_KEY,
    }

    try:

        async with httpx.AsyncClient(
            timeout=20,
        ) as client:

            response = await client.get(
                url,
                params=params,
            )

        if response.status_code != 200:

            print(
                "YouTube channel error:",
                response.status_code,
                response.text,
            )

            return None

        data = response.json()

        items = data.get(
            "items",
            [],
        )

        if not items:
            print(
                "YouTube channel not found."
            )

            return None

        related = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
        )

        return related.get(
            "uploads"
        )

    except Exception as exc:

        print(
            "YouTube playlist exception:",
            repr(exc),
        )

        return None


# ============================================================
# YOUTUBE VIDEO FETCH
# ============================================================

async def youtube_get_videos(
    max_results: int = 9,
) -> list[dict[str, Any]]:

    if not YOUTUBE_ENABLED:
        return []

    if not YOUTUBE_API_KEY:
        print(
            "YouTube API key missing."
        )
        return []

    if not YOUTUBE_CHANNEL_ID:
        print(
            "YouTube channel ID missing."
        )
        return []

    playlist_id = (
        await youtube_get_uploads_playlist()
    )

    if not playlist_id:
        return []

    max_results = max(
        1,
        min(
            int(max_results),
            50,
        ),
    )

    url = (
        "https://www.googleapis.com/"
        "youtube/v3/playlistItems"
    )

    params = {
        "part":
            "snippet,contentDetails",

        "playlistId":
            playlist_id,

        "maxResults":
            max_results,

        "key":
            YOUTUBE_API_KEY,
    }

    try:

        async with httpx.AsyncClient(
            timeout=20,
        ) as client:

            response = await client.get(
                url,
                params=params,
            )

        if response.status_code != 200:

            print(
                "YouTube videos error:",
                response.status_code,
                response.text,
            )

            return []

        data = response.json()

    except Exception as exc:

        print(
            "YouTube video exception:",
            repr(exc),
        )

        return []

    videos = []

    for item in data.get(
        "items",
        [],
    ):

        snippet = (
            item.get("snippet")
            or {}
        )

        resource = (
            snippet.get(
                "resourceId"
            )
            or {}
        )

        video_id = resource.get(
            "videoId"
        )

        if not video_id:
            continue

        thumbnails = (
            snippet.get(
                "thumbnails"
            )
            or {}
        )

        thumbnail = (
            thumbnails.get("maxres")
            or thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )

        videos.append({

            "id":
                video_id,

            "title":
                snippet.get(
                    "title",
                    "SK Builds video",
                ),

            "description":
                snippet.get(
                    "description",
                    "",
                ),

            "published_at":
                snippet.get(
                    "publishedAt"
                ),

            "thumbnail":
                thumbnail.get(
                    "url"
                ),

            "channel_title":
                snippet.get(
                    "channelTitle",
                    "SK Builds",
                ),

            "url":
                f"https://www.youtube.com/watch?v={video_id}",

            "embed_url":
                f"https://www.youtube.com/embed/{video_id}",

            "source":
                "youtube",
        })

    return videos


# ============================================================
# YOUTUBE API ENDPOINT
# ============================================================

@app.get("/api/youtube")
async def api_youtube(
    limit: int = Query(
        YOUTUBE_MAX_RESULTS,
        ge=1,
        le=50,
    ),
):

    videos = await youtube_get_videos(
        limit
    )

    return {
        "success": True,

        "enabled":
            YOUTUBE_ENABLED,

        "configured": bool(
            YOUTUBE_API_KEY
            and YOUTUBE_CHANNEL_ID
        ),

        "channel_id":
            YOUTUBE_CHANNEL_ID,

        "count":
            len(videos),

        "videos":
            videos,
    }


# ============================================================
# GEMINI HELPERS
# ============================================================

async def gemini_generate(
    prompt: str,
    temperature: float = 0.25,
) -> str | None:
    """Call Gemini from the backend. Missing/invalid keys never crash the app."""
    global _gemini_cursor

    if not GEMINI_API_KEYS:
        return None

    key_count = len(GEMINI_API_KEYS)
    for offset in range(key_count):
        key = GEMINI_API_KEYS[(_gemini_cursor + offset) % key_count]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent"
        )
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 5000,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
                response = await client.post(
                    url,
                    params={"key": key},
                    json=payload,
                )
            if response.status_code == 200:
                data = response.json()
                parts = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                text = "".join(
                    str(part.get("text", ""))
                    for part in parts
                    if isinstance(part, dict)
                ).strip()
                if text:
                    _gemini_cursor = (_gemini_cursor + offset + 1) % key_count
                    return text
            else:
                print("Gemini error:", response.status_code, response.text[:500])
        except Exception as exc:
            print("Gemini exception:", repr(exc))

    return None


def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


async def ai_pc_build(prompt: str) -> dict[str, Any] | None:
    """Generate the actual PC configuration with Gemini, independent of retailers."""
    ai_prompt = f"""
You are SK, an expert UK PC-building AI. Build a complete, compatible PC from this user brief:

{prompt}

Important rules:
- The AI build is the PRIMARY result. Retailer APIs are optional enrichment only.
- Use current, realistic PC components and UK pricing only as rough estimates; do not pretend an estimated price is live.
- Respect the stated budget, use case, performance target, aesthetics, noise and upgrade requirements.
- Ensure CPU socket, motherboard, RAM generation, PSU capacity, case fit and cooler compatibility make sense.
- Include CPU, GPU, motherboard, RAM, storage, PSU, case and CPU cooler where appropriate.
- Give a short reason for every choice and note any assumptions.
- Return ONLY valid JSON, with this shape:
{{
  "title": "...",
  "summary": "...",
  "estimated_total": 0,
  "estimated_wattage": 0,
  "components": [
    {{"type":"CPU","name":"...","estimated_price":0,"reason":"...","search_term":"..."}},
    {{"type":"GPU","name":"...","estimated_price":0,"reason":"...","search_term":"..."}}
  ],
  "compatibility": ["..."],
  "notes": ["..."]
}}
"""
    raw = await gemini_generate(ai_prompt, temperature=0.2)
    if not raw:
        return None

    import json
    try:
        data = json.loads(clean_json_text(raw))
    except Exception:
        # Ask Gemini for a compact repair if it returned fenced/extra prose.
        repair = await gemini_generate(
            "Convert the following into ONLY valid JSON matching the requested PC build schema. Do not add commentary.\n\n" + raw,
            temperature=0.0,
        )
        if not repair:
            return None
        try:
            data = json.loads(clean_json_text(repair))
        except Exception:
            return None

    if not isinstance(data, dict):
        return None
    components = data.get("components")
    if not isinstance(components, list):
        data["components"] = []
    return data


def build_fallback(prompt: str) -> dict[str, Any]:
    """Non-AI safety net so the builder never dies just because an AI key is missing."""
    return {
        "title": "SK Starter Configuration",
        "summary": (
            "SK could not reach the AI service, so this safe starter configuration "
            "is shown instead. Add a valid GEMINI_API_KEY to enable AI-generated builds."
        ),
        "estimated_total": 1000,
        "estimated_wattage": 550,
        "components": [
            {"type": "CPU", "name": "AMD Ryzen 5 7600", "estimated_price": 180, "reason": "Strong modern gaming CPU.", "search_term": "AMD Ryzen 5 7600"},
            {"type": "GPU", "name": "NVIDIA GeForce RTX 5070", "estimated_price": 550, "reason": "Strong 1440p gaming performance.", "search_term": "RTX 5070"},
            {"type": "Motherboard", "name": "B650 WiFi motherboard", "estimated_price": 140, "reason": "AM5 platform with upgrade room.", "search_term": "B650 WiFi motherboard"},
            {"type": "RAM", "name": "32GB DDR5-6000", "estimated_price": 90, "reason": "Good capacity and speed for modern gaming.", "search_term": "32GB DDR5 6000"},
            {"type": "Storage", "name": "1TB NVMe SSD", "estimated_price": 65, "reason": "Fast primary storage.", "search_term": "1TB NVMe SSD"},
            {"type": "PSU", "name": "750W 80+ Gold PSU", "estimated_price": 90, "reason": "Reliable headroom for the GPU.", "search_term": "750W 80 Plus Gold PSU"},
            {"type": "Case", "name": "Airflow ATX case", "estimated_price": 75, "reason": "Good airflow and compatibility.", "search_term": "ATX airflow PC case"},
            {"type": "Cooler", "name": "Tower CPU cooler", "estimated_price": 35, "reason": "Quiet, capable cooling.", "search_term": "AM5 tower CPU cooler"},
        ],
        "compatibility": ["AM5 CPU and B650 motherboard", "DDR5 memory", "750W PSU provides sensible headroom"],
        "notes": [f"Original brief: {prompt}", "Prices are estimates until live retailer results are attached."],
        "ai": False,
    }


# ============================================================
# ASK SK AI
# ============================================================

class AskRequest(BaseModel):
    message: str = ""
    question: str = ""


@app.post("/api/ask")
async def api_ask(request: AskRequest):
    message = (request.message or request.question).strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty."})

    prompt = f"""
You are SK, a helpful expert AI for PC hardware, software and technology.
Answer clearly and practically for a UK PC enthusiast. Do not invent live prices or retailer availability.
User question:
{message}
"""
    answer = await gemini_generate(prompt, temperature=0.35)
    if not answer:
        answer = (
            "SK AI is not connected right now. Your backend is running, but a valid "
            "GEMINI_API_KEY is required for live AI answers."
        )
    return {"success": True, "answer": answer, "ai_configured": bool(GEMINI_API_KEYS)}


# ============================================================
# PC BUILD REQUEST
# ============================================================

class BuildRequest(BaseModel):
    prompt: str = ""
    brief: str = ""
    limit: int = 8


def build_search_terms(prompt: str) -> list[str]:
    text = prompt.strip()
    if not text:
        return []
    terms = [text]
    lowered = text.lower()
    for keyword in [
        "gpu", "graphics card", "cpu", "processor", "motherboard",
        "ram", "memory", "ssd", "nvme", "power supply", "psu",
        "case", "cooler", "cpu cooler",
    ]:
        if keyword in lowered:
            terms.append(keyword)
    output, seen = [], set()
    for term in terms:
        clean = term.strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output[:8]


async def enrich_ai_components(components: list[dict[str, Any]], limit_per_component: int = 3) -> list[dict[str, Any]]:
    enriched = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name") or component.get("product_name") or "").strip()
        if not name:
            continue
        search_term = str(component.get("search_term") or name).strip()
        offers = await retailer_search(search_term, limit_per_component)
        best = offers[0] if offers else None
        enriched.append({
            **component,
            "price": (best or {}).get("price"),
            "currency": (best or {}).get("currency", "GBP"),
            "retailer": (best or {}).get("retailer"),
            "url": (best or {}).get("url"),
            "affiliate": bool((best or {}).get("affiliate")),
            "live_offer": bool(best),
            "retailer_offers": offers,
        })
    return enriched


@app.post("/api/build")
async def api_build(request: BuildRequest):
    prompt = (request.prompt or request.brief).strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Build requirements cannot be empty."})

    ai_build = await ai_pc_build(prompt)
    ai_used = bool(ai_build)
    build = ai_build or build_fallback(prompt)
    components = build.get("components") or []
    components = await enrich_ai_components(components, 3)

    # Recalculate only from live offers; never call missing retailer links an error.
    live_total = 0.0
    live_count = 0
    retailer_links = []
    for component in components:
        price = component.get("price")
        try:
            if price is not None:
                live_total += float(price)
                live_count += 1
        except (TypeError, ValueError):
            pass
        if component.get("url"):
            retailer_links.append({
                "retailer": component.get("retailer"),
                "title": component.get("name"),
                "price": component.get("price"),
                "currency": component.get("currency", "GBP"),
                "url": component.get("url"),
                "affiliate": component.get("affiliate", False),
            })

    # Also provide a small general search set for the existing shop/build cards.
    if not retailer_links:
        terms = build_search_terms(prompt)
        for term in terms[:2]:
            for product in await retailer_search(term, min(request.limit, 6)):
                if product.get("url"):
                    retailer_links.append({
                        "retailer": product.get("retailer"),
                        "title": product.get("title"),
                        "price": product.get("price"),
                        "currency": product.get("currency", "GBP"),
                        "url": product.get("url"),
                        "affiliate": product.get("affiliate", False),
                    })
                if len(retailer_links) >= request.limit:
                    break
            if len(retailer_links) >= request.limit:
                break

    return {
        "success": True,
        "requirements": prompt,
        "ai": ai_used,
        "ai_configured": bool(GEMINI_API_KEYS),
        "title": build.get("title", "SK Custom PC Build"),
        "summary": build.get("summary", ""),
        "estimated_total": build.get("estimated_total"),
        "estimated_wattage": build.get("estimated_wattage"),
        "compatibility": build.get("compatibility", []),
        "notes": build.get("notes", []),
        "components": components,
        "build": (
            f"{build.get('title', 'SK Custom PC Build')}\n\n"
            f"{build.get('summary', '')}\n\n"
            + "\n".join(
                f"{c.get('type', 'Component')}: {c.get('name', 'Unknown')}"
                + (f" — £{c.get('price')} live at {c.get('retailer')}" if c.get('price') is not None and c.get('retailer') else "")
                + f"\n  {c.get('reason', '')}"
                for c in components
            )
            + ("\n\nCompatibility:\n" + "\n".join(f"• {x}" for x in build.get("compatibility", [])) if build.get("compatibility") else "")
            + ("\n\nNotes:\n" + "\n".join(f"• {x}" for x in build.get("notes", [])) if build.get("notes") else "")
        ).strip(),
        "products": components,
        "retailer_links": retailer_links[:max(0, min(request.limit, 20))],
        "retailer_links_available": bool(retailer_links),
        "live_component_count": live_count,
        "live_total": round(live_total, 2) if live_count else None,
        "message": (
            "AI build generated. Live retailer offers attached."
            if ai_used and retailer_links
            else "AI build generated. Retailer links are optional and currently unavailable."
            if ai_used
            else "Starter build returned because the AI service is not configured."
        ),
    }


# ============================================================
# PC BUILDER RETAILER ENRICHMENT
# ============================================================

@app.post("/api/retailers/enrich")
async def enrich_retailers(payload: dict[str, Any]):
    """Match each AI-generated PC component against live retailer listings."""
    components = payload.get("components") or []

    if not isinstance(components, list):
        return JSONResponse(
            status_code=400,
            content={"error": "components must be a list"},
        )

    enriched = []
    total = 0.0
    has_total = False

    for component in components:
        if not isinstance(component, dict):
            continue

        name = str(
            component.get("name")
            or component.get("product_name")
            or component.get("title")
            or ""
        ).strip()
        component_type = component.get("type") or "Component"

        if not name:
            continue

        offers = await retailer_search(name, 5)
        offers = [x for x in offers if x.get("url")]

        best = offers[0] if offers else None
        price = best.get("price") if best else None

        if price is not None:
            try:
                total += float(price)
                has_total = True
            except (TypeError, ValueError):
                pass

        enriched.append({
            **component,
            "type": component_type,
            "name": name,
            "price": price,
            "currency": (best or {}).get("currency", "GBP"),
            "retailer": (best or {}).get("retailer"),
            "url": (best or {}).get("url"),
            "product_url": (best or {}).get("product_url"),
            "affiliate_url": (best or {}).get("affiliate_url"),
            "retailers": offers,
            "live_retailer": bool(offers),
        })

    return {
        "success": True,
        "components": enriched,
        "total": round(total, 2) if has_total else None,
        "retailer_links_available": any(x.get("url") for x in enriched),
    }


@app.post("/api/search")
async def api_search_post(request: SearchRequest):
    q = request.q.strip()
    if not q:
        return JSONResponse(status_code=400, content={"error": "Search query cannot be empty."})
    limit = max(1, min(int(request.limit), 20))
    products = await retailer_search(q, limit)
    return {
        "query": q,
        "count": len(products),
        "products": products,
        "retailers": {
            "ebay": {"enabled": EBAY_ENABLED, "configured": bool(EBAY_CLIENT_ID and EBAY_CLIENT_SECRET)},
            "amazon": {"enabled": AMAZON_ENABLED, "configured": bool(AMAZON_ACCESS_KEY and AMAZON_SECRET_KEY and AMAZON_PARTNER_TAG)},
        },
    }


# ============================================================
# RETAILER STATUS
# ============================================================

@app.get("/api/retailers")
async def retailer_status():

    return {

        "ebay": {

            "enabled":
                EBAY_ENABLED,

            "api_configured": bool(
                EBAY_CLIENT_ID
                and EBAY_CLIENT_SECRET
            ),

            "epn_enabled":
                EBAY_EPN_ENABLED,

            "epn_configured": bool(
                EBAY_EPN_CAMPAIGN_ID
            ),
        },

        "amazon": {

            "enabled":
                AMAZON_ENABLED,

            "configured": bool(
                AMAZON_ACCESS_KEY
                and AMAZON_SECRET_KEY
                and AMAZON_PARTNER_TAG
            ),
        },

        "youtube": {

            "enabled":
                YOUTUBE_ENABLED,

            "configured": bool(
                YOUTUBE_API_KEY
                and YOUTUBE_CHANNEL_ID
            ),
        },
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "app": "SK TECH",
        "version": "2.2",
    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():

    print("")
    print("=" * 60)
    print("SK TECH BACKEND")
    print("=" * 60)

    print(
        "eBay:",
        "ENABLED"
        if EBAY_ENABLED
        else "DISABLED",
    )

    print(
        "eBay API:",
        "CONFIGURED"
        if (
            EBAY_CLIENT_ID
            and EBAY_CLIENT_SECRET
        )
        else "MISSING",
    )

    print(
        "eBay EPN:",
        "ENABLED"
        if (
            EBAY_EPN_ENABLED
            and EBAY_EPN_CAMPAIGN_ID
        )
        else "OFF",
    )

    print(
        "Amazon:",
        "ENABLED"
        if AMAZON_ENABLED
        else "OFF",
    )

    print(
        "YouTube:",
        "ENABLED"
        if YOUTUBE_ENABLED
        else "DISABLED",
    )

    print(
        "YouTube API:",
        "CONFIGURED"
        if (
            YOUTUBE_API_KEY
            and YOUTUBE_CHANNEL_ID
        )
        else "MISSING",
    )

    print("=" * 60)
    print("")

