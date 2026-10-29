import urllib.request
import json
import numpy as np
import pandas as pd
from scipy.stats import poisson
from datetime import datetime
import os

# Base headers for ESPN API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_scoreboard(date_str=None):
    """
    Recupera le partite NBA per una data specifica (formato YYYYMMDD o YYYY-MM-DD).
    Se vuoto, usa la data odierna.
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y%m%d')
    else:
        date_str = date_str.replace("-", "")
        
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    data = fetch_json(url)
    if not data or 'events' not in data:
        return []
    
    games = []
    for event in data.get('events', []):
        gid = event.get('id')
        name = event.get('name')
        short_name = event.get('shortName')
        status_info = event.get('status', {})
        status_type = status_info.get('type', {})
        
        state = status_type.get('state', 'pre') # 'pre', 'in', 'post'
        status_desc = status_type.get('description', '')
        clock = status_info.get('displayClock', '')
        period = status_info.get('period', 0)
        
        competitions = event.get('competitions', [{}])[0]
        competitors = competitions.get('competitors', [])
        
        home = {}
        away = {}
        for comp in competitors:
            t_info = {
                'id': comp.get('id'),
                'name': comp.get('team', {}).get('displayName', ''),
                'shortName': comp.get('team', {}).get('shortDisplayName', ''),
                'abbreviation': comp.get('team', {}).get('abbreviation', ''),
                'logo': comp.get('team', {}).get('logo', ''),
                'score': int(comp.get('score', 0)) if comp.get('score') else 0,
                'record': comp.get('records', [{}])[0].get('summary', '') if comp.get('records') else ''
            }
            if comp.get('homeAway') == 'home':
                home = t_info
            else:
                away = t_info
                
        games.append({
            'game_id': gid,
            'name': name,
            'short_name': short_name,
            'state': state, # 'pre', 'in', 'post'
            'status_desc': status_desc,
            'clock': clock,
            'period': period,
            'home': home,
            'away': away
        })
    return games

def parse_stat_value(val_str, default=0.0):
    if not val_str:
        return default
    try:
        val_str = str(val_str).strip()
        if '-' in val_str:
            made, att = val_str.split('-')
            return float(made), float(att)
        return float(val_str)
    except Exception:
        return default

def calculate_radar_analysis(game_id):
    """
    Scarica il summary/boxscore in tempo reale della partita e calcola:
    - Minuti residui attesi (PRM)
    - Fattore Foul Trouble (falli personali)
    - Fattore Blowout (rischio panchinamento garbage time)
    - Run Rate al minuto (PPM, RPM, APM)
    - Proiezioni finali e Segnali Radar (OVER / UNDER Value)
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    data = fetch_json(url)
    if not data or 'boxscore' not in data:
        return None
    
    header = data.get('header', {})
    comp = header.get('competitions', [{}])[0]
    status_info = comp.get('status', {})
    status_type = status_info.get('type', {})
    state = status_type.get('state', 'pre')
    period = status_info.get('period', 1)
    display_clock = status_info.get('displayClock', '12:00')
    
    # Calcolo minuti totali trascorsi nella partita
    # Ogni quarto dura 12 minuti. Se siamo nel periodo P:
    clock_mins = 12.0
    if ':' in str(display_clock):
        try:
            m, s = display_clock.split(':')
            clock_mins = float(m) + float(s)/60.0
        except Exception:
            clock_mins = 0.0
    elif display_clock:
        try:
            clock_mins = float(display_clock) / 60.0
        except Exception:
            clock_mins = 0.0
            
    if state == 'post':
        elapsed_game_mins = 48.0 if period <= 4 else 48.0 + (period - 4) * 5.0
        remaining_game_mins = 0.0
    elif state == 'pre':
        elapsed_game_mins = 0.0
        remaining_game_mins = 48.0
    else: # 'in' (in diretta)
        if period <= 4:
            elapsed_game_mins = ((period - 1) * 12.0) + (12.0 - clock_mins)
            remaining_game_mins = max(0.0, 48.0 - elapsed_game_mins)
        else:
            elapsed_game_mins = 48.0 + ((period - 5) * 5.0) + (5.0 - clock_mins)
            remaining_game_mins = max(0.0, 5.0 - clock_mins)
            
    # Analisi punteggi e rischio Blowout
    home_score = 0
    away_score = 0
    teams_box = data.get('boxscore', {}).get('players', [])
    for comp_team in comp.get('competitors', []):
        if comp_team.get('homeAway') == 'home':
            home_score = int(comp_team.get('score', 0))
        else:
            away_score = int(comp_team.get('score', 0))
            
    margin = abs(home_score - away_score)
    is_blowout_risk = False
    blowout_penalty_mins = 0.0
    if period >= 3 and margin >= 18:
        is_blowout_risk = True
        blowout_penalty_mins = 4.0 if margin < 24 else 8.0 # Perdita minuti nel 4Q
    elif period == 4 and margin >= 15:
        is_blowout_risk = True
        blowout_penalty_mins = 6.0
        
    # Calcolo Live Pace della gara (stima possessi)
    total_points = home_score + away_score
    if elapsed_game_mins > 3.0:
        # Punti/minuto combinati moltiplicati per 48
        est_total_pts_48 = (total_points / elapsed_game_mins) * 48.0
        # Pace ratio: se la gara viaggia a 230 punti vs media 220
        pace_multiplier = min(1.25, max(0.80, est_total_pts_48 / 222.0))
    else:
        pace_multiplier = 1.0
        est_total_pts_48 = 222.0
        
    # Analisi dei giocatori
    players_analyzed = []
    
    for team_data in teams_box:
        team_name = team_data.get('team', {}).get('displayName', '')
        team_abbr = team_data.get('team', {}).get('abbreviation', '')
        stat_entries = team_data.get('statistics', [])
        if not stat_entries:
            continue
            
        names = stat_entries[0].get('names', [])
        athletes = stat_entries[0].get('athletes', [])
        
        for ath in athletes:
            athlete_info = ath.get('athlete', {})
            player_name = athlete_info.get('displayName', '')
            headshot = athlete_info.get('headshot', {}).get('href', '')
            position = athlete_info.get('position', {}).get('abbreviation', 'G/F')
            is_starter = ath.get('starter', False)
            raw_stats = ath.get('stats', [])
            
            if not raw_stats or len(raw_stats) < len(names):
                continue
                
            stat_dict = dict(zip(names, raw_stats))
            
            # Parsing MIN
            min_raw = stat_dict.get('MIN', '0')
            try:
                if ':' in str(min_raw):
                    pm, ps = str(min_raw).split(':')
                    mins_played = float(pm) + float(ps)/60.0
                else:
                    mins_played = float(min_raw)
            except Exception:
                mins_played = 0.0
                
            # Se la partita è in corso o finita, consideriamo solo chi è entrato
            if state != 'pre' and mins_played < 0.5:
                continue
                
            pts = float(stat_dict.get('PTS', 0))
            reb = float(stat_dict.get('REB', 0))
            ast = float(stat_dict.get('AST', 0))
            fouls = float(stat_dict.get('PF', 0))
            
            # Tiri da 3
            fg3_val = stat_dict.get('3PT', '0-0')
            fg3m, fg3a = parse_stat_value(fg3_val) if '-' in str(fg3_val) else (float(fg3_val), 0.0)
            
            # Tiri dal campo totali
            fg_val = stat_dict.get('FG', '0-0')
            fgm, fga = parse_stat_value(fg_val) if '-' in str(fg_val) else (float(fg_val), 0.0)
            
            # Calcolo Foul Trouble Penalty
            foul_penalty_mins = 0.0
            foul_status = "OK"
            if period == 1 and fouls >= 2:
                foul_penalty_mins = 5.0
                foul_status = "⚠️ 2 Falli nel 1Q"
            elif period == 2 and fouls >= 3:
                foul_penalty_mins = 6.0
                foul_status = "🚨 3 Falli nel 1° Tempo"
            elif period == 3 and fouls >= 4:
                foul_penalty_mins = 7.0
                foul_status = "⛔ 4 Falli (Panchina)"
            elif fouls >= 5:
                foul_penalty_mins = 9.0
                foul_status = "🔥 5 Falli (Rischio Espulsione)"
                
            # Stima Minuti Totali e Residui (PRM)
            if state == 'post':
                proj_total_mins = mins_played
                prm = 0.0
            elif state == 'pre':
                proj_total_mins = 34.0 if is_starter else 18.0
                prm = proj_total_mins
            else:
                # Partita IN DIRETTA:
                # Quanti minuti era programmato a giocare?
                base_target_mins = 34.0 if is_starter else 20.0
                
                # Se è già in campo e ha giocato tanto, proiettiamo il ritmo di rotazione
                if elapsed_game_mins > 6.0:
                    rotation_pace_mins = (mins_played / elapsed_game_mins) * 48.0
                    # Media tra target prestabilito e rotazione effettiva odierna
                    est_target = (base_target_mins * 0.4) + (rotation_pace_mins * 0.6)
                else:
                    est_target = base_target_mins
                    
                # Applichiamo penalità falli e rischio blowout (solo se titolare)
                if is_starter:
                    est_target = max(mins_played, est_target - foul_penalty_mins - blowout_penalty_mins)
                else:
                    est_target = max(mins_played, est_target - foul_penalty_mins)
                    
                proj_total_mins = min(44.0, max(mins_played, est_target))
                prm = max(0.0, proj_total_mins - mins_played)
                
            # Calcolo Run Rates al minuto
            if mins_played > 0:
                ppm_live = pts / mins_played
                rpm_live = reb / mins_played
                apm_live = ast / mins_played
                fg3m_live = fg3m / mins_played
            else:
                # Pre-game baseline
                ppm_live = 0.55 if is_starter else 0.40
                rpm_live = 0.18
                apm_live = 0.14
                fg3m_live = 0.06
                
            # Blended Rate per i minuti rimanenti (regredisce dolcemente verso la media per evitare sovra-reazioni)
            # Diamo peso 65% al ritmo odierno e 35% a un'efficienza standard per evitare estremi
            ppm_rest = (ppm_live * 0.65) + (0.50 * 0.35)
            rpm_rest = (rpm_live * 0.65) + (0.16 * 0.35)
            apm_rest = (apm_live * 0.65) + (0.12 * 0.35)
            fg3m_rest = (fg3m_live * 0.70) + (0.05 * 0.30)
            
            # Proiezioni Finali
            proj_pts = pts + (prm * ppm_rest * pace_multiplier)
            proj_reb = reb + (prm * rpm_rest * pace_multiplier)
            proj_ast = ast + (prm * apm_rest * pace_multiplier)
            proj_3pm = fg3m + (prm * fg3m_rest * pace_multiplier)
            proj_pra = proj_pts + proj_reb + proj_ast
            
            # Radar Score & Segnali Operativi
            radar_signal = "HOLD"
            signal_color = "gray"
            recommended_bet = ""
            confidence = 0
            
            # 1. Segnale OVER SCORING (Giocatore caldo, ritmo alto, minuti garantiti)
            if proj_pts >= 30.0 and foul_penalty_mins == 0 and not is_blowout_risk:
                radar_signal = "🔥 STRONG OVER (SCORER)"
                signal_color = "green"
                recommended_line = np.floor(proj_pts - 4.5) + 0.5
                recommended_bet = f"Punta OVER {recommended_line:.1f} PTS"
                confidence = 88 if proj_pts >= 35.0 else 78
            elif proj_pts >= 24.0 and ppm_live >= 0.75 and foul_penalty_mins == 0:
                radar_signal = "🟢 VALUE OVER"
                signal_color = "lightgreen"
                recommended_line = np.floor(proj_pts - 3.5) + 0.5
                recommended_bet = f"Punta OVER {recommended_line:.1f} PTS"
                confidence = 74
            # 2. Segnale UNDER (Falli o rischio blowout)
            elif foul_penalty_mins >= 5.0 and is_starter:
                radar_signal = "❄️ FADE / UNDER (FOULS)"
                signal_color = "red"
                recommended_line = np.ceil(proj_pts + 3.5) + 0.5
                recommended_bet = f"Punta UNDER {recommended_line:.1f} PTS (Foul Trouble)"
                confidence = 82
            elif is_blowout_risk and is_starter:
                radar_signal = "⚠️ UNDER (BLOWOUT BENCH)"
                signal_color = "orange"
                recommended_line = np.ceil(proj_pts + 3.5) + 0.5
                recommended_bet = f"Punta UNDER {recommended_line:.1f} PTS (Garbage Time)"
                confidence = 76
            elif proj_pra >= 40.0:
                radar_signal = "💎 TRIPLE VALUE (PRA)"
                signal_color = "blue"
                recommended_line = np.floor(proj_pra - 4.5) + 0.5
                recommended_bet = f"Punta OVER {recommended_line:.1f} PRA"
                confidence = 80
                
            players_analyzed.append({
                'name': player_name,
                'team': team_abbr,
                'headshot': headshot,
                'position': position,
                'is_starter': is_starter,
                'mins_played': round(mins_played, 1),
                'prm': round(prm, 1),
                'proj_total_mins': round(proj_total_mins, 1),
                'pts': int(pts),
                'reb': int(reb),
                'ast': int(ast),
                'fg3m': int(fg3m),
                'fouls': int(fouls),
                'foul_status': foul_status,
                'ppm_live': round(ppm_live, 2),
                'proj_pts': round(proj_pts, 1),
                'proj_reb': round(proj_reb, 1),
                'proj_ast': round(proj_ast, 1),
                'proj_3pm': round(proj_3pm, 1),
                'proj_pra': round(proj_pra, 1),
                'radar_signal': radar_signal,
                'signal_color': signal_color,
                'recommended_bet': recommended_bet,
                'confidence': confidence
            })
            
    # Ordiniamo i giocatori per proiezione punti o rilevanza del segnale
    players_analyzed = sorted(players_analyzed, key=lambda x: (x['confidence'], x['proj_pts']), reverse=True)
    
    return {
        'game_state': state,
        'period': period,
        'clock': display_clock,
        'elapsed_mins': round(elapsed_game_mins, 1),
        'remaining_mins': round(remaining_game_mins, 1),
        'home_score': home_score,
        'away_score': away_score,
        'margin': margin,
        'is_blowout_risk': is_blowout_risk,
        'pace_multiplier': round(pace_multiplier, 2),
        'est_total_pts': round(est_total_pts_48, 1),
        'players': players_analyzed
    }

