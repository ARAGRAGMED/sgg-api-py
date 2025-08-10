from typing import Optional, Dict, Any, List
import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import datetime

app = FastAPI(title="SGG Bulletin Officiel API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security setup
security = HTTPBearer(auto_error=False)
API_KEY = os.getenv("INTERNAL_API_KEY", "TESTAPIKEY")

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """Verify API key for internal endpoints"""
    if not credentials:
        return False
    return credentials.credentials == API_KEY

async def require_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Dependency to require valid API key"""
    if not await verify_api_key(credentials):
        raise HTTPException(
            status_code=401, 
            detail={"error": "Invalid or missing API key. This endpoint requires internal access."}
        )
    return True

# Load bulletins from local file
def load_bulletins_from_file() -> Dict[str, Any]:
    """Load bulletins from local JSON file"""
    try:
        with open("data/bulletins.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"bulletins": {"FR": [], "AR": []}}
    except json.JSONDecodeError:
        return {"bulletins": {"FR": [], "AR": []}}

# Filter by year helper function
def filter_by_year(bulletins: List[Dict[str, Any]], year: str) -> List[Dict[str, Any]]:
    """Filter bulletins by year"""
    if year == "current":
        current_year = str(datetime.datetime.utcnow().year)
        return [b for b in bulletins if b.get("BoDate", "").startswith(current_year)]
    else:
        return [b for b in bulletins if b.get("BoDate", "").startswith(year)]

@app.get("/", include_in_schema=False)
async def root():
    # Serve the main bulletin interface directly
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bulletin Officiel SGG - Interface</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f8fafc;
                color: #333;
                line-height: 1.6;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }

            /* Navigation */
            .nav {
                background: white;
                padding: 1rem 0;
                border-bottom: 1px solid #e0e0e0;
                margin-bottom: 2rem;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            .nav-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .nav-brand {
                font-size: 1.25rem;
                font-weight: 600;
                color: #007acc;
                text-decoration: none;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .nav-menu {
                display: flex;
                gap: 1rem;
                align-items: center;
            }

            .nav-link {
                color: #666;
                text-decoration: none;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                transition: all 0.2s ease;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .nav-link:hover {
                background: #f0f0f0;
                color: #333;
            }

            .nav-link.active {
                background: #007acc;
                color: white;
                position: relative;
            }

            .nav-link.active::after {
                content: '';
                position: absolute;
                bottom: -1px;
                left: 50%;
                transform: translateX(-50%);
                width: 20px;
                height: 2px;
                background: #007acc;
                border-radius: 1px;
            }

            /* Header */
            .header {
                text-align: center;
                margin-bottom: 3rem;
                padding: 3rem 0;
            }

            .header h1 {
                font-size: 3rem;
                font-weight: 700;
                color: #007acc;
                margin-bottom: 1rem;
            }

            .header p {
                font-size: 1.25rem;
                color: #666;
                max-width: 600px;
                margin: 0 auto;
            }

            /* Controls */
            .controls {
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                margin-bottom: 2rem;
            }

            .control-group {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }

            .control-item {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .control-item label {
                font-weight: 600;
                color: #333;
                font-size: 0.9rem;
            }

            .control-item select,
            .control-item input {
                padding: 0.75rem;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.2s ease;
                background: white;
            }

            .control-item select:focus,
            .control-item input:focus {
                outline: none;
                border-color: #007acc;
            }

            .search-container {
                position: relative;
                display: flex;
                align-items: center;
                width: 100%;
            }

            .clear-search-btn {
                position: absolute;
                right: 0.5rem;
                top: 50%;
                transform: translateY(-50%);
                background: #f0f0f0 !important;
                border: 1px solid #ddd !important;
                color: #666 !important;
                cursor: pointer !important;
                padding: 0.25rem 0 !important;
                border-radius: 4px !important;
                transition: all 0.2s ease !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center;
                z-index: 10;
                min-width: 24px;
                max-width: 24px;
                height: 24px;
                text-align: center;
            }

            .clear-search-btn:hover {
                background: #e0e0e0 !important;
                color: #333 !important;
            }

            .control-item button {
                padding: 0.75rem 1.5rem;
                background: #007acc;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .control-item button:hover {
                background: #005a9e;
                transform: translateY(-1px);
            }

            .control-item button:active {
                transform: translateY(0);
            }

            /* Load button specific styling */
            #load-btn {
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                font-weight: 700;
                padding: 1rem 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            #load-btn:hover {
                background: linear-gradient(135deg, #059669, #047857);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
            }

            #load-btn:active {
                transform: translateY(0);
                box-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);
            }

            #load-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }

            #load-btn:hover::before {
                left: 100%;
            }

            /* Results */
            .results-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                flex-wrap: wrap;
                gap: 1rem;
            }

            .results-count {
                font-size: 1.1rem;
                color: #666;
            }

            .view-toggle {
                display: flex;
                gap: 0.5rem;
            }

            .view-toggle button {
                padding: 0.5rem 1rem;
                background: white;
                border: 2px solid #e0e0e0;
                color: #666;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 500;
            }

            .view-toggle button.active {
                background: #007acc;
                border-color: #007acc;
                color: white;
            }

            .view-toggle button:hover:not(.active) {
                background: #f0f0f0;
                border-color: #ccc;
            }

            /* Bulletin Grid */
            .bulletin-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }

            .bulletin-card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                transition: all 0.2s ease;
                border: 1px solid #f0f0f0;
            }

            .bulletin-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            }

            .bulletin-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 1rem;
                gap: 1rem;
            }

            .bulletin-number {
                font-size: 1.5rem;
                font-weight: 700;
                color: #007acc;
            }

            .bulletin-date {
                font-size: 0.9rem;
                color: #666;
                background: #f8f9fa;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                white-space: nowrap;
            }

            .bulletin-actions {
                display: flex;
                gap: 0.5rem;
                margin-top: 1rem;
            }

            .btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 6px;
                font-size: 0.9rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }

            .btn-primary {
                background: #007acc;
                color: white;
            }

            .btn-primary:hover {
                background: #005a9e;
            }

            .btn-secondary {
                background: #f8f9fa;
                color: #666;
                border: 1px solid #e0e0e0;
            }

            .btn-secondary:hover {
                background: #e9ecef;
                color: #333;
            }

            /* Loading */
            .loading {
                text-align: center;
                padding: 3rem;
                color: #666;
            }

            .loading::after {
                content: '';
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 2px solid #e0e0e0;
                border-radius: 50%;
                border-top-color: #007acc;
                animation: spin 1s ease-in-out infinite;
                margin-left: 0.5rem;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            /* Icons */
            .icon {
                width: 1em;
                height: 1em;
            }

            .icon-sm {
                width: 0.875em;
                height: 0.875em;
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .nav-container {
                    padding: 0 1rem;
                    flex-direction: column;
                    gap: 1rem;
                }
                
                .nav-menu {
                    gap: 0.5rem;
                }
                
                .nav-link {
                    padding: 0.5rem 0.75rem;
                    font-size: 0.9rem;
                }
                
                .container {
                    padding: 1rem;
                }
                
                .header h1 {
                    font-size: 2rem;
                }
                
                .control-group {
                    grid-template-columns: 1fr;
                }
                
                .bulletin-grid {
                    grid-template-columns: 1fr;
                }
                
                .bulletin-header {
                    flex-direction: column;
                    gap: 1rem;
                    align-items: center;
                }
                
                .results-header {
                    flex-direction: column;
                    gap: 1rem;
                    align-items: flex-start;
                }
            }
        </style>
    </head>
    <body>
        <nav class="nav">
            <div class="nav-container">
                <a href="/" class="nav-brand">
                    <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M7,10H12V15H7V10Z"/>
                    </svg>
                    BO SGG
                </a>
                <div class="nav-menu">
                    <a href="/" class="nav-link active" id="nav-index">
                        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z"/>
                        </svg>
                        Interface
                    </a>
                    <a href="/docs" class="nav-link" id="nav-docs" target="_blank">
                        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M8,12V14H16V12H8M8,16V18H13V16H8Z"/>
                        </svg>
                        API Docs
                    </a>
                </div>
            </div>
        </nav>
        
        <div class="container">
            <div class="header">
                <h1>Bulletin Officiel SGG</h1>
                <p>Consultez et recherchez les bulletins officiels du Secrétariat Général du Gouvernement</p>
            </div>

            <div class="controls">
                <div class="control-group">
                    <div class="control-item">
                        <label for="language">Langue</label>
                        <select id="language">
                            <option value="ALL">Toutes les langues</option>
                            <option value="FR">Français</option>
                            <option value="AR">العربية</option>
                        </select>
                    </div>
                    <div class="control-item">
                        <label for="year">Année</label>
                        <select id="year">
                            <option value="">Toutes les années</option>
                            <option value="current">Année en cours</option>
                        </select>
                    </div>
                    <div class="control-item">
                        <label for="search">Recherche par numéro BO</label>
                        <div class="search-container">
                            <input type="text" id="search" placeholder="Ex: 7214">
                            <button class="clear-search-btn" id="clear-search-btn" style="display: none;">
                                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="control-item">
                        <label for="sort">Trier par</label>
                        <select id="sort">
                            <option value="date">Date</option>
                            <option value="number">Numéro</option>
                        </select>
                    </div>
                </div>
                <button id="load-btn" class="control-item button">Charger les données</button>
            </div>

            <div class="results-header">
                <div class="results-info">
                    <div class="results-count" id="results-count">Aucun résultat</div>
                    <div class="current-lang" id="current-lang" style="font-size: 0.9rem; color: #666; margin-top: 0.25rem;"></div>
                </div>
                <div class="view-toggle">
                    <button class="active" data-view="grid">Grille</button>
                    <button data-view="list">Liste</button>
                </div>
            </div>

            <div id="loading" class="loading" style="display: none;">Chargement en cours...</div>
            <div id="results" class="bulletin-grid"></div>
        </div>

        <script>
            let currentData = [];
            let currentView = 'grid';

            // DOM elements
            const languageSelect = document.getElementById('language');
            const yearSelect = document.getElementById('year');
            const searchInput = document.getElementById('search');
            const sortSelect = document.getElementById('sort');
            const loadBtn = document.getElementById('load-btn');
            const resultsCount = document.getElementById('results-count');
            const currentLangDiv = document.getElementById('current-lang');
            const resultsDiv = document.getElementById('results');
            const loadingDiv = document.getElementById('loading');
            const clearSearchBtn = document.getElementById('clear-search-btn');

            // Load data on page load
            window.addEventListener('load', function() {
                loadData();
                updateClearButton(); // Initialize clear button state
                updateNavigationState(); // Update navigation active state
                updateLanguageIndicator(); // Initialize language indicator
            });

            // Language change event
            languageSelect.addEventListener('change', function() {
                loadData();
                updateLanguageIndicator();
            });

            // Update navigation active state
            function updateNavigationState() {
                const currentPath = window.location.pathname;
                const navIndex = document.getElementById('nav-index');
                const navDocs = document.getElementById('nav-docs');
                
                if (currentPath === '/' || currentPath === '/index.html') {
                    navIndex.classList.add('active');
                    navDocs.classList.remove('active');
                } else if (currentPath === '/docs') {
                    navDocs.classList.add('active');
                    navIndex.classList.remove('active');
                }
            }

            // Update language indicator
            function updateLanguageIndicator() {
                const currentLang = languageSelect.value;
                let langLabel;
                if (currentLang === 'ALL') {
                    langLabel = 'Français + العربية';
                } else if (currentLang === 'FR') {
                    langLabel = 'Français';
                } else {
                    langLabel = 'العربية';
                }
                currentLangDiv.textContent = `Langue: ${langLabel}`;
            }

            // Scroll to top function
            function scrollToTop() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            // Load data function
            async function loadData() {
                try {
                    loadingDiv.style.display = 'block';
                    resultsDiv.style.display = 'none';
                    
                    const response = await fetch('/api/database');
                    if (!response.ok) {
                        throw new Error('Failed to fetch data');
                    }
                    
                    const data = await response.json();
                    const selectedLang = languageSelect.value;
                    
                    if (selectedLang === 'ALL') {
                        // Combine both French and Arabic bulletins with language markers
                        const frBulletins = (data.bulletins.FR || []).map(item => ({ ...item, language: 'FR' }));
                        const arBulletins = (data.bulletins.AR || []).map(item => ({ ...item, language: 'AR' }));
                        currentData = [...frBulletins, ...arBulletins];
                    } else {
                        currentData = (data.bulletins[selectedLang] || []).map(item => ({ ...item, language: selectedLang }));
                    }
                    
                    displayResults();
                } catch (error) {
                    console.error('Error loading data:', error);
                    resultsDiv.innerHTML = '<div style="text-align: center; color: #dc2626; padding: 2rem;">Erreur lors du chargement des données</div>';
                    resultsDiv.style.display = 'block';
                } finally {
                    loadingDiv.style.display = 'none';
                }
            }

            // Display results function
            function displayResults() {
                if (!currentData || currentData.length === 0) {
                    resultsDiv.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Aucun bulletin trouvé</div>';
                    resultsDiv.style.display = 'block';
                    resultsCount.textContent = 'Aucun résultat';
                    return;
                }

                let filteredData = [...currentData];

                // Apply search filter
                const searchTerm = searchInput.value.trim().toLowerCase();
                if (searchTerm) {
                    filteredData = filteredData.filter(item => 
                        item.BoNum && item.BoNum.toString().toLowerCase().includes(searchTerm)
                    );
                }

                // Apply year filter
                const selectedYear = yearSelect.value;
                if (selectedYear === 'current') {
                    const currentYear = new Date().getFullYear();
                    filteredData = filteredData.filter(item => {
                        if (!item.BoDate) return false;
                        const itemYear = new Date(item.BoDate).getFullYear();
                        return itemYear === currentYear;
                    });
                } else if (selectedYear) {
                    filteredData = filteredData.filter(item => {
                        if (!item.BoDate) return false;
                        const itemYear = new Date(item.BoDate).getFullYear();
                        return itemYear === parseInt(selectedYear);
                    });
                }

                // Apply sorting
                const sortBy = sortSelect.value;
                if (sortBy === 'date') {
                    filteredData.sort((a, b) => new Date(b.BoDate) - new Date(a.BoDate));
                } else if (sortBy === 'number') {
                    filteredData.sort((a, b) => parseInt(b.BoNum) - parseInt(a.BoNum));
                }

                // Update results count
                resultsCount.textContent = `${filteredData.length} résultat${filteredData.length !== 1 ? 's' : ''}`;

                // Display results
                if (currentView === 'grid') {
                    displayGridResults(filteredData);
                } else {
                    displayListResults(filteredData);
                }

                resultsDiv.style.display = 'block';
            }

            // Display grid results
            function displayGridResults(data) {
                resultsDiv.className = 'bulletin-grid';
                resultsDiv.innerHTML = data.map(item => {
                    // Determine language for each item based on data source
                    let langLabel, langColor;
                    if (item.language) {
                        // If item has explicit language field
                        langLabel = item.language === 'FR' ? 'Français' : 'العربية';
                        langColor = item.language === 'FR' ? '#007acc' : '#059669';
                    } else {
                        // Fallback to current selection
                        const currentLang = languageSelect.value;
                        langLabel = currentLang === 'FR' ? 'Français' : 'العربية';
                        langColor = currentLang === 'FR' ? '#007acc' : '#059669';
                    }
                    
                    return `
                        <div class="bulletin-card">
                            <div class="bulletin-header">
                                <div class="bulletin-number">BO ${item.BoNum}</div>
                                <div class="bulletin-date">${formatDate(item.BoDate)}</div>
                            </div>
                            <div class="bulletin-lang" style="margin: 0.5rem 0; padding: 0.25rem 0.75rem; background: ${langColor}; color: white; border-radius: 6px; font-size: 0.8rem; font-weight: 600; display: inline-block; text-align: center;">
                                ${langLabel}
                            </div>
                            <div class="bulletin-actions">
                                <a href="${item.BoUrl}" target="_blank" class="btn btn-primary">
                                    <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M7,10H12V15H7V10Z"/>
                                    </svg>
                                    Voir PDF
                                </a>
                                <button class="btn btn-secondary" onclick="copyToClipboard('${item.BoUrl}')">
                                    <svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M16,12V4H17V2H7V4H8V12H6L12,18L18,12H16M2,22V20H22V22H2Z"/>
                                    </svg>
                                    Copier le lien
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Display list results
            function displayListResults(data) {
                resultsDiv.className = '';
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = data.map(item => {
                    // Determine language for each item based on data source
                    let langLabel, langColor;
                    if (item.language) {
                        // If item has explicit language field
                        langLabel = item.language === 'FR' ? 'Français' : 'العربية';
                        langColor = item.language === 'FR' ? '#007acc' : '#059669';
                    } else {
                        // Fallback to current selection
                        const currentLang = languageSelect.value;
                        langLabel = currentLang === 'FR' ? 'Français' : 'العربية';
                        langColor = currentLang === 'FR' ? '#007acc' : '#059669';
                    }
                    
                    return `
                        <div class="bulletin-card" style="margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>BO ${item.BoNum}</strong> - ${formatDate(item.BoDate)}
                                    <span style="margin-left: 0.5rem; padding: 0.25rem 0.75rem; background: ${langColor}; color: white; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">
                                        ${langLabel}
                                    </span>
                                </div>
                                <div>
                                    <a href="${item.BoUrl}" target="_blank" class="btn btn-primary">Voir PDF</a>
                                    <button class="btn btn-secondary" onclick="copyToClipboard('${item.BoUrl}')">Copier le lien</button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Format date function
            function formatDate(dateString) {
                if (!dateString) return 'Date inconnue';
                try {
                    const date = new Date(dateString);
                    return date.toLocaleDateString('fr-FR', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    });
                } catch (error) {
                    return 'Date invalide';
                }
            }

            // Copy to clipboard function
            function copyToClipboard(text) {
                navigator.clipboard.writeText(text).then(() => {
                    // Show a temporary success message
                    const btn = event.target.closest('button');
                    const originalText = btn.innerHTML;
                    btn.innerHTML = 'Copié !';
                    btn.style.background = '#10b981';
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.style.background = '';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            }

            // Event listeners
            languageSelect.addEventListener('change', loadData);
            yearSelect.addEventListener('change', displayResults);
            searchInput.addEventListener('input', displayResults);
            sortSelect.addEventListener('change', displayResults);
            loadBtn.addEventListener('click', loadData);

            // View toggle functionality
            document.querySelectorAll('.view-toggle button').forEach(button => {
                button.addEventListener('click', function() {
                    document.querySelectorAll('.view-toggle button').forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                    currentView = this.dataset.view;
                    displayResults();
                });
            });

            // Clear search functionality
            function clearSearch() {
                searchInput.value = '';
                displayResults();
                searchInput.focus();
            }

            function updateClearButton() {
                const hasValue = searchInput.value.trim().length > 0;
                clearSearchBtn.style.display = hasValue ? 'flex' : 'none';
            }

            searchInput.addEventListener('input', updateClearButton);
            searchInput.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    displayResults();
                }
                updateClearButton();
            });
            clearSearchBtn.addEventListener('click', clearSearch);

            // Populate year options
            function populateYearOptions() {
                const currentYear = new Date().getFullYear();
                for (let year = currentYear; year >= 2000; year--) {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    yearSelect.appendChild(option);
                }
            }

            // Initialize year options
            populateYearOptions();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/index.html", include_in_schema=False)
async def index_page():
    # Serve the main bulletin interface directly
    return await root()

# Public endpoints (no API key required)
@app.get("/api/database")
async def get_database():
    """Get the current database content from local storage (public access)"""
    data = load_bulletins_from_file()
    return data

@app.get("/api/BO/local/FR")
async def api_bo_local_fr(year: Optional[str] = Query(None, description="Filter by year (e.g., 2024) or 'current'. If not specified, returns all bulletins from local database.")):
    """Get French BOs from local database (public access)"""
    data = load_bulletins_from_file()
    fr_bulletins = data.get("bulletins", {}).get("FR", [])
    
    if not fr_bulletins:
        raise HTTPException(status_code=404, detail={"error": "No French Bulletin Officiel found in local database"})
    
    if year is not None:
        filtered = filter_by_year(fr_bulletins, year)
        if not filtered:
            raise HTTPException(status_code=404, detail={"error": f"No French Bulletin Officiel found for year {year} in local database"})
        return filtered
    
    return fr_bulletins

@app.get("/api/BO/local/AR")
async def api_bo_local_ar(year: Optional[str] = Query(None, description="Filter by year (e.g., 2024) or 'current'. If not specified, returns all bulletins from local database.")):
    """Get Arabic BOs from local database (public access)"""
    data = load_bulletins_from_file()
    ar_bulletins = data.get("bulletins", {}).get("AR", [])
    
    if not ar_bulletins:
        raise HTTPException(status_code=404, detail={"error": "No Arabic Bulletin Officiel found in local database"})
    
    if year is not None:
        filtered = filter_by_year(ar_bulletins, year)
        if not filtered:
            raise HTTPException(status_code=404, detail={"error": f"No Arabic Bulletin Officiel found for year {year} in local database"})
        return filtered
    
    return ar_bulletins

# Internal endpoints (require API key)
@app.get("/api/BO/FR/internal")
async def api_bo_fr_internal(api_key: bool = Depends(require_api_key)):
    """Get French BOs from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/FR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from external API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/BO/ALL/FR/internal")
async def api_bo_all_fr_internal(api_key: bool = Depends(require_api_key)):
    """Get all French BOs from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/ALL/FR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from external API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/BO/AR/internal")
async def api_bo_ar_internal(api_key: bool = Depends(require_api_key)):
    """Get Arabic BOs from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/AR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from external API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/BO/ALL/AR/internal")
async def api_bo_all_ar_internal(api_key: bool = Depends(require_api_key)):
    """Get all Arabic BOs from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/ALL/AR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from external API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/BO/Text/FR/internal")
async def api_bo_text_fr_internal(api_key: bool = Depends(require_api_key)):
    """Get French BO text from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/Text/FR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from external API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/BO/Text/AR/internal")
async def api_bo_text_ar_internal(api_key: bool = Depends(require_api_key)):
    """Get Arabic BO text from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://aicrafters-scraper-api.vercel.app/api/BO/Text/AR")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/database/refresh/internal")
async def refresh_database_internal(api_key: bool = Depends(require_api_key)):
    """Refresh database from SGG website - INTERNAL USE ONLY (requires API key)"""
    try:
        # This would typically involve fetching fresh data and updating the local database
        # For now, we'll return a success message
        return {"message": "Database refresh initiated", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/test-proxy")
async def test_proxy():
    """Test proxy functionality with free proxy services"""
    import httpx
    
    # Test 1: Direct access (should fail from Vercel)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://www.sgg.gov.ma/BulletinOfficiel.aspx")
            direct_status = response.status_code
            direct_content = len(response.text) if response.status_code == 200 else "Failed"
    except Exception as e:
        direct_status = "Error"
        direct_content = str(e)
    
    # Test 2: Free proxy service (cors-anywhere)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            proxy_url = f"https://cors-anywhere.herokuapp.com/https://www.sgg.gov.ma/BulletinOfficiel.aspx"
            response = await client.get(proxy_url)
            proxy_status = response.status_code
            proxy_content = len(response.text) if response.status_code == 200 else "Failed"
    except Exception as e:
        proxy_status = "Error"
        proxy_content = str(e)
    
    # Test 3: Another free proxy (allorigins)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            proxy_url = f"https://api.allorigins.win/get?url={httpx.URL('https://www.sgg.gov.ma/BulletinOfficiel.aspx')}"
            response = await client.get(proxy_url)
            allorigins_status = response.status_code
            allorigins_content = len(response.text) if response.status_code == 200 else "Failed"
    except Exception as e:
        allorigins_status = "Error"
        allorigins_content = str(e)
    
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "direct_access": {
            "status": direct_status,
            "content_length": direct_content
        },
        "cors_anywhere_proxy": {
            "status": proxy_status,
            "content_length": proxy_content
        },
        "allorigins_proxy": {
            "status": allorigins_status,
            "content_length": allorigins_content
        },
        "recommendation": "Check which proxy works best for your use case"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}
