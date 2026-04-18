"""
config.py — Tous les sélecteurs et constantes centralisés.
Modifier ici si CongoBet change sa structure HTML.
"""

# ── URLs ──────────────────────────────────────────────────────
URL_MATCHES = "https://www.congobet.net/virtual/category/instant-league/8035/matches"
URL_RESULTS = "https://www.congobet.net/virtual/category/instant-league/8035/results"

# ── Timeouts (ms) ─────────────────────────────────────────────
TIMEOUT_PAGE_LOAD   = 120_000   # chargement initial
TIMEOUT_ELEMENT     = 30_000    # attente d'un élément
TIMEOUT_SHORT       = 10_000    # action rapide
TIMEOUT_ROUND_CLICK = 1_500     # après clic sur un round

# ── Retries ───────────────────────────────────────────────────
MAX_RETRIES   = 3
RETRY_DELAY_S = 2.0

# ── Sélecteurs CongoBet ───────────────────────────────────────
SEL = {
    # Rounds / tabs
    "round_tabs"   : "hg-instant-league-round-picker li",
    "round_time"   : ".time",

    # Marchés (boutons en haut)
    "market_active": "hg-event-bet-type-picker button.active",
    "market_button": "hg-event-bet-type-picker button",
    "market_select": "hg-event-bet-type-picker hg-select .selected",
    "market_option": "hg-event-bet-type-picker hg-select .dropdown .option",

    # Matchs (cotes)
    "match_any"    : "div.match",
    "match_1x2"    : "div.match.bet-type-1x2",
    "match_gng"    : "div.match.bet-type-gng, div.match",  # fallback
    "team_spans"   : ".teams span",
    "odds_spans"   : "span.odds",

    # Résultats (structure réelle du site)
    "results_container": "hg-instant-league-results .result-container",
    "results_header"   : ".header",
    "results_row"      : ".match-results .row",
    "team_span"        : ".team span",
    "match_score"      : ".match-score",
    "halftime_score"   : ".halfTime-score",
    "home_goals_min"   : ".haltTime-goals.home span",
    "away_goals_min"   : ".haltTime-goals.away span",
    "show_more_btn"    : "text=/Afficher plus/i",

    # Anciens sélecteurs (gardés pour compatibilité, mais non utilisés dans la nouvelle version)
    "result_label"  : ".round-label, .header-label, [class*='round-label']",
    "result_home"   : ".home-team, [class*='home']",
    "result_away"   : ".away-team, [class*='away']",
    "result_score"  : ".score, [class*='score']",
}

# Marché labels
MARKET_GNG = "G/NG"
MARKET_1X2 = "1X2"

# Viewport
VIEWPORT = {"width": 1600, "height": 3000}

# ── Fichiers de sortie ────────────────────────────────────────
FILE_1X2     = "data/congobet_1x2_rounds.json"
FILE_GNG     = "data/cbet_odds.json"
FILE_RESULTS = "data/cbet_results.json"
FILE_STATUS  = "data/scraper_status.json"

# ── Résultats : max journées à conserver ──────────────────────
MAX_SHOW_MORE_CLICKS = 8
MAX_DAYS_HISTORY     = 7   # nb max de journées affichées dans les dashboards