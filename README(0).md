# CongoBet Scraper — Auto-Scraping 1X2 & G/NG

Système de scraping automatique pour CongoBet Virtual Instant League.  
**GitHub Actions** scrape les données · **Streamlit** affiche le dashboard · **data/** stocke les JSON

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (toutes les 5 min)                          │
│  ┌──────────────┐   wait 2m30   ┌───────────────────────┐  │
│  │ Scrape cotes │──────────────▶│ Scrape résultats +    │  │
│  │ 1X2 + GNG    │               │ nouvelles cotes       │  │
│  └──────────────┘               └───────────────────────┘  │
│         │                                  │                │
│         └──────────────┬───────────────────┘                │
│                        ▼                                    │
│                 git commit & push                           │
│                  → data/*.json                              │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         │                                │
         ▼                                ▼
  ┌─────────────────┐           ┌──────────────────────┐
  │ Streamlit App   │           │ HTML Apps (1X2/GNG)  │
  │ Dashboard live  │           │ Chargent JSON via    │
  │ Status + DL     │           │ raw.githubusercontent │
  └─────────────────┘           └──────────────────────┘
```

## Fichiers produits

| Fichier | Description |
|---|---|
| `data/congobet_1x2_rounds.json` | Cotes 1X2 par round |
| `data/cbet_odds.json` | Cotes G/NG par round |
| `data/cbet_results.json` | Résultats + GNG + 1X2 dérivés |
| `data/scraper_status.json` | Statut du dernier scrape |

---

## Installation pas à pas

### Étape 1 — Créer le repo GitHub

1. Créez un nouveau repo GitHub : `congobet-scraper` (public ou privé)
2. Clonez-le localement : `git clone https://github.com/VOUS/congobet-scraper`
3. Copiez tous ces fichiers dans le repo
4. Créez le dossier `data/` avec un `.gitkeep` :
   ```bash
   mkdir -p data && touch data/.gitkeep
   ```
5. Push initial :
   ```bash
   git add . && git commit -m "Initial setup" && git push
   ```

### Étape 2 — Créer un token GitHub

1. Allez sur **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Cliquez **Generate new token**
3. Nom : `congobet-scraper-token`
4. Expiration : 90 jours (ou sans expiration)
5. Repository access : `congobet-scraper` seulement
6. Permissions :
   - **Contents** : Read and write
   - **Actions** : Read and write
   - **Workflows** : Read and write
7. **Copiez le token** (il ne sera affiché qu'une fois)

### Étape 3 — Déployer sur Streamlit Cloud

1. Allez sur **[share.streamlit.io](https://share.streamlit.io)**
2. **New app** → Connectez votre repo GitHub → choisissez `app.py`
3. Dans **Advanced settings → Secrets**, ajoutez :
   ```toml
   GITHUB_TOKEN  = "ghp_votre_token_ici"
   GITHUB_OWNER  = "votre_username"
   GITHUB_REPO   = "congobet-scraper"
   GITHUB_BRANCH = "main"
   ```
4. Cliquez **Deploy**

### Étape 4 — Activer GitHub Actions

1. Dans votre repo, allez dans **Settings → Actions → General**
2. Activez : **Allow all actions and reusable workflows**
3. Dans **Workflow permissions** : choisissez **Read and write permissions**
4. Le cron démarrera automatiquement au prochain cycle de 5 minutes

### Étape 5 — Intégrer dans les apps HTML

Dans `congobet_1x2_database.html` et `congobet_gng_database.html`, les JSON peuvent être chargés directement. Dans l'onglet **Importation**, au lieu de choisir un fichier local, vous pouvez fetch l'URL :

```
https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/congobet_1x2_rounds.json
https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/cbet_odds.json
https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/cbet_results.json
```

---

## Timing de scraping

| Événement | Timing |
|---|---|
| Cycle GitHub Actions | Toutes les **5 min** |
| Scrape cotes (cycle 1) | Immédiat au lancement |
| Attente interne | **2 min 30 sec** |
| Scrape résultats (cycle 2) | Après attente |
| Résultats disponibles sur site | **~30 sec** après fin affiche |
| Données disponibles sur GitHub | **~30 sec** après scrape |

> **Note** : Les matchs virtuels durent ~2 minutes et les résultats apparaissent ~30 secondes après la fin. Le cycle interne de 2m30 est calibré pour capturer les résultats de l'affiche précédente.

---

## Tests en local

```bash
# Installer les dépendances
pip install playwright streamlit requests
playwright install chromium

# Tester le scraper
python scraper.py all          # Tout scraper
python scraper.py 1x2          # Cotes 1X2 seulement
python scraper.py gng          # Cotes G/NG seulement
python scraper.py results      # Résultats seulement

# Lancer le dashboard
streamlit run app.py
```

---

## Déclenchement manuel

Via GitHub Actions :
1. Allez dans **Actions → CongoBet Auto Scraper**
2. Cliquez **Run workflow**
3. Choisissez le mode (all, 1x2, gng, results)
4. Cliquez **Run workflow**

Via Streamlit dashboard :
1. Ouvrez le dashboard Streamlit
2. Choisissez le mode dans le menu déroulant
3. Cliquez **▶ Lancer le scraping**

---

## Structure des fichiers JSON

### congobet_1x2_rounds.json
```json
{
  "source_url": "https://www.congobet.net/...",
  "scraped_at_utc": "2026-04-17T12:00:00+00:00",
  "round_count": 9,
  "rounds": [
    {
      "round_index": 1,
      "round_time": "11:34",
      "matches": [
        { "home": "London Reds", "away": "Manchester Blue",
          "odds_1": "2,21", "odds_x": "3,69", "odds_2": "2,98" }
      ]
    }
  ]
}
```

### cbet_results.json
```json
{
  "metadata": { "scraped_at_utc": "...", "records_count": 320 },
  "matches": [
    {
      "matchday": 32,
      "round_time": "07:47",
      "home_team": "Everton", "away_team": "C. Palace",
      "score": "2:1",
      "home_score": 2, "away_score": 1,
      "both_teams_scored": true,
      "gng_result": "Oui",
      "result_1x2": "1"
    }
  ]
}
```
