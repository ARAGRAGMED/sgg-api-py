# Bulletin Officiel API (Python)

FastAPI implementation of the SGG API that surfaces Moroccan Bulletin Officiel metadata and full-text content in French and Arabic.

- Original inspiration: `mounseflit/SGG-API` (Node/Express)

## Security & Access Control

### **API Key Protection**
Endpoints that fetch data directly from external websites (SGG) are protected with API key authentication to prevent abuse and rate limiting issues.

**Setup:**
1. Copy `env.template` to `.env`
2. Set your `INTERNAL_API_KEY` in the `.env` file
3. Restart the application

**Usage:**
```bash
# Include API key in Authorization header
curl -H "Authorization: Bearer your-secret-api-key-here" \
     http://localhost:3003/api/BO/FR/internal
```

### **Endpoint Categories**

#### **🔓 Public Endpoints** (No API key required)
- `GET /api/health` - Health check
- `GET /api/database` - Local database content
- `GET /api/database/public` - Local database content (alias)
- `GET /api/BO/local/FR` - French BOs from local database
- `GET /api/BO/local/AR` - Arabic BOs from local database
- `GET /api/database/status` - Database status and statistics
- `GET /api/database/test` - Test database structure

#### **🔐 Internal Endpoints** (API key required)
- `GET /api/BO/FR` - Latest French bulletin metadata (direct from SGG)
- `GET /api/BO/FR/internal` - Latest French bulletin metadata (direct from SGG)
- `GET /api/BO/ALL/FR` - All French bulletins metadata (direct from SGG)
- `GET /api/BO/ALL/FR/internal` - All French bulletins metadata (direct from SGG)
- `GET /api/BO/AR` - Latest Arabic bulletin metadata (direct from SGG)
- `GET /api/BO/AR/internal` - Latest Arabic bulletin metadata (direct from SGG)
- `GET /api/BO/ALL/AR` - All Arabic bulletins metadata (direct from SGG)
- `GET /api/BO/ALL/AR/internal` - All Arabic bulletins metadata (direct from SGG)
- `GET /api/BO/Text/FR` - Full text of latest French bulletin (direct from SGG)
- `GET /api/BO/Text/FR/internal` - Full text of latest French bulletin (direct from SGG)
- `GET /api/BO/Text/AR` - Full text of latest Arabic bulletin (direct from SGG)
- `GET /api/BO/Text/AR/internal` - Full text of latest Arabic bulletin (direct from SGG)
- `GET /api/database/refresh` - Refresh database from SGG
- `GET /api/database/refresh/internal` - Refresh database from SGG (with API key)

**Note:** Internal endpoints make direct requests to external websites and should be used sparingly to avoid rate limiting.

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

- `INTERNAL_API_KEY` (required for internal endpoints)
  - Secret key for accessing endpoints that fetch data directly from SGG
  - Set this in your `.env` file (copy from `env.template`)
- `SCRAPER_API_BASE` (default: `https://aicrafters-scraper-api.vercel.app`)
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

### **Public Endpoints** (No API key required)
```bash
# Health check
curl "http://127.0.0.1:3003/api/health"

# Local database content
curl "http://127.0.0.1:3003/api/database"

# French BOs from local database (2024)
curl "http://127.0.0.1:3003/api/BO/local/FR?year=2024"

# Arabic BOs from local database (current year)
curl "http://127.0.0.1:3003/api/BO/local/AR?year=current"

# Database status
curl "http://127.0.0.1:3003/api/database/status"
```

### **Internal Endpoints** (API key required)
```bash
# Set your API key
export API_KEY="your-secret-api-key-here"

# Latest French metadata (direct from SGG)
curl -H "Authorization: Bearer $API_KEY" \
     "http://127.0.0.1:3003/api/BO/FR/internal"

# All Arabic metadata this year (direct from SGG)
curl -H "Authorization: Bearer $API_KEY" \
     "http://127.0.0.1:3003/api/BO/ALL/AR/internal?year=current"

# Full text (French) – prints first 300 chars
curl -H "Authorization: Bearer $API_KEY" \
     "http://127.0.0.1:3003/api/BO/Text/FR/internal" | \
     python -c 'import sys,json;print(json.load(sys.stdin)["text"][:300])'

# Refresh database from SGG
curl -H "Authorization: Bearer $API_KEY" \
     "http://127.0.0.1:3003/api/database/refresh/internal"
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
