"""
scraper.py — CongoBet Virtual Instant League
Scraping 1X2, G/NG et Résultats via une seule instance Playwright.

Fix principal : le marché G/NG est RE-sélectionné après chaque changement de round,
car CongoBet repasse parfois sur 1X2 lors d'un clic d'onglet.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser, Page, TimeoutError as PWTimeout, async_playwright,
)

import config as C

# ── Logging ───────────────────────────────────────────────────
Path("data").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("congobet")

# ── Helpers ───────────────────────────────────────────────────
def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def _is_valid_time(s: str) -> bool:
    return bool(re.match(r"^\d{1,2}:\d{2}$", (s or "").strip()))

def _extract_hhmm(label: str) -> str:
    m = re.search(r"\b(\d{1,2}:\d{2})\b", label or "")
    return m.group(1).zfill(5) if m else ""

def _parse_score(text: str) -> tuple:
    m = re.search(r"(\d+)\s*[:\-]\s*(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

def _save(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def retry(max_attempts=3, delay=2.0):
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        log.warning(f"[retry {attempt}/{max_attempts}] {fn.__name__}: {exc}")
                        await asyncio.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# CongoBetScraper — instance unique de navigateur
# ═══════════════════════════════════════════════════════════════
class CongoBetScraper:
    def __init__(self):
        self._pw = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"],
        )
        self._page = await self._browser.new_page(locale="fr-FR", viewport=C.VIEWPORT)
        self._page.set_default_timeout(C.TIMEOUT_ELEMENT)
        return self

    async def __aexit__(self, *_):
        if self._browser: await self._browser.close()
        if self._pw: await self._pw.stop()

    @property
    def page(self) -> Page:
        return self._page

    @retry()
    async def goto(self, url: str) -> None:
        await self._page.goto(url, wait_until="networkidle", timeout=C.TIMEOUT_PAGE_LOAD)
        await self._page.wait_for_load_state("networkidle")
        await self._page.wait_for_timeout(2000)

    async def ensure_market(self, market: str) -> bool:
        """
        Sélectionne le marché voulu.
        Appelé APRÈS chaque click_round car CongoBet repasse sur 1X2.
        """
        page = self._page
        # Vérifier si déjà actif
        active = page.locator(C.SEL["market_active"])
        for i in range(await active.count()):
            if market.upper() in _clean(await active.nth(i).inner_text()).upper():
                return True
        # Bouton direct
        btns = page.locator(C.SEL["market_button"])
        for i in range(await btns.count()):
            try:
                if market.upper() in _clean(await btns.nth(i).inner_text()).upper():
                    await btns.nth(i).scroll_into_view_if_needed()
                    await btns.nth(i).click(timeout=C.TIMEOUT_SHORT)
                    await page.wait_for_timeout(800)
                    await page.wait_for_load_state("networkidle")
                    return True
            except Exception:
                continue
        # Dropdown
        try:
            sel_box = page.locator(C.SEL["market_select"]).first
            if await sel_box.count() > 0:
                await sel_box.click(timeout=C.TIMEOUT_SHORT)
                await page.wait_for_timeout(500)
                opt = page.locator(C.SEL["market_option"], has_text=market).first
                if await opt.count() > 0:
                    await opt.click(timeout=C.TIMEOUT_SHORT)
                    await page.wait_for_timeout(800)
                    await page.wait_for_load_state("networkidle")
                    return True
        except Exception as e:
            log.warning(f"Dropdown {market}: {e}")
        log.warning(f"Impossible de sélectionner {market}")
        return False

    async def get_round_times(self) -> list:
        tabs = self._page.locator(C.SEL["round_tabs"])
        count = await tabs.count()
        result = []
        for i in range(count):
            try:
                time_el = tabs.nth(i).locator(C.SEL["round_time"])
                if await time_el.count() > 0:
                    t = _clean(await time_el.inner_text())
                    if _is_valid_time(t):
                        result.append((i, t))
            except Exception:
                pass
        log.info(f"{len(result)} rounds valides / {count} total")
        return result

    @retry(max_attempts=2)
    async def click_round(self, idx: int) -> None:
        tabs = self._page.locator(C.SEL["round_tabs"])
        item = tabs.nth(idx)
        await item.scroll_into_view_if_needed()
        await item.click(force=True)
        await self._page.wait_for_selector(C.SEL["match_any"], state="attached", timeout=C.TIMEOUT_ELEMENT)
        await self._page.wait_for_timeout(400)

    async def extract_odds(self, n_cols: int = 3) -> list:
        """n_cols=3 → 1X2, n_cols=2 → G/NG"""
        page = self._page
        try:
            await page.wait_for_selector(C.SEL["match_any"], state="attached", timeout=C.TIMEOUT_ELEMENT)
        except PWTimeout:
            return []

        cards = page.locator(C.SEL["match_any"])
        count = await cards.count()
        matches = []

        for i in range(count):
            card = cards.nth(i)
            try:
                team_spans = card.locator(C.SEL["team_spans"])
                odd_spans  = card.locator(C.SEL["odds_spans"])
                teams, odds = [], []
                for j in range(await team_spans.count()):
                    t = _clean(await team_spans.nth(j).inner_text())
                    if t: teams.append(t)
                for j in range(await odd_spans.count()):
                    o = _clean(await odd_spans.nth(j).inner_text())
                    if o: odds.append(o)
                if len(teams) >= 2 and len(odds) >= n_cols:
                    entry = {"home": teams[0], "away": teams[-1]}
                    if n_cols == 3:
                        entry.update({"odds_1": odds[0], "odds_x": odds[1], "odds_2": odds[2]})
                    else:
                        entry.update({"odds_oui": odds[0], "odds_non": odds[1]})
                    matches.append(entry)
            except Exception as e:
                log.debug(f"card {i}: {e}")
        return matches


# ═══════════════════════════════════════════════════════════════
# Scrapers individuels
# ═══════════════════════════════════════════════════════════════
async def scrape_1x2(scraper: CongoBetScraper) -> dict:
    log.info("=== SCRAPE 1X2 ===")
    scraped_at = datetime.now(timezone.utc).isoformat()
    await scraper.goto(C.URL_MATCHES)
    await scraper.ensure_market(C.MARKET_1X2)
    round_list = await scraper.get_round_times()
    all_rounds = []
    for idx, rt in round_list:
        try:
            await scraper.click_round(idx)
            await scraper.ensure_market(C.MARKET_1X2)  # re-sélection post-clic
            matches = await scraper.extract_odds(n_cols=3)
            all_rounds.append({"round_index": idx, "round_time": rt, "matches": matches})
            log.info(f"  1X2 [{rt}]: {len(matches)} matchs")
        except Exception as e:
            log.error(f"  1X2 round {idx}: {e}")
    payload = {
        "source_url": C.URL_MATCHES,
        "title": "CongoBet Virtual Instant League 1X2",
        "scraped_at_utc": scraped_at,
        "round_count": len(all_rounds),
        "rounds": all_rounds,
    }
    _save(C.FILE_1X2, payload)
    log.info(f"1X2: {len(all_rounds)} rounds → {C.FILE_1X2}")
    return payload


async def scrape_gng(scraper: CongoBetScraper) -> dict:
    """
    Fix GNG : ensure_market("G/NG") est appelé APRÈS chaque click_round.
    Sans ce re-appel, les odds affichées sont celles de 1X2 (bug observé sur screenshots).
    """
    log.info("=== SCRAPE G/NG ===")
    scraped_at = datetime.now(timezone.utc).isoformat()
    if C.URL_MATCHES not in scraper.page.url:
        await scraper.goto(C.URL_MATCHES)
    ok = await scraper.ensure_market(C.MARKET_GNG)
    if not ok:
        return {"metadata": {"scraped_at_utc": scraped_at, "records_count": 0, "error": "market_not_selected"}, "matches": []}
    await scraper.page.wait_for_timeout(1000)
    round_list = await scraper.get_round_times()
    all_matches, seen = [], set()
    for idx, rt in round_list:
        try:
            await scraper.click_round(idx)
            # ⚠ CORRECTION CRITIQUE — re-sélectionner G/NG après chaque clic
            await scraper.ensure_market(C.MARKET_GNG)
            await scraper.page.wait_for_timeout(300)
            matches = await scraper.extract_odds(n_cols=2)
            for m in matches:
                key = f"{rt}|{m['home']}|{m['away']}"
                if key in seen: continue
                seen.add(key)
                all_matches.append({
                    "unique_key": key, "round_time": rt, "market": "G/NG",
                    "teams": {"home": m["home"], "away": m["away"]},
                    "odds": {"Oui": m["odds_oui"], "Non": m["odds_non"]},
                })
            log.info(f"  G/NG [{rt}]: {len(matches)} matchs")
        except Exception as e:
            log.error(f"  G/NG round {idx}: {e}")
    payload = {
        "source": {"site": "CongoBet", "url": C.URL_MATCHES, "market": "G/NG"},
        "metadata": {"scraped_at_utc": scraped_at, "records_count": len(all_matches)},
        "matches": all_matches,
    }
    _save(C.FILE_GNG, payload)
    log.info(f"G/NG: {len(all_matches)} cotes → {C.FILE_GNG}")
    return payload


async def scrape_results(scraper: CongoBetScraper) -> dict:
    log.info("=== SCRAPE RÉSULTATS ===")
    scraped_at = datetime.now(timezone.utc).isoformat()
    await scraper.goto(C.URL_RESULTS)
    # Afficher plus
    clicks = 0
    for _ in range(C.MAX_SHOW_MORE_CLICKS):
        try:
            btn = scraper.page.locator(C.SEL["show_more_btn"]).last
            if await btn.count() == 0 or not await btn.is_visible(timeout=3000):
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await scraper.page.wait_for_load_state("networkidle")
            await scraper.page.wait_for_timeout(800)
            clicks += 1
        except Exception:
            break
    log.info(f"  {clicks} clics 'Afficher plus'")
    matches, seen, round_labels = [], set(), []
    round_groups = scraper.page.locator(C.SEL["results_round"])
    group_count  = await round_groups.count()
    log.info(f"  {group_count} groupes résultats")
    for g_idx in range(group_count):
        group = round_groups.nth(g_idx)
        try:
            label_el = group.locator(C.SEL["result_label"]).first
            round_label = _clean(await label_el.inner_text()) if await label_el.count() > 0 else ""
            md_m = re.search(r"[Jj]ourn[eé]e\s*(\d+)", round_label)
            matchday  = int(md_m.group(1)) if md_m else None
            round_time = _extract_hhmm(round_label)
            if round_label and round_label not in round_labels:
                round_labels.append(round_label)
            cards = group.locator(".match, hg-event-result, [class*='event-row']")
            for c_idx in range(await cards.count()):
                card = cards.nth(c_idx)
                try:
                    card_text = _clean(await card.inner_text())
                    hs, as_ = _parse_score(card_text)
                    if hs is None: continue
                    team_els = card.locator(C.SEL["team_spans"])
                    teams = []
                    for t in range(await team_els.count()):
                        txt = _clean(await team_els.nth(t).inner_text())
                        if txt and not re.match(r"^[\d:\-]+$", txt): teams.append(txt)
                    if len(teams) < 2:
                        parts = re.split(r"\d+\s*[:\-]\s*\d+", card_text)
                        if len(parts) >= 2: teams = [_clean(parts[0]), _clean(parts[-1])]
                    if len(teams) < 2 or not teams[0] or not teams[-1]: continue
                    score = f"{hs}:{as_}"
                    ukey  = f"{matchday}|{teams[0]}|{teams[-1]}|{score}"
                    if ukey in seen: continue
                    seen.add(ukey)
                    ht_m   = re.search(r"\((\d+)[:\-](\d+)\)", card_text)
                    home_ht = int(ht_m.group(1)) if ht_m else None
                    away_ht = int(ht_m.group(2)) if ht_m else None
                    both   = hs > 0 and as_ > 0
                    matches.append({
                        "unique_key": ukey, "round_label": round_label,
                        "matchday": matchday, "round_time": round_time,
                        "home_team": teams[0], "away_team": teams[-1],
                        "score": score, "home_score": hs, "away_score": as_,
                        "halftime_score": f"{home_ht}:{away_ht}" if home_ht is not None else None,
                        "home_halftime_score": home_ht, "away_halftime_score": away_ht,
                        "both_teams_scored": both,
                        "gng_result": "Oui" if both else "Non",
                        "result_1x2": "1" if hs > as_ else ("X" if hs == as_ else "2"),
                    })
                except Exception as e:
                    log.debug(f"  card {c_idx}/{g_idx}: {e}")
        except Exception as e:
            log.warning(f"  groupe {g_idx}: {e}")
    matches.sort(key=lambda x: -(x.get("matchday") or 0))
    payload = {
        "metadata": {
            "scraped_at_utc": scraped_at,
            "show_more_clicks": clicks,
            "rounds_count": len(round_labels),
            "round_labels": round_labels[:32],
            "records_count": len(matches),
        },
        "matches": matches,
    }
    _save(C.FILE_RESULTS, payload)
    log.info(f"Résultats: {len(matches)} → {C.FILE_RESULTS}")
    return payload


# ═══════════════════════════════════════════════════════════════
# Runner principal
# ═══════════════════════════════════════════════════════════════
async def run_scraping_cycle(mode: str = "all") -> dict:
    t_start = datetime.now(timezone.utc)
    log.info(f"=== DÉBUT CYCLE mode={mode} ===")
    results, errors, durations = {}, [], {}

    async with CongoBetScraper() as scraper:
        if mode in ("all", "1x2"):
            t0 = datetime.now(timezone.utc)
            try: results["1x2"] = await scrape_1x2(scraper)
            except Exception as e: errors.append(f"1X2: {e}"); log.error(e)
            durations["1x2"] = round((datetime.now(timezone.utc)-t0).total_seconds(), 1)

        if mode in ("all", "gng"):
            t0 = datetime.now(timezone.utc)
            try: results["gng"] = await scrape_gng(scraper)
            except Exception as e: errors.append(f"GNG: {e}"); log.error(e)
            durations["gng"] = round((datetime.now(timezone.utc)-t0).total_seconds(), 1)

        if mode in ("all", "results"):
            t0 = datetime.now(timezone.utc)
            try: results["results"] = await scrape_results(scraper)
            except Exception as e: errors.append(f"Results: {e}"); log.error(e)
            durations["results"] = round((datetime.now(timezone.utc)-t0).total_seconds(), 1)

    total_s = round((datetime.now(timezone.utc)-t_start).total_seconds(), 1)
    status = {
        "last_run_utc": t_start.isoformat(),
        "mode": mode, "total_duration_s": total_s,
        "durations_s": durations, "success": list(results.keys()),
        "errors": errors,
        "counts": {
            "1x2_rounds":      results.get("1x2", {}).get("round_count", 0),
            "gng_matches":     results.get("gng", {}).get("metadata", {}).get("records_count", 0),
            "results_matches": results.get("results", {}).get("metadata", {}).get("records_count", 0),
        },
    }
    _save(C.FILE_STATUS, status)
    log.info(f"=== FIN {total_s}s erreurs={errors or 'aucune'} ===")
    return status


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    asyncio.run(run_scraping_cycle(mode))
