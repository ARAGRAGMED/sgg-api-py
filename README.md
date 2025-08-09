# Bulletin Officiel API (Python)

FastAPI implementation of the SGG API that surfaces Moroccan Bulletin Officiel metadata and full-text content in French and Arabic.

- Original inspiration: `mounseflit/SGG-API` (Node/Express)

## Endpoints

- GET `/api/BO/FR`: Latest French bulletin metadata
- GET `/api/BO/ALL/FR`: All French bulletins metadata
- GET `/api/BO/Text/FR`: Full text of the latest French bulletin
- GET `/api/BO/AR`: Latest Arabic bulletin metadata
- GET `/api/BO/ALL/AR`: All Arabic bulletins metadata
- GET `/api/BO/Text/AR`: Full text of the latest Arabic bulletin
- GET `/api/health`: Health check

Response shape (example):
```json
{
  "BoId": 5790,
  "BoNum": "7214",
  "BoDate": "2023-06-22T00:00:00.000Z",
  "BoUrl": "https://www.sgg.gov.ma/Portals/1/BO/2023/BO_7214_Ar.pdf"
}
```

## Requirements

- Python 3.9+

## Environment variables

- `SCRAPER_API_BASE` (default: `https://scraper-api-py.vercel.app`)
  - Used to fetch page scripts to derive `ModuleId` and `TabId` dynamically
- `PDF2TEXT_BASE` (default: `https://pdf2text-api-py.vercel.app`)
  - Used to extract text content from bulletin PDFs

## Local setup

```bash
cd sgg-api-py
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3003
```

Open `http://127.0.0.1:3003/api/health`.

## Quick examples

```bash
# Health
curl "http://127.0.0.1:3003/api/health"

# Latest French metadata
curl "http://127.0.0.1:3003/api/BO/FR"

# All Arabic metadata (first item)
curl "http://127.0.0.1:3003/api/BO/ALL/AR"

# Full text (French) – prints first 300 chars
curl "http://127.0.0.1:3003/api/BO/Text/FR" | python -c 'import sys,json;print(json.load(sys.stdin)["text"][:300])'
```

## Deployment (Vercel)

This project is already configured for Vercel Python serverless:
- `api/index.py` exposes the ASGI `app`
- `vercel.json` rewrites all routes to the ASGI function
- `requirements.txt` at project root

Deploy options:

- Via Vercel CLI:
```bash
npm i -g vercel
vercel login
cd sgg-api-py
vercel
vercel --prod
```

- Via Vercel dashboard:
  - New Project → Import GitHub repo containing `sgg-api-py`
  - Deploy

## Notes

- The API calls SGG’s backend endpoint (`/DesktopModules/MVC/TableListBO/BO/AjaxMethod`) using `ModuleId` and `TabId` parsed from the public pages. If upstream changes, IDs parsing may need updates.
- External services (`SCRAPER_API_BASE`, `PDF2TEXT_BASE`) must be reachable for dynamic ID discovery and PDF text extraction.
- CORS is enabled for all origins.
