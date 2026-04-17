"""
CongoBet Scraper — Cotes 1X2 + Cotes GNG + Résultats
Extrait directement depuis https://www.congobet.net
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ── URLs ──────────────────────────────────────────────────────
URL_MATCHES = "https://www.congobet.net/virtual/category/instant-league/8035/matches"
URL_RESULTS = "https://www.congobet.net/virtual/category/instant-league/8035/results"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _valid_time(s: str) -> bool:
    """Vérifie si une chaîne est une heure valide HH:MM"""
    return bool(re.match(r"^\d{1,2}:\d{2}$", (s or "").strip()))


def _extract_time_from_label(label: str) -> str:
    """Extrait HH:MM depuis 'Aujourd'hui 07:47' ou 'Journée X - ... 07:47'"""
    m = re.search(r"(\d{1,2}:\d{2})(?::\d{2})?$", label)
    return m.group(1).zfill(5) if m else label.strip()


# ═══════════════════════════════════════════════════════════════
# SCRAPER 1 — Cotes 1X2
# ═══════════════════════════════════════════════════════════════
async def scrape_1x2_odds() -> dict[str, Any]:
    """Scrape les cotes 1X2 pour tous les rounds disponibles."""
    print("[1X2] Démarrage scraping cotes 1X2...")
    scraped_at = datetime.now(timezone.utc).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--single-process"]
        )
        page = await browser.new_page(
            locale="fr-FR",
            viewport={"width": 1600, "height": 3000}
        )
        page.set_default_timeout(20000)

        try:
            await page.goto(URL_MATCHES, wait_until="networkidle", timeout=120000)
            await page.wait_for_timeout(3000)

            # Attendre que les rounds soient chargés
            await page.wait_for_selector("hg-instant-league-round-picker li", timeout=20000)

            round_items = page.locator("hg-instant-league-round-picker li")
            round_count = await round_items.count()
            print(f"[1X2] {round_count} rounds détectés")

            all_rounds = []
            for idx in range(round_count):
                try:
                    item = round_items.nth(idx)
                    time_text = _clean(await item.locator(".time").inner_text())

                    # Ignorer les rounds "Live" et sans heure valide
                    if not _valid_time(time_text):
                        print(f"[1X2] Round {idx} ignoré (heure invalide: '{time_text}')")
                        continue

                    await item.scroll_into_view_if_needed()
                    await item.click(force=True)
                    await page.wait_for_timeout(1200)

                    match_locator = page.locator("div.match.bet-type-1x2")
                    count = await match_locator.count()
                    matches = []

                    for i in range(count):
                        card = match_locator.nth(i)
                        team_spans = card.locator(".teams span")
                        odd_spans  = card.locator("span.odds")

                        teams = []
                        for j in range(await team_spans.count()):
                            txt = _clean(await team_spans.nth(j).inner_text())
                            if txt:
                                teams.append(txt)

                        odds = []
                        for j in range(await odd_spans.count()):
                            txt = _clean(await odd_spans.nth(j).inner_text())
                            if txt:
                                odds.append(txt)

                        if len(teams) >= 2 and len(odds) >= 3:
                            matches.append({
                                "home":   teams[0],
                                "away":   teams[1],
                                "odds_1": odds[0],
                                "odds_x": odds[1],
                                "odds_2": odds[2],
                            })

                    all_rounds.append({
                        "round_index": idx,
                        "round_time": time_text,
                        "matches": matches,
                    })
                    print(f"[1X2] Round {idx} ({time_text}): {len(matches)} matchs")

                except Exception as e:
                    print(f"[1X2] WARN round {idx}: {e}")

        finally:
            await browser.close()

    payload = {
        "source_url": URL_MATCHES,
        "title": "CongoBet Virtual Instant League 1X2",
        "scraped_at_utc": scraped_at,
        "round_count": len(all_rounds),
        "rounds": all_rounds,
    }

    out = DATA_DIR / "congobet_1x2_rounds.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[1X2] ✓ {len(all_rounds)} rounds → {out}")
    return payload


