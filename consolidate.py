"""
consolidate.py — Fusion et mise à jour de la base consolidée des matchs.
Met à jour les cotes 1X2, G/NG et les résultats pour chaque rencontre.
À exécuter régulièrement (après chaque scraping).
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DATA_DIR = Path("data")
CONSOLIDATED_FILE = DATA_DIR / "consolidated_matches.json"

def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(data: Dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_match_key(round_time: str, home: str, away: str) -> str:
    """Clé unique pour un match : round_time|home|away"""
    return f"{round_time}|{home}|{away}"

def consolidate():
    print("=== Consolidation et mise à jour de la base ===")
    
    # Charger la base existante
    existing_data = load_json(CONSOLIDATED_FILE)
    existing_matches: Dict[str, Dict] = {}
    if existing_data:
        for m in existing_data.get("matches", []):
            key = get_match_key(m["round_time"], m["home_team"], m["away_team"])
            existing_matches[key] = m
        print(f"Base existante : {len(existing_matches)} matchs")
    else:
        print("Aucune base existante, création d'une nouvelle")
    
    # Charger les nouvelles sources
    results_data = load_json(DATA_DIR / "cbet_results.json")
    gng_data = load_json(DATA_DIR / "cbet_odds.json")
    odds_1x2_data = load_json(DATA_DIR / "congobet_1x2_rounds.json")
    
    # 1. Traiter les cotes 1X2
    if odds_1x2_data:
        for rnd in odds_1x2_data.get("rounds", []):
            rt = rnd["round_time"]
            for m in rnd.get("matches", []):
                home = m["home"]
                away = m["away"]
                key = get_match_key(rt, home, away)
                # Créer ou mettre à jour l'entrée
                if key not in existing_matches:
                    existing_matches[key] = {
                        "matchday": None,
                        "round_time": rt,
                        "home_team": home,
                        "away_team": away,
                        "score": None,
                        "home_score": None,
                        "away_score": None,
                        "gng_result": None,
                        "both_teams_scored": None,
                        "result_1x2": None,
                        "odds_1": None,
                        "odds_x": None,
                        "odds_2": None,
                        "odds_gng_oui": None,
                        "odds_gng_non": None,
                    }
                # Mettre à jour les cotes 1X2 (toujours les plus récentes)
                existing_matches[key]["odds_1"] = m.get("odds_1")
                existing_matches[key]["odds_x"] = m.get("odds_x")
                existing_matches[key]["odds_2"] = m.get("odds_2")
        print(f"Cotes 1X2 intégrées")
    
    # 2. Traiter les cotes G/NG
    if gng_data:
        for g in gng_data.get("matches", []):
            rt = g["round_time"]
            home = g["teams"]["home"]
            away = g["teams"]["away"]
            key = get_match_key(rt, home, away)
            if key not in existing_matches:
                existing_matches[key] = {
                    "matchday": None,
                    "round_time": rt,
                    "home_team": home,
                    "away_team": away,
                    "score": None,
                    "home_score": None,
                    "away_score": None,
                    "gng_result": None,
                    "both_teams_scored": None,
                    "result_1x2": None,
                    "odds_1": None,
                    "odds_x": None,
                    "odds_2": None,
                    "odds_gng_oui": None,
                    "odds_gng_non": None,
                }
            existing_matches[key]["odds_gng_oui"] = g.get("odds", {}).get("Oui")
            existing_matches[key]["odds_gng_non"] = g.get("odds", {}).get("Non")
        print(f"Cotes G/NG intégrées")
    
    # 3. Traiter les résultats (mise à jour des matchs ayant un résultat)
    results_updated = 0
    if results_data:
        for res in results_data.get("matches", []):
            rt = res.get("round_time", "")
            home = res["home_team"]
            away = res["away_team"]
            key = get_match_key(rt, home, away)
            if key not in existing_matches:
                # Créer une entrée avec les infos de base
                existing_matches[key] = {
                    "matchday": res.get("matchday"),
                    "round_time": rt,
                    "home_team": home,
                    "away_team": away,
                    "score": None,
                    "home_score": None,
                    "away_score": None,
                    "gng_result": None,
                    "both_teams_scored": None,
                    "result_1x2": None,
                    "odds_1": None,
                    "odds_x": None,
                    "odds_2": None,
                    "odds_gng_oui": None,
                    "odds_gng_non": None,
                }
            # Mettre à jour les champs de résultat (ne pas écraser les cotes existantes)
            existing_matches[key]["matchday"] = res.get("matchday") or existing_matches[key]["matchday"]
            existing_matches[key]["score"] = res["score"]
            existing_matches[key]["home_score"] = res["home_score"]
            existing_matches[key]["away_score"] = res["away_score"]
            existing_matches[key]["gng_result"] = res["gng_result"]
            existing_matches[key]["both_teams_scored"] = res["both_teams_scored"]
            existing_matches[key]["result_1x2"] = res["result_1x2"]
            results_updated += 1
        print(f"Résultats mis à jour pour {results_updated} matchs")
    
    # 4. Reconstruire la liste finale (trier par matchday décroissant si possible)
    matches_list = list(existing_matches.values())
    # Trier : d'abord ceux avec matchday, puis par round_time
    matches_list.sort(key=lambda x: (x.get("matchday") is None, x.get("matchday", 0)), reverse=True)
    
    # 5. Sauvegarder
    output = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_matches": len(matches_list),
            "source_files": {
                "results": "cbet_results.json",
                "gng": "cbet_odds.json",
                "1x2": "congobet_1x2_rounds.json"
            }
        },
        "matches": matches_list,
    }
    save_json(output, CONSOLIDATED_FILE)
    print(f"✅ Base consolidée sauvegardée : {len(matches_list)} matchs")

if __name__ == "__main__":
    consolidate()
