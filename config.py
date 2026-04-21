"""
config.py — Sélecteurs et constantes centralisés.
Modifier ici si CongoBet change sa structure HTML.
"""

# ── URLs ──────────────────────────────────────────────────────
URL_MATCHES = "https://www.congobet.net/virtual/category/instant-league/8035/matches"
URL_RESULTS = "https://www.congobet.net/virtual/category/instant-league/8035/results"

# ── Timeouts (ms) ─────────────────────────────────────────────
# Réduits pour accélérer le scraping sans sacrifier la fiabilité

TIMEOUT_PAGE_LOAD   = 90_000   # 120→90s : la page charge en <30s en pratique
TIMEOUT_ELEMENT     = 15_000   # 30→15s  : les éléments sont là rapidement
TIMEOUT_SHORT       = 6_000    # 10→6s   : actions rapides
TIMEOUT_ROUND_CLICK = 800      # après clic sur un round

# ── Attentes fixes réduites (ms) ──────────────────────────────
WAIT_AFTER_GOTO      = 1200    # 2000→1200ms : page chargée via networkidle
WAIT_AFTER_MARKET    = 400     # 800→400ms   : après clic marché (G/NG/1X2)
WAIT_AFTER_ROUND     = 200     # 400→200ms   : après clic round
WAIT_GNG_INIT        = 300     # 1000→300ms  : attente initiale G/NG
WAIT_GNG_PER_ROUND   = 150     # 300→150ms   : entre rounds G/NG

# ── Retries ───────────────────────────────────────────────────
MAX_RETRIES   = 2              # 3→2 : un retry suffit
RETRY_DELAY_S = 1.5            # 2→1.5s

# ── Sélecteurs CongoBet ───────────────────────────────────────
SEL = {
    # Rounds / tabs
    "round_tabs"   : "hg-instant-league-round-picker li",
    "round_time"   : ".time",

    # Marchés
    "market_active": "hg-event-bet-type-picker button.active",
    "market_button": "hg-event-bet-type-picker button",
    "market_select": "hg-event-bet-type-picker hg-select .selected",
    "market_option": "hg-event-bet-type-picker hg-select .dropdown .option",

    # Matchs (cotes)
    "match_any"    : "div.match",
    "match_1x2"    : "div.match.bet-type-1x2",
    "team_spans"   : ".teams span",
    "odds_spans"   : "span.odds",

    # Résultats
    "results_container": "hg-instant-league-results .result-container",
    "results_header"   : ".header",
    "results_row"      : ".match-results .row",
    "team_span"        : ".team span",
    "match_score"      : ".match-score",
    "halftime_score"   : ".halfTime-score",
    "show_more_btn"    : "text=/Afficher plus/i",
}

# Marchés
MARKET_GNG = "G/NG"
MARKET_1X2 = "1X2"

# Viewport — réduit pour charger moins de DOM hors-écran
VIEWPORT = {"width": 1280, "height": 1500}   # 1600×3000 → 1280×1500

# ── Fichiers de sortie ────────────────────────────────────────
FILE_1X2     = "data/congobet_1x2_rounds.json"
FILE_GNG     = "data/cbet_odds.json"
FILE_RESULTS = "data/cbet_results.json"
FILE_STATUS  = "data/scraper_status.json"

# Nombre de clics "Afficher plus" (résultats)
MAX_SHOW_MORE_CLICKS = 5   # 8→5 : 5 clics = ~25 journées, suffisant

# Max journées à afficher dans le dashboard
MAX_DAYS_HISTORY = 7
