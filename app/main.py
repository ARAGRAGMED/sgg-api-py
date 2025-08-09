from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx
import os
import re

app = FastAPI(title="Bulletin Officiel API (Python)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCRAPER_BASE = os.getenv("SCRAPER_API_BASE", "https://scraper-api-py.vercel.app")
PDF2TEXT_BASE = os.getenv("PDF2TEXT_BASE", "https://pdf2text-api-py.vercel.app")

SGG_AJAX_URL = "https://www.sgg.gov.ma/DesktopModules/MVC/TableListBO/BO/AjaxMethod"


async def get_module_and_tab(lang: str) -> Dict[str, Optional[str]]:
    if lang == "fr":
        page_url = "https://www.sgg.gov.ma/BulletinOfficiel.aspx"
    else:
        page_url = "https://www.sgg.gov.ma/arabe/BulletinOfficiel.aspx"

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{SCRAPER_BASE}/scrape", params={"url": page_url, "type": "scripts"})
        r.raise_for_status()
        data = r.json()
        scripts_str = str(data.get("result", ""))

    module_matches = list(re.finditer(r"ModuleId\s*=\s*(\d+)", scripts_str))
    tab_matches = list(re.finditer(r"var\s+TabId\s*=\s*(\d+)", scripts_str))

    tab_id = tab_matches[0].group(1) if tab_matches else None

    module_id: Optional[str] = None
    if module_matches:
        nums = [int(m.group(1)) for m in module_matches]
        if lang == "fr":
            module_id = str(min(nums))
        else:
            module_id = str(max(nums))

    return {"moduleId": module_id, "tabId": tab_id}


def parse_bo_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    bo_date_raw = str(raw.get("BoDate", ""))
    # Expected like /Date(1687392000000)/
    ms_match = re.search(r"\d+", bo_date_raw)
    iso_date = None
    if ms_match:
        try:
            ms = int(ms_match.group(0))
            # Convert ms to ISO string
            import datetime
            iso_date = datetime.datetime.utcfromtimestamp(ms / 1000.0).isoformat() + "Z"
        except Exception:
            iso_date = None

    bo_url = raw.get("BoUrl", "")
    if bo_url and not bo_url.startswith("http"):
        bo_url = f"https://www.sgg.gov.ma{bo_url}"

    return {
        "BoId": raw.get("BoId"),
        "BoNum": raw.get("BoNum"),
        "BoDate": iso_date,
        "BoUrl": bo_url,
    }


async def fetch_latest_bo(lang: str, fallback_module: str, fallback_tab: str) -> Optional[Dict[str, Any]]:
    try:
        ids = await get_module_and_tab(lang)
        module_id = ids.get("moduleId") or fallback_module
        tab_id = ids.get("tabId") or fallback_tab
    except Exception:
        module_id = fallback_module
        tab_id = fallback_tab

    headers = {"ModuleId": module_id, "TabId": tab_id, "RequestVerificationToken": ""}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(SGG_AJAX_URL, headers=headers)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list) and arr:
            return parse_bo_item(arr[0])
        return None


async def fetch_all_bo(lang: str, fallback_module: str, fallback_tab: str) -> Optional[List[Dict[str, Any]]]:
    try:
        ids = await get_module_and_tab(lang)
        module_id = ids.get("moduleId") or fallback_module
        tab_id = ids.get("tabId") or fallback_tab
    except Exception:
        module_id = fallback_module
        tab_id = fallback_tab

    headers = {"ModuleId": module_id, "TabId": tab_id, "RequestVerificationToken": ""}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(SGG_AJAX_URL, headers=headers)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list):
            return [parse_bo_item(item) for item in arr]
        return None


@app.get("/api/BO/FR")
async def api_bo_fr():
    bo = await fetch_latest_bo(lang="fr", fallback_module="2873", fallback_tab="775")
    if not bo:
        raise HTTPException(status_code=404, detail={"error": "Latest Bulletin Officiel not found"})
    return bo


@app.get("/api/BO/ALL/FR")
async def api_bo_all_fr():
    arr = await fetch_all_bo(lang="fr", fallback_module="2873", fallback_tab="775")
    if not arr:
        raise HTTPException(status_code=404, detail={"error": "No French Bulletin Officiel was found"})
    return arr


@app.get("/api/BO/AR")
async def api_bo_ar():
    bo = await fetch_latest_bo(lang="ar", fallback_module="3111", fallback_tab="847")
    if not bo:
        raise HTTPException(status_code=404, detail={"error": "Latest Bulletin Officiel not found"})
    return bo


@app.get("/api/BO/ALL/AR")
async def api_bo_all_ar():
    arr = await fetch_all_bo(lang="ar", fallback_module="3111", fallback_tab="847")
    if not arr:
        raise HTTPException(status_code=404, detail={"error": "No Arabic Bulletin Officiel was found"})
    return arr


async def extract_pdf_text(pdf_url: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{PDF2TEXT_BASE}/api/pdf-text-all", params={"pdfUrl": pdf_url})
        r.raise_for_status()
        data = r.json()
        return (data.get("text") or "").strip()


@app.get("/api/BO/Text/FR")
async def api_bo_text_fr():
    bo = await fetch_latest_bo(lang="fr", fallback_module="2873", fallback_tab="775")
    if not bo:
        raise HTTPException(status_code=404, detail={"error": "Latest Bulletin Officiel not found"})
    text = await extract_pdf_text(bo["BoUrl"]) if bo.get("BoUrl") else ""
    if not text:
        raise HTTPException(status_code=404, detail={"error": "Text content not found"})
    return {"text": text}


@app.get("/api/BO/Text/AR")
async def api_bo_text_ar():
    bo = await fetch_latest_bo(lang="ar", fallback_module="3111", fallback_tab="847")
    if not bo:
        raise HTTPException(status_code=404, detail={"error": "Latest Bulletin Officiel not found"})
    text = await extract_pdf_text(bo["BoUrl"]) if bo.get("BoUrl") else ""
    if not text:
        raise HTTPException(status_code=404, detail={"error": "Text content not found"})
    return {"text": text}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    # Serve the rich index page from the original project inline for simplicity
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html><head><meta charset=\"utf-8\"><title>Bulletin Officiel API (Python)</title></head>
    <body style=\"font-family: Arial; padding: 24px; max-width: 960px; margin: auto;\">
      <h1>Bulletin Officiel API (Python)</h1>
      <p>Endpoints:</p>
      <ul>
        <li>GET <code>/api/BO/FR</code></li>
        <li>GET <code>/api/BO/ALL/FR</code></li>
        <li>GET <code>/api/BO/Text/FR</code></li>
        <li>GET <code>/api/BO/AR</code></li>
        <li>GET <code>/api/BO/ALL/AR</code></li>
        <li>GET <code>/api/BO/Text/AR</code></li>
        <li>GET <code>/api/health</code></li>
      </ul>
      <p>Set env <code>SCRAPER_API_BASE</code> and <code>PDF2TEXT_BASE</code> to override defaults.</p>
    </body></html>
    """)