# ═══════════════════════════════════════════════════════════════
# SCRAPER 2 — Cotes G/NG
# ═══════════════════════════════════════════════════════════════
async def _select_gng(page) -> None:
    active = page.locator("hg-event-bet-type-picker button.active", has_text="G/NG")
    if await active.count() > 0:
        return
    btn = page.locator("hg-event-bet-type-picker button", has_text="G/NG")
    if await btn.count() > 0:
        await btn.first.click()
        await page.wait_for_timeout(1200)
        return
    sel = page.locator("hg-event-bet-type-picker hg-select .selected").first
    await sel.click()
    await page.wait_for_timeout(500)
    opt = page.locator("hg-event-bet-type-picker hg-select .dropdown .option", has_text="G/NG").first
    await opt.click()
    await page.wait_for_timeout(1500)


async def scrape_gng_odds() -> dict[str, Any]:
    """Scrape les cotes G/NG pour tous les rounds disponibles."""
    print("[GNG] Démarrage scraping cotes G/NG...")
    scraped_at = datetime.now(timezone.utc).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--single-process"]
        )
        page = await browser.new_page(viewport={"width": 1600, "height": 2200})
        page.set_default_timeout(20000)

        try:
            await page.goto(URL_MATCHES, wait_until="networkidle", timeout=120000)
            await page.wait_for_timeout(3000)
            await page.wait_for_selector("div.match", timeout=20000)

            # Sélectionner le marché G/NG
            await _select_gng(page)
            await page.wait_for_selector("div.match", timeout=15000)

            # Récupérer les labels des colonnes (Oui / Non)
            labels = ["Oui", "Non"]
            try:
                header_spans = page.locator("div[class*='header'] span")
                for i in range(await header_spans.count()):
                    txt = _clean(await header_spans.nth(i).inner_text())
                    if txt and len(txt) < 20:
                        labels.append(txt)
                labels = [l for l in labels if l][:2] or ["Oui", "Non"]
            except Exception:
                pass

            round_tabs = page.locator("hg-instant-league-round-picker li")
            total_tabs = await round_tabs.count()
            print(f"[GNG] {total_tabs} rounds détectés")

            all_matches = []
            seen_keys: set[str] = set()

            for idx in range(1, total_tabs):  # Ignorer le premier tab (Live)
                try:
                    tabs = page.locator("hg-instant-league-round-picker li")
                    item = tabs.nth(idx)
                    time_el = item.locator(".time")
                    round_time = _clean(await time_el.inner_text()) if await time_el.count() > 0 else f"idx_{idx}"

                    if not _valid_time(round_time):
                        continue

                    await item.scroll_into_view_if_needed()
                    await item.click(force=True)
                    await page.wait_for_timeout(1000)

                    match_cards = page.locator("div.match")
                    for i in range(await match_cards.count()):
                        card = match_cards.nth(i)
                        team_spans = card.locator(".teams span")
                        odd_spans  = card.locator("span.odds")

                        teams, odds_vals = [], []
                        for j in range(await team_spans.count()):
                            t = _clean(await team_spans.nth(j).inner_text())
                            if t: teams.append(t)
                        for j in range(await odd_spans.count()):
                            o = _clean(await odd_spans.nth(j).inner_text())
                            if o: odds_vals.append(o)

                        if len(teams) >= 2 and len(odds_vals) >= 2:
                            key = f"{round_time}|{teams[0]}|{teams[1]}|GNG"
                            if key in seen_keys:
                                continue
                            seen_keys.add(key)
                            all_matches.append({
                                "unique_key": key,
                                "round_time": round_time,
                                "market": "G/NG",
                                "teams": {"home": teams[0], "away": teams[1]},
                                "odds": {labels[0]: odds_vals[0], labels[1]: odds_vals[1]},
                            })

                    print(f"[GNG] Round {idx} ({round_time}): OK")

                except Exception as e:
                    print(f"[GNG] WARN round {idx}: {e}")

        finally:
            await browser.close()

    payload = {
        "source": {"site": "CongoBet", "url": URL_MATCHES, "market": "G/NG"},
        "metadata": {
            "scraped_at_utc": scraped_at,
            "records_count": len(all_matches),
        },
        "matches": all_matches,
    }

    out = DATA_DIR / "cbet_odds.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[GNG] ✓ {len(all_matches)} cotes → {out}")
    return payload


