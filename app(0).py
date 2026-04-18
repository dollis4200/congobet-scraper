"""
app.py — CongoBet Scraper Dashboard
Auto-refresh JS, déclenchement GitHub Actions, visualisation live.
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ── Config ────────────────────────────────────────────────────
st.set_page_config(page_title="CongoBet Scraper", page_icon="⚽", layout="wide")

# Charger les secrets Streamlit → env vars
GITHUB_TOKEN  = st.secrets.get("GITHUB_TOKEN",  os.environ.get("GITHUB_TOKEN", ""))
GITHUB_OWNER  = st.secrets.get("GITHUB_OWNER",  os.environ.get("GITHUB_OWNER", ""))
GITHUB_REPO   = st.secrets.get("GITHUB_REPO",   os.environ.get("GITHUB_REPO", ""))
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", os.environ.get("GITHUB_BRANCH", "main"))

RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/data"
DATA_DIR = Path("data")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""<style>
.stApp { background:#080c10; color:#c8d8e8; }
.block-container { padding-top:1rem; }
div[data-testid="metric-container"] { background:#0d1219; border:1px solid #1e2d3d; border-radius:4px; padding:12px; }
.badge-1   { background:rgba(58,184,255,.18); color:#3ab8ff;  padding:2px 9px; border-radius:3px; font-weight:700; font-size:12px; }
.badge-x   { background:rgba(240,165,0,.18);  color:#f0a500;  padding:2px 9px; border-radius:3px; font-weight:700; font-size:12px; }
.badge-2   { background:rgba(224,62,82,.18);  color:#e03e52;  padding:2px 9px; border-radius:3px; font-weight:700; font-size:12px; }
.badge-oui { background:rgba(0,229,160,.18);  color:#00e5a0;  padding:2px 9px; border-radius:3px; font-weight:700; font-size:12px; }
.badge-non { background:rgba(224,62,82,.18);  color:#e03e52;  padding:2px 9px; border-radius:3px; font-weight:700; font-size:12px; }
.status-bar { padding:10px 16px; border-radius:4px; margin-bottom:12px; font-size:13px; }
</style>""", unsafe_allow_html=True)

# ── Auto-refresh ──────────────────────────────────────────────
# Rafraîchissement automatique toutes les 30 secondes
count = st_autorefresh(interval=30_000, limit=None, key="auto_refresh")

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0d1219;border-bottom:1px solid #243344;padding:14px 20px;margin:-1rem -1rem 1rem;display:flex;align-items:center;gap:14px">
  <div style="width:30px;height:30px;background:linear-gradient(135deg,#3ab8ff,#e03e52);clip-path:polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)"></div>
  <div>
    <div style="font-size:18px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.08em">CongoBet · Scraper Dashboard</div>
    <div style="font-size:11px;color:#3ab8ff;letter-spacing:.15em;text-transform:uppercase">Virtual Instant League · Auto-refresh 30s</div>
  </div>