def calculate_poisson_edge(proj_stat, bookmaker_line, over_odds=1.85, under_odds=1.85):
    """
    Calcola la probabilità di superare una specifica linea e l'Expected Value.
    """
    target = int(np.floor(bookmaker_line))
    prob_under = poisson.cdf(target, proj_stat)
    prob_over = 1.0 - prob_under
    
    stake = 100
    ev_over = (prob_over * ((over_odds * stake) - stake)) - (prob_under * stake)
    ev_under = (prob_under * ((under_odds * stake) - stake)) - (prob_over * stake)
    
    return {
        'prob_over': prob_over,
        'prob_under': prob_under,
        'ev_over': round(ev_over, 2),
        'ev_under': round(ev_under, 2)
    }

if __name__ == "__main__":
    print("Test Radar Engine con una partita recente...")
    analysis = calculate_radar_analysis('401704668')
    if analysis:
        print(f"Stato: {analysis['game_state']} | Margine: {analysis['margin']} | Pace Mult: {analysis['pace_multiplier']}")
        print(f"Giocatori analizzati: {len(analysis['players'])}")
        print("\nTop 3 Segnali Radar:")
        for p in analysis['players'][:3]:
            print(f" - {p['name']} ({p['team']}): PTS Attuali: {p['pts']}, Proiezione: {p['proj_pts']} | Segnale: {p['radar_signal']} | Consiglio: {p['recommended_bet']}")