# ═══════════════════════════════════════════════════════════════
# SCRAPER 3 — Résultats (GNG + 1X2 dérivés des scores)
# ═══════════════════════════════════════════════════════════════
async def _click_show_more(page, max_clicks: int = 8) -> int:
    """Clique sur 'Afficher plus' autant de fois que possible."""
    clicks = 0
    for _ in range(max_clicks):
        try:
            btn = page.locator("button", has_text=re.compile("Afficher|plus|more", re.I)).last
            if await btn.count() == 0 or not await btn.is_visible():
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(1500)
            clicks += 1
        except Exception:
            break
    return clicks


def _parse_score(score_text: str) -> tuple[int | None, int | None]:
    m = re.match(r"(\d+)[:\-](\d+)", (score_text or "").strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


async def scrape_results(show_more_clicks: int = 8) -> dict[str, Any]:
    """Scrape les résultats depuis la page résultats CongoBet."""
    print("[RESULTS] Démarrage scraping résultats...")
    scraped_at = datetime.now(timezone.utc).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--single-process"]
        )
        page = await browser.new_page(viewport={"width": 1600, "height": 3000})
        page.set_default_timeout(20000)

        matches = []
        seen_keys: set[str] = set()
        round_labels = []

        try:
            await page.goto(URL_RESULTS, wait_until="networkidle", timeout=120000)
            await page.wait_for_timeout(3000)

            # Cliquer sur "Afficher plus" pour charger plus de données
            clicks = await _click_show_more(page, show_more_clicks)
            print(f"[RESULTS] {clicks} clics 'Afficher plus'")

            # ── Extraire tous les rounds de résultats ──
            # La structure typique: groupes de matchs par journée
            # Sélecteurs possibles selon la structure CongoBet résultats
            round_groups = page.locator("hg-instant-league-results-round, .results-round, [class*='results-round'], .round-group")
            group_count = await round_groups.count()

            if group_count == 0:
                # Fallback: chercher les labels et les cartes de match directement
                print("[RESULTS] Tentative fallback extraction...")
                group_count = 1  # Traiter toute la page comme un seul groupe

            for g_idx in range(group_count):
                try:
                    # Extraire le label de la journée
                    round_label = ""
                    matchday_num = None

                    if group_count > 1:
                        group = round_groups.nth(g_idx)
                        label_el = group.locator("[class*='label'], [class*='title'], [class*='header']").first
                        if await label_el.count() > 0:
                            round_label = _clean(await label_el.inner_text())

                        m_day = re.search(r"[Jj]ourn[eé]e\s*(\d+)", round_label)
                        if m_day:
                            matchday_num = int(m_day.group(1))

                        round_time_val = _extract_time_from_label(round_label)

                        # Matchs dans ce groupe
                        cards = group.locator(".match, [class*='match'], hg-event-result")
                    else:
                        # Fallback: tous les résultats sur la page
                        cards = page.locator(
                            ".match-result, hg-event-result, [class*='result']:not([class*='halftime']), .event-item"
                        )
                        # Chercher les labels de round séparément
                        round_label_els = page.locator("[class*='round-label'], .journee, [class*='day-header']")

                    card_count = await cards.count()
                    print(f"[RESULTS] Groupe {g_idx}: {card_count} matchs")

                    for c_idx in range(card_count):
                        card = cards.nth(c_idx)
                        try:
                            # Texte complet de la carte
                            card_text = _clean(await card.inner_text())

                            # Chercher le score
                            score_m = re.search(r"(\d+)\s*[:\-]\s*(\d+)", card_text)
                            if not score_m:
                                continue

                            home_score = int(score_m.group(1))
                            away_score = int(score_m.group(2))
                            score = f"{home_score}:{away_score}"

                            # Chercher les noms d'équipes
                            team_els = card.locator(".teams span, [class*='team'] span, [class*='team-name']")
                            teams = []
                            for t_idx in range(await team_els.count()):
                                t = _clean(await team_els.nth(t_idx).inner_text())
                                if t and not re.match(r"^\d+$", t):
                                    teams.append(t)

                            if len(teams) < 2:
                                # Fallback: chercher avant/après le score dans le texte
                                parts = re.split(r"\d+\s*[:\-]\s*\d+", card_text)
                                if len(parts) >= 2:
                                    teams = [_clean(parts[0]), _clean(parts[-1])]

                            if len(teams) < 2:
                                continue

                            home_team = teams[0]
                            away_team = teams[-1]

                            # Chercher la demi-temps
                            ht_m = re.search(r"\((\d+)[:\-](\d+)\)", card_text)
                            home_ht = int(ht_m.group(1)) if ht_m else None
                            away_ht = int(ht_m.group(2)) if ht_m else None

                            # Chercher les minutes de but
                            goal_mins = re.findall(r"\b(\d{1,3})['′]\b", card_text)

                            # Dériver G/NG et 1X2
                            both_scored = home_score > 0 and away_score > 0
                            gng_result = "Oui" if both_scored else "Non"
                            result_1x2 = "1" if home_score > away_score else ("X" if home_score == away_score else "2")

                            # Numéro de journée depuis le label ou le texte
                            if matchday_num is None:
                                jn_m = re.search(r"[Jj]ourn[eé]e\s*(\d+)", card_text + round_label)
                                matchday_num = int(jn_m.group(1)) if jn_m else None

                            # Heure depuis le label
                            rt = _extract_time_from_label(round_label) if round_label else ""

                            ukey = f"{matchday_num or 'X'}|{home_team}|{away_team}|{score}"
                            if ukey in seen_keys:
                                continue
                            seen_keys.add(ukey)

                            rec = {
                                "unique_key": ukey,
                                "round_label": round_label,
                                "matchday": matchday_num,
                                "round_time": rt,
                                "home_team": home_team,
                                "away_team": away_team,
                                "score": score,
                                "home_score": home_score,
                                "away_score": away_score,
                                "halftime_score": f"{home_ht}:{away_ht}" if home_ht is not None else None,
                                "home_halftime_score": home_ht,
                                "away_halftime_score": away_ht,
                                "home_goal_minutes": [],
                                "away_goal_minutes": [],
                                "both_teams_scored": both_scored,
                                "gng_result": gng_result,
                                "result_1x2": result_1x2,
                            }
                            matches.append(rec)

                        except Exception as e:
                            pass  # Skip card silently

                except Exception as e:
                    print(f"[RESULTS] WARN groupe {g_idx}: {e}")

        except Exception as e:
            print(f"[RESULTS] ERREUR: {e}")
        finally:
            await browser.close()

    # Trier par journée décroissante
    matches.sort(key=lambda x: -(x.get("matchday") or 0))

    metadata = {
        "scraped_at_utc": scraped_at,
        "show_more_clicks": show_more_clicks,
        "rounds_count": len(set(m.get("matchday") for m in matches if m.get("matchday"))),
        "records_count": len(matches),
    }

    payload = {"metadata": metadata, "matches": matches}

    out = DATA_DIR / "cbet_results.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RESULTS] ✓ {len(matches)} résultats → {out}")
    return payload


