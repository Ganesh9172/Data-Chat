import os
import re
import json
import html
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

def clean_search_query(query: str) -> str:
    """
    Cleans and optimizes a user question for video search.
    Removes conversational prefixes and noise.
    """
    q = query.strip()
    # Remove leading conversational filler
    patterns = [
        r"^(can you please tell me|can you tell me|please tell me|tell me|how do i|how to|what is|how can i|could you tell me)\s+",
        r"^(i want to know|i need to know|do you know)\s+"
    ]
    for p in patterns:
        q = re.sub(p, "", q, flags=re.IGNORECASE)

    # Remove trailing punctuation
    q = re.sub(r"[?!.,;]+$", "", q).strip()
    return q if q else query.strip()

def search_related_youtube_video(query: str) -> Optional[Dict[str, str]]:
    """
    Searches YouTube for exactly ONE video relevant to the user query.
    
    Resilience:
    - Never throws an exception.
    - If search fails, times out, or returns no results, safely returns None.
    - Uses official YouTube Data API v3 with provided API key, with automatic fallback
      to direct query extraction if the API call fails or encounters an issue.
    """
    if not query or len(query.strip()) < 3:
        return None

    # Filter out pure confirmation / cancellation words
    lower = query.strip().lower()
    if lower in {"yes", "no", "cancel", "confirm", "ok", "thanks", "thank you", "revert update"}:
        return None

    cleaned_q = clean_search_query(query)
    search_term = f"{cleaned_q} heating" if not any(w in cleaned_q.lower() for w in ["boiler", "heating", "hydronic"]) else cleaned_q

    # Method 1: Official YouTube Data API v3
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip() or "AIzaSyACik3kC1K0PYMU5VnCL_ZuPMUVsVY5Yqs"
    if api_key and api_key != "your_youtube_api_key_here":
        try:
            api_url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet&type=video&maxResults=1"
                f"&q={urllib.parse.quote(search_term)}"
                f"&key={api_key}"
            )
            req = urllib.request.Request(api_url, headers={"User-Agent": "FirebirdAI/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                if items:
                    item = items[0]
                    vid = item.get("id", {}).get("videoId")
                    snippet = item.get("snippet", {})
                    raw_title = snippet.get("title", "")
                    title = html.unescape(raw_title).strip()
                    thumbs = snippet.get("thumbnails", {})
                    thumb_url = (
                        thumbs.get("high", {}).get("url") or
                        thumbs.get("medium", {}).get("url") or
                        thumbs.get("default", {}).get("url") or
                        f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                    )
                    if vid and title:
                        return {
                            "video_id": vid,
                            "title": title,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "thumbnail_url": thumb_url
                        }
        except Exception as e:
            # Silently fall back to web parser
            pass

    # Method 2: High-speed YouTube web search fallback (no API key required)
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

            # Try parsing structured JSON in ytInitialData
            m = re.search(r"var ytInitialData = ({.*?});</script>", html)
            if m:
                data = json.loads(m.group(1))
                sections = (
                    data.get("contents", {})
                    .get("twoColumnSearchResultsRenderer", {})
                    .get("primaryContents", {})
                    .get("sectionListRenderer", {})
                    .get("contents", [])
                )
                for sec in sections:
                    items = sec.get("itemSectionRenderer", {}).get("contents", [])
                    for item in items:
                        v = item.get("videoRenderer")
                        if v and "videoId" in v:
                            vid = v["videoId"]
                            title_runs = v.get("title", {}).get("runs", [])
                            title = title_runs[0].get("text", "") if title_runs else ""
                            thumbs = v.get("thumbnail", {}).get("thumbnails", [])
                            thumb_url = thumbs[-1]["url"] if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                            if vid and title:
                                return {
                                    "video_id": vid,
                                    "title": title,
                                    "url": f"https://www.youtube.com/watch?v={vid}",
                                    "thumbnail_url": thumb_url
                                }

            # Fallback regex for videoId if initial data wasn't found
            vids = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html)
            if vids:
                first_vid = vids[0]
                return {
                    "video_id": first_vid,
                    "title": f"Watch related video on {cleaned_q}",
                    "url": f"https://www.youtube.com/watch?v={first_vid}",
                    "thumbnail_url": f"https://i.ytimg.com/vi/{first_vid}/hqdefault.jpg"
                }
    except Exception as e:
        # Silently fail without error to never affect the answer
        return None

    return None