</div>""", unsafe_allow_html=True)


# ── Data loaders ─────────────────────────────────────────────
@st.cache_data(ttl=25)
def load_json(filename: str) -> dict | None:
    local = DATA_DIR / filename
    if local.exists():
        try:
            return json.loads(local.read_text("utf-8"))
        except Exception:
            pass
    if GITHUB_OWNER and GITHUB_REPO:
        try:
            url = f"{RAW_BASE}/{filename}"
            headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def fmt_ago(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:   return f"{secs}s"
        if secs < 3600: return f"{secs//60}min {secs%60}s"
        return f"{secs//3600}h{(secs%3600)//60:02d}min"
    except Exception:
        return "?"


def trigger_workflow(mode: str) -> bool:
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/scrape.yml/dispatches"
        r = requests.post(url,
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"ref": GITHUB_BRANCH, "inputs": {"mode": mode}},
            timeout=10)
        return r.status_code == 204
    except Exception:
        return False


def get_workflow_runs() -> list:
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return []
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?per_page=5",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
        return r.json().get("workflow_runs", []) if r.status_code == 200 else []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# STATUT & CONTRÔLES
# ═══════════════════════════════════════════════════════════════
status = load_json("scraper_status.json")
col_s, col_c = st.columns([2.5, 1])

with col_s:
    if status:
        last_run = status.get("last_run_utc", "—")
        ago  = fmt_ago(last_run)
        errs = status.get("errors", [])
        ok   = not errs
        col = "#00e5a0" if ok else "#f0a500"
        icon = "✅" if ok else "⚠️"
        c = status.get("counts", {})
        dur = status.get("total_duration_s", "—")
        st.markdown(f"""
        <div class="status-bar" style="background:#0d1219;border:1px solid {'#243344' if ok else '#f0a50040'}">
          <span style="font-size:16px">{icon}</span>
          <strong style="color:{col}"> il y a {ago}</strong>
          <span style="color:#6a8aa8;font-size:11px;margin-left:8px">{last_run[:19].replace('T',' ')} UTC · {dur}s</span>
          {'<br><span style="color:#f0a500;font-size:11px">Erreurs: ' + ', '.join(errs) + '</span>' if errs else ''}
        </div>""", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("🔵 Rounds 1X2",    c.get("1x2_rounds",0))
        m2.metric("🟢 Cotes G/NG",    c.get("gng_matches",0))
        m3.metric("📋 Résultats",      c.get("results_matches",0))
    else:
        st.info("Aucun statut disponible. En attente du premier scraping...")

with col_c:
    st.markdown("**⚡ Déclenchement manuel**")
    mode_sel = st.selectbox("Mode", ["all","1x2","gng","results"],
        format_func=lambda x: {"all":"Tout","1x2":"Cotes 1X2","gng":"Cotes G/NG","results":"Résultats"}[x])
    if st.button("▶ Lancer", use_container_width=True, type="primary"):
        if not GITHUB_TOKEN:
            st.warning("⚠ GITHUB_TOKEN non configuré")
        else:
            with st.spinner("Déclenchement..."):
                if trigger_workflow(mode_sel):
                    st.success("✅ Workflow déclenché (~2 min)")
                else:
                    st.error("❌ Échec — vérifiez les secrets")
    if st.button("🔄 Vider le cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Auto-refresh: 30s · Run #{count}")

st.divider()

# ═══════════════════════════════════════════════════════════════
# ONGLETS
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["⚽ Cotes 1X2", "🎯 Cotes G/NG", "📋 Résultats", "⚙️ Config"])

# ── 1X2 ──────────────────────────────────────────────────────
with tab1:
    d = load_json("congobet_1x2_rounds.json")
    if d:
        sc = d.get("scraped_at_utc","—")
        c1, c2 = st.columns([3,1])
        c1.markdown(f"**{d.get('round_count',0)} rounds** · {sc[:19].replace('T',' ')} UTC · il y a {fmt_ago(sc)}")
        c2.download_button("⬇ JSON", json.dumps(d, ensure_ascii=False, indent=2).encode(),
            file_name=f"1x2_{sc[:10]}.json", mime="application/json", use_container_width=True)
        for rnd in d.get("rounds", []):
            with st.expander(f"🕐 **{rnd['round_time']}** — {len(rnd['matches'])} matchs"):
                for m in rnd["matches"]:
                    c = st.columns([3,1,1,1])
                    c[0].markdown(f"**{m['home']}** vs **{m['away']}**")
                    c[1].markdown(f"<span class='badge-1'>{m['odds_1']}</span>", unsafe_allow_html=True)
                    c[2].markdown(f"<span class='badge-x'>{m['odds_x']}</span>", unsafe_allow_html=True)
                    c[3].markdown(f"<span class='badge-2'>{m['odds_2']}</span>", unsafe_allow_html=True)
    else:
        st.info("Données 1X2 non disponibles.")

# ── G/NG ─────────────────────────────────────────────────────
with tab2:
    d = load_json("cbet_odds.json")
    if d:
        ms  = d.get("matches", [])
        meta= d.get("metadata", {})
        sc  = meta.get("scraped_at_utc","—")
        c1, c2 = st.columns([3,1])
        c1.markdown(f"**{meta.get('records_count',0)} cotes G/NG** · {sc[:19].replace('T',' ')} UTC · il y a {fmt_ago(sc)}")
        c2.download_button("⬇ JSON", json.dumps(d, ensure_ascii=False, indent=2).encode(),
            file_name=f"gng_{sc[:10]}.json", mime="application/json", use_container_width=True)
        by_time = defaultdict(list)
        for m in ms: by_time[m.get("round_time","—")].append(m)
        for rt, mlist in sorted(by_time.items()):
            with st.expander(f"🕐 **{rt}** — {len(mlist)} matchs"):
                for m in mlist:
                    odds = m.get("odds", {})
                    teams= m.get("teams", {})
                    oui_v = odds.get("Oui","—")
                    non_v = odds.get("Non","—")
                    c = st.columns([3,1,1])
                    c[0].markdown(f"**{teams.get('home','?')}** vs **{teams.get('away','?')}**")
                    c[1].markdown(f"<span class='badge-oui'>OUI {oui_v}</span>", unsafe_allow_html=True)
                    c[2].markdown(f"<span class='badge-non'>NON {non_v}</span>", unsafe_allow_html=True)
    else:
        st.info("Données G/NG non disponibles.")

# ── Résultats ────────────────────────────────────────────────
with tab3:
    d = load_json("cbet_results.json")
    if d:
        ms   = d.get("matches", [])
        meta = d.get("metadata", {})
        sc   = meta.get("scraped_at_utc","—")
        c1, c2 = st.columns([3,1])
        c1.markdown(f"**{meta.get('records_count',0)} résultats** · {sc[:19].replace('T',' ')} UTC · il y a {fmt_ago(sc)}")
        c2.download_button("⬇ JSON", json.dumps(d, ensure_ascii=False, indent=2).encode(),
            file_name=f"results_{sc[:10]}.json", mime="application/json", use_container_width=True)
        by_day = defaultdict(list)
        for m in ms: by_day[m.get("matchday","—")].append(m)
        days = sorted([d for d in by_day if isinstance(d, int)], reverse=True)
        day_sel = st.selectbox("Filtrer par journée", ["Toutes"] + [f"Journée {d}" for d in days])
        show_days = days if day_sel == "Toutes" else [int(day_sel.split()[-1])]
        for day in show_days[:15]:
            mday = by_day[day]
            rt   = mday[0].get("round_time","—") if mday else "—"
            with st.expander(f"📅 **Journée {day}** — {rt} — {len(mday)} matchs"):
                for m in mday:
                    hs, as_ = m.get("home_score","?"), m.get("away_score","?")
                    gng = m.get("gng_result","?")
                    r1x2= m.get("result_1x2","?")
                    b_gng = "<span class='badge-oui'>OUI</span>" if gng=="Oui" else "<span class='badge-non'>NON</span>"
                    cls = {"1":"badge-1","X":"badge-x","2":"badge-2"}.get(r1x2,"")
                    b_1x2 = f"<span class='{cls}'>{r1x2}</span>" if cls else r1x2
                    c = st.columns([3,1,1,1])
                    c[0].markdown(f"**{m.get('home_team','?')}** vs **{m.get('away_team','?')}**")
                    c[1].markdown(f"**{hs}:{as_}**")
                    c[2].markdown(b_gng, unsafe_allow_html=True)
                    c[3].markdown(b_1x2, unsafe_allow_html=True)
    else:
        st.info("Résultats non disponibles.")

# ── Config ───────────────────────────────────────────────────
with tab4:
    st.markdown("### ⚙️ Configuration")
    st.markdown("#### Variables d'environnement")
    env_ok = all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO])
    for k, v in [("GITHUB_TOKEN", "✅" if GITHUB_TOKEN else "❌"), ("GITHUB_OWNER", GITHUB_OWNER or "❌"), ("GITHUB_REPO", GITHUB_REPO or "❌"), ("GITHUB_BRANCH", GITHUB_BRANCH)]:
        st.markdown(f"- **{k}**: {v}")
    st.divider()
    st.markdown("#### URLs des données (raw GitHub)")
    for f in ["congobet_1x2_rounds.json","cbet_odds.json","cbet_results.json"]:
        st.code(f"{RAW_BASE}/{f}")
    st.divider()
    st.markdown("#### Derniers runs GitHub Actions")
    if env_ok:
        runs = get_workflow_runs()
        for run in runs[:5]:
            icons = {"success":"✅","failure":"❌","in_progress":"🔄","queued":"⏳"}
            ic = icons.get(run.get("status",""),"❓")
            st.markdown(f"{ic} **{run.get('name','Run')}** · {run.get('conclusion', run.get('status','—'))} · il y a {fmt_ago(run.get('created_at',''))}")
    else:
        st.caption("Configurez les secrets pour voir les runs")
    st.divider()
    st.markdown("""#### Timing
| Événement | Délai |
|---|---|
| Cron GitHub | toutes les 5 min |
| Scrape 1X2 + G/NG | ~45s |
| Attente inter-cycle | 2 min 30s |
| Scrape résultats | ~30s |
| Résultats dispos site | ~30s après fin match |
| Rafraîchissement dashboard | 30s automatique |""")
