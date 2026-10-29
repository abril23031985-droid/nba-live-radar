import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import live_radar_engine as lre
import player_props_model as ppm

st.set_page_config(
    page_title="NBA on Air | Live Broadcast Radar",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# STILE GRAFICO TNT / ESPN BROADCAST EDITION
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800;900&family=Chakra+Petch:wght@600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }

    /* Sfondo Generale Broadcast */
    .stApp {
        background: linear-gradient(180deg, #0B0E14 0%, #121721 100%);
        color: #E6EDF3;
    }

    /* TV Header Banner */
    .broadcast-header {
        background: linear-gradient(90deg, #C9082A 0%, #17408B 60%, #0F2027 100%);
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid #FDB927;
    }
    .broadcast-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 1.8em;
        font-weight: 900;
        letter-spacing: 1px;
        color: #FFFFFF;
        text-transform: uppercase;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .broadcast-badge {
        background: #FDB927;
        color: #0B0E14;
        font-size: 0.55em;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 900;
        letter-spacing: 1.5px;
        vertical-align: middle;
    }

    /* Scoreboard Card stile Lower-Thirds TV */
    .tv-score-card {
        background: linear-gradient(135deg, #1A202C 0%, #141821 100%);
        border: 1px solid #2D3748;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 6px 16px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .tv-score-card:hover {
        transform: translateY(-2px);
        border-color: #FDB927;
    }
    .tv-game-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #2D3748;
        padding-bottom: 6px;
        margin-bottom: 10px;
    }
    .tv-live-pill {
        background: #E03A3E;
        color: #FFFFFF;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: 800;
        letter-spacing: 0.5px;
        animation: tv-pulse 1.5s infinite;
    }
    .tv-final-pill {
        background: #2D3748;
        color: #A0AEC0;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: 700;
    }
    .tv-clock {
        font-family: 'Chakra Petch', monospace;
        color: #00E676;
        font-weight: 700;
        font-size: 0.9em;
    }
    .tv-team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
    }
    .tv-team-info {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .tv-team-name {
        font-weight: 700;
        font-size: 1.05em;
        color: #FFFFFF;
    }
    .tv-team-score {
        font-family: 'Chakra Petch', monospace;
        font-size: 1.4em;
        font-weight: 700;
        color: #FDB927;
    }

    /* Player Spotlight Card */
    .player-spotlight-card {
        background: linear-gradient(145deg, #18202F 0%, #121722 100%);
        border: 1px solid #2B384E;
        border-top: 3px solid #00E676;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    .player-spotlight-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 14px;
    }
    .player-photo {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        border: 2px solid #FDB927;
        background: #0B0E14;
        object-fit: cover;
    }
    .player-meta h3 {
        margin: 0;
        font-size: 1.25em;
        font-weight: 800;
        color: #FFFFFF;
    }
    .player-meta span {
        font-size: 0.85em;
        color: #A0AEC0;
        font-weight: 600;
    }

    /* Barra di progresso TV Broadcast */
    .tv-progress-container {
        background: #1A202C;
        border-radius: 8px;
        height: 18px;
        width: 100%;
        position: relative;
        overflow: hidden;
        margin: 8px 0;
        border: 1px solid #2D3748;
    }
    .tv-progress-current {
        background: linear-gradient(90deg, #17408B 0%, #00B0FF 100%);
        height: 100%;
        border-radius: 8px 0 0 8px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 6px;
        font-size: 0.7em;
        font-weight: 800;
        color: #FFF;
    }
    .tv-progress-proj {
        background: rgba(0, 230, 118, 0.35);
        height: 100%;
        position: absolute;
        top: 0;
        border-right: 3px solid #00E676;
    }

    /* Badge Segnali TV */
    .badge-signal-fire {
        background: linear-gradient(90deg, #FF3D00 0%, #FF9100 100%);
        color: #FFF;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.85em;
        letter-spacing: 0.5px;
        box-shadow: 0 0 12px rgba(255, 61, 0, 0.4);
    }
    .badge-signal-value {
        background: linear-gradient(90deg, #00C853 0%, #64DD17 100%);
        color: #000;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.85em;
        letter-spacing: 0.5px;
    }
    .badge-signal-fade {
        background: linear-gradient(90deg, #D50000 0%, #FF1744 100%);
        color: #FFF;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.85em;
    }

    /* Live pulse animation */
    @keyframes tv-pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# BROADCAST HEADER TV
# -------------------------------------------------------------
st.markdown("""
<div class="broadcast-header">
    <div class="broadcast-title">
        <span>🏀 NBA ON AIR</span>
        <span class="broadcast-badge">LIVE BROADCAST RADAR</span>
    </div>
    <div style="text-align:right;">
        <span style="font-family:'Chakra Petch', monospace; font-size:1.1em; font-weight:700; color:#FDB927;">ESPN / TNT QUANTITATIVE EDITION</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
st.sidebar.markdown("### ⚙️ STUDIO BROADCAST CONTROL")
selected_date = st.sidebar.date_input("Data Match", datetime.now().date(), key="radar_date")
date_str = selected_date.strftime('%Y%m%d')

auto_refresh = st.sidebar.toggle("🔴 Telemetria Live Auto (30s)", value=True, help="Aggiorna le statistiche, i falli e le proiezioni ogni 30 secondi in tempo reale.")
refresh_interval = 30 if auto_refresh else None

if st.sidebar.button("🔄 Sync Dati Immediato"):
    st.rerun()

st.sidebar.markdown("---")
min_confidence = st.sidebar.slider("Filtro Affidabilità (%)", 0, 95, 60, step=5, key="conf_slider")
only_hot_picks = st.sidebar.checkbox("Filtra solo Top Picks (Over/Under)", value=False, key="hot_picks_check")

# TAB NAVIGATION
tab_live, tab_singolo, tab_prematch = st.tabs([
    "📺 LIVE BROADCAST RADAR",
    "🔍 PLAYER SPOTLIGHT & EV CALCULATOR",
    "📊 PRE-MATCH STUDIO (FOUR FACTORS)"
])

# -------------------------------------------------------------
# TAB 1: LIVE BROADCAST RADAR (Auto-refresh 30s)
# -------------------------------------------------------------
with tab_live:
    @st.fragment(run_every=refresh_interval)
    def render_live_multimatch(current_date_str, min_conf, only_hot):
        games = lre.get_scoreboard(current_date_str)

        # On-Air status ticker
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            if auto_refresh:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                    <span class="tv-live-pill">● ON AIR LIVE</span>
                    <span style="font-size:0.9em; font-weight:600; color:#CBD5E0;">Feed attivo (Auto-refresh 30s)</span>
                    <span style="font-family:'Chakra Petch', monospace; color:#00E676; font-size:0.95em;">Sync: {datetime.now().strftime('%H:%M:%S')}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption(f"Sync manuale: {datetime.now().strftime('%H:%M:%S')} (Auto-refresh disattivato)")
        with col_t1:
            pass
        with col_t2:
            if st.button("⚡ Ricarica Radar", key="btn_refresh_tab1"):
                st.rerun(scope="fragment")

        if not games:
            st.warning(f"Nessuna partita trovata per il {selected_date.strftime('%d/%m/%Y')}. Seleziona un'altra data dalla barra laterale (es. 28/10/2024 per una serata completa).")
            return

        st.markdown(f"#### 🏆 MATCH IN PROGRAMMA ({len(games)})")
        
        # Schede delle partite in stile Lower-Thirds TV
        cols = st.columns(min(3, len(games)))
        for idx, g in enumerate(games):
            col_target = cols[idx % len(cols)]
            with col_target:
                status_pill = f'<span class="tv-live-pill">LIVE {g["status_desc"]}</span>' if g['state'] == 'in' else (
                    f'<span class="tv-final-pill">FINAL</span>' if g['state'] == 'post' else f'<span class="tv-final-pill">PRE-GAME</span>'
                )
                clock_str = f'<span class="tv-clock">{g["clock"]}</span>' if g['clock'] else ''
                
                st.markdown(f"""
                <div class="tv-score-card">
                    <div class="tv-game-header">
                        {status_pill}
                        {clock_str}
                    </div>
                    <div class="tv-team-row">
                        <div class="tv-team-info">
                            <img src="{g['away']['logo']}" width="28"/>
                            <span class="tv-team-name">{g['away']['shortName']}</span>
                        </div>
                        <span class="tv-team-score">{g['away']['score']}</span>
                    </div>
                    <div class="tv-team-row">
                        <div class="tv-team-info">
                            <img src="{g['home']['logo']}" width="28"/>
                            <span class="tv-team-name">{g['home']['shortName']}</span>
                        </div>
                        <span class="tv-team-score">{g['home']['score']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🎯 RADAR ANALYTICS: GIOCATORI MONITORATI IN TEMPO REALE")
        st.caption("Proiezione finale calcolata ponderando i minuti effettivi, l'allerta falli e il ritmo di gioco.")

        all_radar_players = []
        with st.spinner("Acquisizione telemetria giocatori in corso..."):
            for g in games:
                analysis = lre.calculate_radar_analysis(g['game_id'])
                if analysis and 'players' in analysis:
                    for p in analysis['players']:
                        p['game_name'] = f"{g['away']['abbreviation']} @ {g['home']['abbreviation']}"
                        p['game_state'] = g['status_desc']
                        p['game_id'] = g['game_id']
                        all_radar_players.append(p)

        if not all_radar_players:
            st.info("Nessuna statistica giocatore attualmente disponibile per questi match.")
        else:
            filtered = [p for p in all_radar_players if p['confidence'] >= min_conf]
            if only_hot:
                filtered = [p for p in filtered if p['radar_signal'] != 'HOLD']

            if not filtered:
                st.info("Nessun giocatore corrisponde ai criteri di confidenza selezionati.")
            else:
                # Tabella principale con visualizzazione compatta e leggibile
                table_rows = []
                for p in filtered:
                    table_rows.append({
                        "Match": p['game_name'],
                        "Atleta": f"{p['name']} ({p['position']})",
                        "Squadra": p['team'],
                        "Minuti Giocati": f"{p['mins_played']}'",
                        "Minuti Previsti": f"{p['proj_total_mins']}'",
                        "Punti Attuali": p['pts'],
                        "Proiezione Punti": f"👉 {p['proj_pts']} pts",
                        "Falli": f"{p['fouls']} ({p['foul_status']})",
                        "Segnale": p['radar_signal'],
                        "Consiglio Operativo": p['recommended_bet'],
                        "Affidabilità": f"{p['confidence']}%"
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    render_live_multimatch(date_str, min_confidence, only_hot_picks)

# -------------------------------------------------------------
# TAB 2: PLAYER SPOTLIGHT & EV CALCULATOR (Auto-refresh 30s)
# -------------------------------------------------------------
with tab_singolo:
    @st.fragment(run_every=refresh_interval)
    def render_detailed_calculator(current_date_str):
        games = lre.get_scoreboard(current_date_str)

        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.markdown("#### 🌟 PLAYER SPOTLIGHT & BETTING LAB")
            st.caption(f"Studio televisivo per simulare le linee dei bookmaker in diretta. Sync: {datetime.now().strftime('%H:%M:%S')}")
        with col_top2:
            if st.button("⚡ Aggiorna Atleta", key="btn_refresh_tab2"):
                st.rerun(scope="fragment")

        if not games:
            st.warning("Nessuna partita disponibile per questa data.")
            return

        game_options = {f"{g['away']['name']} @ {g['home']['name']} ({g['status_desc']})": g['game_id'] for g in games}
        selected_match_label = st.selectbox("Seleziona Partita", list(game_options.keys()), key="match_select_box")
        selected_gid = game_options[selected_match_label]

        analysis = lre.calculate_radar_analysis(selected_gid)
        if not analysis or not analysis.get('players'):
            st.warning("Statistiche giocatori non ancora disponibili per questa partita.")
            return

        # Game telemetry bar
        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        t_col1.metric("⏱️ Cronometro", f"{analysis['clock']} - Q{analysis['period']}")
        t_col2.metric("🏀 Scoreboard", f"{analysis['away_score']} - {analysis['home_score']} (Diff: {analysis['margin']})")
        t_col3.metric("⚡ Pace Multiplier", f"{analysis['pace_multiplier']}x ({analysis['est_total_pts']} pt previsti)")
        t_col4.metric("🚨 Rischio Blowout", "⚠️ ALTO (Garbage Time)" if analysis['is_blowout_risk'] else "✅ REGOLARE")

        st.markdown("---")
        player_list = [p['name'] for p in analysis['players']]
        selected_player_name = st.selectbox("Seleziona Giocatore NBA", player_list, key="player_select_box")
        
        p = next((x for x in analysis['players'] if x['name'] == selected_player_name), None)
        if p:
            # Player Spotlight Hero Card
            img_src = p.get('headshot') if p.get('headshot') else "https://cdn.nba.com/headshots/nba/latest/1040x760/fallback.png"
            
            badge_html = f'<span class="badge-signal-fire">{p["radar_signal"]}</span>' if 'STRONG' in p['radar_signal'] else (
                f'<span class="badge-signal-value">{p["radar_signal"]}</span>' if 'VALUE' in p['radar_signal'] else f'<span class="badge-signal-fade">{p["radar_signal"]}</span>'
            )

            st.markdown(f"""
            <div class="player-spotlight-card">
                <div class="player-spotlight-header">
                    <img class="player-photo" src="{img_src}"/>
                    <div class="player-meta">
                        <h3>{p['name']} ({p['position']}) — {p['team']}</h3>
                        <span>Ruolo: {'Titolare' if p['is_starter'] else 'Sesto Uomo / Panchina'} | Falli: {p['fouls']} ({p['foul_status']})</span>
                    </div>
                    <div style="margin-left:auto;">
                        {badge_html}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Barra di progresso Punti TV (Current vs Proj vs Max Benchmark 50)
            max_stat = max(50.0, float(p['proj_pts']) + 5.0)
            curr_pct = min(100.0, (float(p['pts']) / max_stat) * 100.0)
            proj_pct = min(100.0, (float(p['proj_pts']) / max_stat) * 100.0)

            st.markdown(f"**Progressione Punti Live:** {p['pts']} realizzati 👉 **{p['proj_pts']} punti attesi a fine gara**")
            st.markdown(f"""
            <div class="tv-progress-container">
                <div class="tv-progress-proj" style="width: {proj_pct}%;"></div>
                <div class="tv-progress-current" style="width: {curr_pct}%;">{p['pts']} PTS</div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.75em; color:#A0AEC0;">
                <span>0 PTS</span>
                <span>Proiezione: {p['proj_pts']} PTS</span>
                <span>Target 50+ PTS</span>
            </div>
            """, unsafe_allow_html=True)

            # Statistiche dettagliate
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            sc1.metric("Punti (PTS)", f"{p['pts']}  ➔  {p['proj_pts']}")
            sc2.metric("Rimbalzi (REB)", f"{p['reb']}  ➔  {p['proj_reb']}")
            sc3.metric("Assist (AST)", f"{p['ast']}  ➔  {p['proj_ast']}")
            sc4.metric("Triple (3PM)", f"{p['fg3m']}  ➔  {p['proj_3pm']}")
            sc5.metric("P+R+A Totale", f"{p['pts']+p['reb']+p['ast']}  ➔  {p['proj_pra']}")

            if p['recommended_bet']:
                st.success(f"🎯 **CONSIGLIO ON-AIR:** {p['recommended_bet']} (Affidabilità: {p['confidence']}%)")

            # Simulatore di Linee Bookmaker & Poisson EV
            st.markdown("---")
            st.markdown("#### 💰 CALCOLATORE EXPECTED VALUE (+EV)")
            st.caption("Confronta la linea in tempo reale del tuo bookmaker con la distribuzione reale attesa calcolata dall'AI.")

            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1:
                market = st.selectbox("Mercato", ["Punti (PTS)", "Rimbalzi (REB)", "Assist (AST)", "Triple (3PM)", "PRA"], key="mkt_select")
            with bc2:
                def_line = float(p['proj_pts'] - 2.5) if "Punti" in market else (float(p['proj_pra'] - 3.5) if "PRA" in market else 5.5)
                line_val = st.number_input("Linea Quota Bookmaker", min_value=0.5, value=max(0.5, round(def_line, 1)), step=1.0, key="line_box")
            with bc3:
                odds_over = st.number_input("Quota OVER", min_value=1.01, value=1.85, step=0.05, key="odd_over")
            with bc4:
                odds_under = st.number_input("Quota UNDER", min_value=1.01, value=1.85, step=0.05, key="odd_under")

            if "Punti" in market: target_stat = p['proj_pts']
            elif "Rimbalzi" in market: target_stat = p['proj_reb']
            elif "Assist" in market: target_stat = p['proj_ast']
            elif "Triple" in market: target_stat = p['proj_3pm']
            else: target_stat = p['proj_pra']

            ev = lre.calculate_poisson_edge(target_stat, line_val, odds_over, odds_under)

            rc1, rc2 = st.columns(2)
            with rc1:
                st.metric(f"Probabilità OVER {line_val}", f"{ev['prob_over']*100:.1f}%", delta=f"EV: €{ev['ev_over']:.2f}")
                if ev['ev_over'] > 0:
                    st.success(f"🔥 **VALUEBET OVER:** Vantaggio matematico del +{ev['ev_over']}% a quota {odds_over}")
                else:
                    st.caption("Nessun vantaggio statistico su OVER.")
            with rc2:
                st.metric(f"Probabilità UNDER {line_val}", f"{ev['prob_under']*100:.1f}%", delta=f"EV: €{ev['ev_under']:.2f}")
                if ev['ev_under'] > 0:
                    st.success(f"🔥 **VALUEBET UNDER:** Vantaggio matematico del +{ev['ev_under']}% a quota {odds_under}")
                else:
                    st.caption("Nessun vantaggio statistico su UNDER.")

    render_detailed_calculator(date_str)

# -------------------------------------------------------------
# TAB 3: PRE-MATCH STUDIO (FOUR FACTORS)
# -------------------------------------------------------------
with tab_prematch:
    st.markdown("#### 📊 STUDIO TATTICO PRE-GARA: I QUATTRO FATTORI DI DEAN OLIVER")
    st.caption("Analisi quantitativa dell'efficienza su 100 possessi: Tiro effettivo ($eFG\\%$), Palle perse ($TOV\\%$), Rimbalzi ($ORB\\%$) e Tiri Liberi ($FTr$).")

    if os.path.exists("nba_matchups_2023_24.csv"):
        df_hist = pd.read_csv("nba_matchups_2023_24.csv")
        teams_avail = sorted(df_hist['HOME_TEAM_ABBREVIATION'].dropna().unique())
        
        fc1, fc2 = st.columns(2)
        with fc1:
            team_h = st.selectbox("Squadra in Casa", teams_avail, index=0, key="pre_home")
        with fc2:
            team_a = st.selectbox("Squadra in Trasferta", teams_avail, index=1, key="pre_away")

        if team_h != team_a and st.button("Analizza Four Factors Matchup", key="btn_four_factors"):
            h_sub = df_hist[df_hist['HOME_TEAM_ABBREVIATION'] == team_h]
            a_sub = df_hist[df_hist['AWAY_TEAM_ABBREVIATION'] == team_a]

            ff1, ff2 = st.columns(2)
            with ff1:
                st.markdown(f"**🏠 {team_h} (Home Profile):**")
                st.write(f"- Offensive Rating: **{h_sub['HOME_OFF_RATING'].mean():.1f}**")
                st.write(f"- Defensive Rating: **{h_sub['HOME_DEF_RATING'].mean():.1f}**")
                st.write(f"- eFG% (Efficienza Tiro): **{h_sub['HOME_eFG_PCT'].mean()*100:.1f}%**")
                st.write(f"- Turnover%: **{h_sub['HOME_TOV_PCT'].mean()*100:.1f}%**")
                st.write(f"- Offensive Rebound%: **{h_sub['HOME_ORB_PCT'].mean()*100:.1f}%**")
            with ff2:
                st.markdown(f"**✈️ {team_a} (Away Profile):**")
                st.write(f"- Offensive Rating: **{a_sub['AWAY_OFF_RATING'].mean():.1f}**")
                st.write(f"- Defensive Rating: **{a_sub['AWAY_DEF_RATING'].mean():.1f}**")
                st.write(f"- eFG% (Efficienza Tiro): **{a_sub['AWAY_eFG_PCT'].mean()*100:.1f}%**")
                st.write(f"- Turnover%: **{a_sub['AWAY_TOV_PCT'].mean()*100:.1f}%**")
                st.write(f"- Offensive Rebound%: **{a_sub['AWAY_ORB_PCT'].mean()*100:.1f}%**")
    else:
        st.info("Dataset storico pre-gara non presente. Le funzioni live e radar rimangono pienamente attive.")