# ═══════════════════════════════════════════════════════════════
# RUNNER PRINCIPAL — boucle de scraping continue
# ═══════════════════════════════════════════════════════════════
async def run_scraping_cycle(mode: str = "all") -> dict[str, Any]:
    """
    Exécute un cycle de scraping complet.
    mode: 'all' | '1x2' | 'gng' | 'results'
    """
    results = {}
    errors = []

    if mode in ("all", "1x2"):
        try:
            results["1x2"] = await scrape_1x2_odds()
        except Exception as e:
            errors.append(f"1X2: {e}")
            print(f"[ERROR] 1X2: {e}")

    if mode in ("all", "gng"):
        try:
            results["gng"] = await scrape_gng_odds()
        except Exception as e:
            errors.append(f"GNG: {e}")
            print(f"[ERROR] GNG: {e}")

    if mode in ("all", "results"):
        try:
            results["results"] = await scrape_results()
        except Exception as e:
            errors.append(f"Results: {e}")
            print(f"[ERROR] Results: {e}")

    # Sauvegarder un fichier de statut
    status = {
        "last_run_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "success": list(results.keys()),
        "errors": errors,
        "counts": {
            "1x2_rounds": results.get("1x2", {}).get("round_count", 0),
            "gng_matches": results.get("gng", {}).get("metadata", {}).get("records_count", 0),
            "results_matches": results.get("results", {}).get("metadata", {}).get("records_count", 0),
        }
    }

    status_file = DATA_DIR / "scraper_status.json"
    status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    return status


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    asyncio.run(run_scraping_cycle(mode))
