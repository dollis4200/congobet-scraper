"""
CongoBet Scraper Dashboard — Streamlit
Interface de monitoring et de déclenchement du scraping
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="CongoBet Scraper",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS personnalisé ──────────────────────────────────────────
st.markdown("""
<style>
:root { --home: #3ab8ff; --draw: #f0a500; --away: #e03e52; --accent: #00e5a0; }
.stApp { background: #080c10; color: #c8d8e8; }

.metric-card {
    background: #0d1219;
    border: 1px solid #1e2d3d;
    border-radius: 4px;
    padding: 16px;
    text-align: center;
    margin: 4px;
}
.metric-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #3a5570;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #3ab8ff;
}
.status-ok   { color: #00e5a0; font-weight: 700; }
.status-warn { color: #f0a500; font-weight: 700; }
.status-err  { color: #e03e52; font-weight: 700; }
.badge-1 { background: rgba(58,184,255,0.15); color:#3ab8ff; padding:2px 8px; border-radius:3px; }
.badge-x { background: rgba(240,165,0,0.15); color:#f0a500; padding:2px 8px; border-radius:3px; }
.badge-2 { background: rgba(224,62,82,0.15); color:#e03e52; padding:2px 8px; border-radius:3px; }
.badge-oui { background: rgba(0,229,160,0.15); color:#00e5a0; padding:2px 8px; border-radius:3px; }
.badge-non { background: rgba(224,62,82,0.15); color:#e03e52; padding:2px 8px; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ── Configuration GitHub ──────────────────────────────────────
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER  = os.environ.get("GITHUB_OWNER", "")   # votre username
GITHUB_REPO   = os.environ.get("GITHUB_REPO", "")    # nom du repo
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# URL de base pour les fichiers raw GitHub
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/data"

# Fichiers locaux (si l'app tourne localement)
DATA_DIR = Path("data")


def get_raw_url(filename: str) -> str:
    return f"{RAW_BASE}/{filename}"


@st.cache_data(ttl=30)  # Cache 30 secondes
def load_remote_json(filename: str) -> dict | None:
    """Charge un JSON depuis GitHub raw ou fichier local."""
    # Essayer local d'abord
    local = DATA_DIR / filename
    if local.exists():
        try:
            return json.loads(local.read_text("utf-8"))
        except Exception:
            pass
    # Essayer GitHub
    if GITHUB_OWNER and GITHUB_REPO:
        try:
            url = get_raw_url(filename)
            headers = {}
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return None


def trigger_github_action(mode: str = "all") -> bool:
    """Déclenche le workflow GitHub Actions via l'API."""
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/scrape.yml/dispatches"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {"ref": GITHUB_BRANCH, "inputs": {"mode": mode}}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.status_code == 204
    except Exception:
        return False


def get_workflow_runs() -> list[dict]:
    """Récupère les derniers runs du workflow."""
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return []
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?per_page=5"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("workflow_runs", [])
    except Exception:
        pass
    return []


def fmt_ago(iso_str: str) -> str:
    """Formate une durée depuis maintenant."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        secs = int(delta.total_seconds())
        if secs < 60:   return f"il y a {secs}s"
        if secs < 3600: return f"il y a {secs//60}min"
        return f"il y a {secs//3600}h{(secs%3600)//60:02d}min"
    except Exception:
        return iso_str


# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:#0d1219;border-bottom:1px solid #243344;padding:16px 24px;margin:-1rem -1rem 1rem;display:flex;align-items:center;gap:16px">
  <div style="width:32px;height:32px;background:linear-gradient(135deg,#3ab8ff,#e03e52);
       clip-path:polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)"></div>
  <div>
    <div style="font-size:20px;font-weight:700;color:#fff;letter-spacing:0.08em;text-transform:uppercase">
      CongoBet · Scraper Dashboard
    </div>
    <div style="font-size:11px;color:#3ab8ff;letter-spacing:0.15em;text-transform:uppercase">
      Virtual Instant League · 1X2 &amp; G/NG · Auto-Scraping
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# STATUT & CONTRÔLES
# ═══════════════════════════════════════════════════════════════
col_status, col_ctrl = st.columns([2, 1])

with col_status:
    status = load_remote_json("scraper_status.json")

    if status:
        last_run = status.get("last_run_utc", "—")
        ago = fmt_ago(last_run) if last_run != "—" else "—"
        success = status.get("success", [])
        errors  = status.get("errors", [])
        counts  = status.get("counts", {})

        status_color = "status-ok" if not errors else "status-warn"
        status_icon  = "✅" if not errors else "⚠️"

        st.markdown(f"""
        <div style="background:#0d1219;border:1px solid #1e2d3d;padding:14px 18px;border-radius:4px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <span style="font-size:18px">{status_icon}</span>
            <div>
              <div style="font-size:13px;color:#c8d8e8">
                Dernier scrape: <strong style="color:#00e5a0">{ago}</strong>
                <span style="color:#3a5570;font-size:11px;margin-left:8px">{last_run[:19].replace('T',' ')} UTC</span>
              </div>
              <div style="font-size:11px;color:#6a8aa8;margin-top:4px">
                Mode: <strong>{status.get('mode','—')}</strong> · 
                OK: {', '.join(success) or '—'} · 
                Erreurs: {', '.join(errors) or 'aucune'}
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Métriques
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Rounds 1X2</div><div class="metric-value">{counts.get("1x2_rounds",0)}</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Cotes G/NG</div><div class="metric-value">{counts.get("gng_matches",0)}</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Résultats</div><div class="metric-value">{counts.get("results_matches",0)}</div></div>', unsafe_allow_html=True)
    else:
        st.info("Aucun fichier de statut disponible. Le scraper n'a peut-être pas encore tourné.")

with col_ctrl:
    st.markdown("**⚡ Déclenchement manuel**")

    mode_sel = st.selectbox(
        "Mode",
        ["all", "1x2", "gng", "results"],
        format_func=lambda x: {"all":"Tout (1X2 + GNG + Résultats)", "1x2":"Cotes 1X2 seulement", "gng":"Cotes G/NG seulement", "results":"Résultats seulement"}[x]
    )

    if st.button("▶ Lancer le scraping", use_container_width=True, type="primary"):
        if not GITHUB_TOKEN:
            st.warning("⚠ Token GitHub non configuré (variable GITHUB_TOKEN)")
        else:
            with st.spinner("Déclenchement du workflow GitHub Actions..."):
                ok = trigger_github_action(mode_sel)
                if ok:
                    st.success("✅ Workflow déclenché ! Les données seront disponibles dans ~2 minutes.")
                else:
                    st.error("❌ Échec du déclenchement. Vérifiez GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO.")

    st.caption("Le cron GitHub tourne automatiquement toutes les 5 min.")

    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

st.divider()

# ═══════════════════════════════════════════════════════════════
# ONGLETS DONNÉES
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "⚽ Cotes 1X2",
    "🎯 Cotes G/NG",
    "📋 Résultats",
    "⚙️ Config & GitHub",
])

# ── TAB 1: Cotes 1X2 ─────────────────────────────────────────
with tab1:
    data_1x2 = load_remote_json("congobet_1x2_rounds.json")

    if data_1x2:
        meta_col, dl_col = st.columns([3, 1])
        with meta_col:
            scraped = data_1x2.get("scraped_at_utc", "—")
            st.markdown(f"**{data_1x2.get('round_count', 0)} rounds** · Scrape: `{scraped[:19].replace('T',' ')} UTC` · {fmt_ago(scraped)}")
        with dl_col:
            st.download_button(
                "⬇ congobet_1x2_rounds.json",
                data=json.dumps(data_1x2, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="congobet_1x2_rounds.json",
                mime="application/json",
                use_container_width=True,
            )

        for rnd in data_1x2.get("rounds", []):
            with st.expander(f"🕐 **{rnd['round_time']}** — {len(rnd['matches'])} matchs"):
                if rnd["matches"]:
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].markdown("**Rencontre**")
                    cols[1].markdown('<span class="badge-1">1</span>', unsafe_allow_html=True)
                    cols[2].markdown('<span class="badge-x">X</span>', unsafe_allow_html=True)
                    cols[3].markdown('<span class="badge-2">2</span>', unsafe_allow_html=True)
                    st.divider()
                    for m in rnd["matches"]:
                        c = st.columns([3, 1, 1, 1])
                        c[0].markdown(f"**{m['home']}** vs **{m['away']}**")
                        c[1].markdown(f"<span class='badge-1'>{m['odds_1']}</span>", unsafe_allow_html=True)
                        c[2].markdown(f"<span class='badge-x'>{m['odds_x']}</span>", unsafe_allow_html=True)
                        c[3].markdown(f"<span class='badge-2'>{m['odds_2']}</span>", unsafe_allow_html=True)
                else:
                    st.caption("Aucun match dans ce round")
    else:
        st.info("Données 1X2 non disponibles. Lancez un scraping ou attendez le prochain cycle automatique.")

# ── TAB 2: Cotes G/NG ────────────────────────────────────────
with tab2:
    data_gng = load_remote_json("cbet_odds.json")

    if data_gng:
        matches_gng = data_gng.get("matches", [])
        meta = data_gng.get("metadata", {})
        scraped = meta.get("scraped_at_utc", "—")

        mcol, dcol = st.columns([3, 1])
        with mcol:
            st.markdown(f"**{meta.get('records_count', 0)} cotes G/NG** · Scrape: `{scraped[:19].replace('T',' ')} UTC` · {fmt_ago(scraped)}")
        with dcol:
            st.download_button(
                "⬇ cbet_odds.json",
                data=json.dumps(data_gng, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="cbet_odds.json",
                mime="application/json",
                use_container_width=True,
            )

        # Grouper par round_time
        from collections import defaultdict
        by_time = defaultdict(list)
        for m in matches_gng:
            by_time[m.get("round_time", "—")].append(m)

        for rt, ms in sorted(by_time.items()):
            with st.expander(f"🕐 **{rt}** — {len(ms)} matchs"):
                for m in ms:
                    odds = m.get("odds", {})
                    teams = m.get("teams", {})
                    o_keys = list(odds.keys())
                    oui_v = odds.get(o_keys[0], "—") if o_keys else "—"
                    non_v = odds.get(o_keys[1], "—") if len(o_keys) > 1 else "—"
                    c = st.columns([3, 1, 1])
                    c[0].markdown(f"**{teams.get('home','?')}** vs **{teams.get('away','?')}**")
                    c[1].markdown(f"<span class='badge-oui'>OUI {oui_v}</span>", unsafe_allow_html=True)
                    c[2].markdown(f"<span class='badge-non'>NON {non_v}</span>", unsafe_allow_html=True)
    else:
        st.info("Données G/NG non disponibles.")

# ── TAB 3: Résultats ─────────────────────────────────────────
with tab3:
    data_res = load_remote_json("cbet_results.json")

    if data_res:
        matches_res = data_res.get("matches", [])
        meta_r = data_res.get("metadata", {})
        scraped_r = meta_r.get("scraped_at_utc", "—")

        rc, dc = st.columns([3, 1])
        with rc:
            st.markdown(f"**{meta_r.get('records_count', 0)} résultats** · {meta_r.get('rounds_count', 0)} journées · Scrape: `{scraped_r[:19].replace('T',' ')} UTC` · {fmt_ago(scraped_r)}")
        with dc:
            st.download_button(
                "⬇ cbet_results.json",
                data=json.dumps(data_res, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="cbet_results.json",
                mime="application/json",
                use_container_width=True,
            )

        # Grouper par journée
        from collections import defaultdict
        by_day = defaultdict(list)
        for m in matches_res:
            by_day[m.get("matchday", "—")].append(m)

        for day in sorted(by_day.keys(), reverse=True)[:10]:  # 10 dernières journées
            ms_day = by_day[day]
            rt = ms_day[0].get("round_time", "—") if ms_day else "—"
            with st.expander(f"📅 **Journée {day}** — {rt} — {len(ms_day)} matchs"):
                for m in ms_day:
                    hs = m.get("home_score", "?")
                    as_ = m.get("away_score", "?")
                    gng = m.get("gng_result", "?")
                    r1x2 = m.get("result_1x2", "?")
                    score = m.get("score", f"{hs}:{as_}")

                    badge_gng = f"<span class='badge-oui'>OUI</span>" if gng == "Oui" else f"<span class='badge-non'>NON</span>"
                    r_color = {"1": "badge-1", "X": "badge-x", "2": "badge-2"}.get(r1x2, "")
                    badge_1x2 = f"<span class='{r_color}'>{r1x2}</span>" if r_color else r1x2

                    c = st.columns([3, 1, 1, 1])
                    c[0].markdown(f"**{m.get('home_team','?')}** vs **{m.get('away_team','?')}**")
                    c[1].markdown(f"**{score}**")
                    c[2].markdown(badge_gng, unsafe_allow_html=True)
                    c[3].markdown(badge_1x2, unsafe_allow_html=True)
    else:
        st.info("Résultats non disponibles.")

# ── TAB 4: Config ─────────────────────────────────────────────
with tab4:
    st.markdown("### ⚙️ Configuration")

    st.markdown("""
    #### 1. Variables d'environnement requises

    Configurez ces variables dans **Streamlit Cloud** (Settings → Secrets) :

    ```toml
    # .streamlit/secrets.toml (NE PAS COMMITTER ce fichier)
    GITHUB_TOKEN  = "ghp_votre_token_personnel"
    GITHUB_OWNER  = "votre_username_github"
    GITHUB_REPO   = "congobet-scraper"
    GITHUB_BRANCH = "main"
    ```

    #### 2. Permissions du token GitHub
    Le token doit avoir les permissions :
    - `repo` (lecture/écriture) pour pousser les données
    - `workflow` pour déclencher les Actions

    #### 3. Architecture
    """)

    st.code("""
    congobet-scraper/                    ← Votre repo GitHub
    ├── scraper.py                       ← Logique de scraping Playwright
    ├── app.py                           ← Ce dashboard Streamlit
    ├── requirements.txt                 ← Dépendances Python
    ├── packages.txt                     ← Dépendances système (Streamlit Cloud)
    ├── .streamlit/
    │   └── secrets.toml                 ← Variables privées (non committé)
    ├── .github/
    │   └── workflows/
    │       └── scrape.yml               ← Auto-scraping toutes les 5 min
    └── data/                            ← JSONs scrappés (auto-committés)
        ├── congobet_1x2_rounds.json     ← Cotes 1X2 actuelles
        ├── cbet_odds.json               ← Cotes G/NG actuelles
        ├── cbet_results.json            ← Résultats récents
        └── scraper_status.json          ← Statut du dernier scrape
    """, language="")

    st.markdown("""
    #### 4. URLs des données (à charger dans vos applis HTML)

    Une fois le repo public, vos applications HTML peuvent charger les données directement :
    """)

    if GITHUB_OWNER and GITHUB_REPO:
        for fname in ["congobet_1x2_rounds.json", "cbet_odds.json", "cbet_results.json"]:
            url = get_raw_url(fname)
            st.code(url)
    else:
        st.code("https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/congobet_1x2_rounds.json")
        st.code("https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/cbet_odds.json")
        st.code("https://raw.githubusercontent.com/VOTRE_USERNAME/VOTRE_REPO/main/data/cbet_results.json")

    st.markdown("""
    #### 5. Fréquence des cycles

    | Événement | Timing |
    |---|---|
    | GitHub Actions cron | Toutes les **5 min** (minimum) |
    | Cycle interne 1 | Scrape cotes → immédiat |
    | Attente interne | **2 min 30 sec** |
    | Cycle interne 2 | Scrape résultats + nouvelles cotes |
    | Résultats disponibles | **~30 sec** après fin de l'affiche |
    """)

    st.divider()
    st.markdown("#### Statut des variables d'environnement")
    env_status = {
        "GITHUB_TOKEN":  "✅ Configuré" if GITHUB_TOKEN else "❌ Non configuré",
        "GITHUB_OWNER":  f"✅ `{GITHUB_OWNER}`" if GITHUB_OWNER else "❌ Non configuré",
        "GITHUB_REPO":   f"✅ `{GITHUB_REPO}`" if GITHUB_REPO else "❌ Non configuré",
        "GITHUB_BRANCH": f"✅ `{GITHUB_BRANCH}`",
    }
    for k, v in env_status.items():
        st.markdown(f"- **{k}**: {v}")

    # Derniers runs GitHub Actions
    st.divider()
    st.markdown("#### Derniers runs GitHub Actions")
    if GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO:
        runs = get_workflow_runs()
        if runs:
            for run in runs[:5]:
                status_icon = {"success": "✅", "failure": "❌", "in_progress": "🔄", "queued": "⏳"}.get(run.get("status",""), "❓")
                conclusion = run.get("conclusion", run.get("status", "—"))
                created = fmt_ago(run.get("created_at", ""))
                st.markdown(f"{status_icon} **{run.get('name','Run')}** · {conclusion} · {created}")
        else:
            st.caption("Aucun run trouvé")
    else:
        st.caption("Variables GitHub non configurées")

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:2rem;padding:12px;border-top:1px solid #1e2d3d;font-size:10px;color:#3a5570;text-align:center">
  CongoBet Scraper · Virtual Instant League · Auto-refresh GitHub Actions · Données brutes disponibles via raw GitHub URL
</div>
""", unsafe_allow_html=True)
