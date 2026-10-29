import pandas as pd
import numpy as np
from scipy.stats import poisson
import warnings
warnings.filterwarnings('ignore')

from nba_api.stats.endpoints import leaguegamelog
from nba_api.stats.static import players

# File di cache per evitare di scaricare ogni volta
PROPS_DATA_PATH = "nba_player_logs_23_24.csv"

def fetch_player_data(season='2023-24'):
    print(f"Scaricamento dei Game Logs dei giocatori per la stagione {season}...")
    # Fetch player game logs
    gamelog = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
    df = gamelog.get_data_frames()[0]
    
    # Pulizia base
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by=['PLAYER_ID', 'GAME_DATE'])
    
    # La colonna MIN potrebbe essere formato 'MM:SS' o float. Nel gamelog recente è intero o frazione
    # Proviamo a convertirla in float in modo sicuro
    def parse_min(m):
        if isinstance(m, str) and ':' in m:
            parts = m.split(':')
            return float(parts[0]) + float(parts[1])/60.0
        return float(m)
    
    df['MIN_FLOAT'] = df['MIN'].apply(parse_min)
    
    # Filtriamo le partite dove il giocatore ha giocato almeno 5 minuti
    df = df[df['MIN_FLOAT'] >= 5.0]
    
    # Calcolo Per-Minute Stats (PPM, RPM, APM)
    df['PPM'] = df['PTS'] / df['MIN_FLOAT']
    df['RPM'] = df['REB'] / df['MIN_FLOAT']
    df['APM'] = df['AST'] / df['MIN_FLOAT']
    df['3PM_PM'] = df['FG3M'] / df['MIN_FLOAT'] # Triple per minuto
    
    df.to_csv(PROPS_DATA_PATH, index=False)
    print("Dati giocatori salvati con successo in", PROPS_DATA_PATH)
    return df

def calculate_player_projections(df):
    """
    Calcola le medie mobili esponenziali (EMA) come suggerito nel testo,
    dando più peso (70%) alle ultime 10 gare.
    """
    print("Calcolo delle proiezioni tramite Medie Mobili Esponenziali (EMA)...")
    
    # Creiamo un dizionario con le proiezioni per ogni giocatore
    projections = {}
    
    for player_id, group in df.groupby('PLAYER_ID'):
        player_name = group['PLAYER_NAME'].iloc[0]
        
        # Ordiniamo cronologicamente per sicurezza
        group = group.sort_values('GAME_DATE')
        
        if len(group) < 5:
            continue # Troppe poche partite per proiettare
            
        # Calcolo EMA per Minuti, PPM, RPM, APM (span=10 corrisponde a circa 70% peso sulle ultime gare)
        # Preleviamo l'ultimo valore calcolato dalla EMA
        ema_min = group['MIN_FLOAT'].ewm(span=10, adjust=False).mean().iloc[-1]
        ema_ppm = group['PPM'].ewm(span=10, adjust=False).mean().iloc[-1]
        ema_rpm = group['RPM'].ewm(span=10, adjust=False).mean().iloc[-1]
        ema_apm = group['APM'].ewm(span=10, adjust=False).mean().iloc[-1]
        ema_3pm = group['3PM_PM'].ewm(span=10, adjust=False).mean().iloc[-1]
        
        projections[player_name] = {
            'Proj_MIN': ema_min,
            'Proj_PTS': ema_ppm * ema_min,
            'Proj_REB': ema_rpm * ema_min,
            'Proj_AST': ema_apm * ema_min,
            'Proj_3PM': ema_3pm * ema_min,
            'Proj_PRA': (ema_ppm + ema_rpm + ema_apm) * ema_min
        }
        
    return projections

def analyze_player_prop(projections, player_name, market, line, over_odds=1.90, under_odds=1.90, custom_minutes=None):
    """
    Analizza una linea (es. Over 24.5 Punti) usando la distribuzione di Poisson.
    market: 'PTS', 'REB', 'AST', '3PM', 'PRA'
    """
    if player_name not in projections:
        return {"error": "Giocatore non trovato o dati insufficienti."}
    
    proj = projections[player_name]
    
    # Se viene fornita una stima di minuti custom (es. titolare infortunato)
    mins = custom_minutes if custom_minutes else proj['Proj_MIN']
    
    # Ricalcoliamo il valore atteso (Lambda per Poisson) in base ai minuti
    if market == 'PTS': base_lambda = (proj['Proj_PTS'] / proj['Proj_MIN']) * mins
    elif market == 'REB': base_lambda = (proj['Proj_REB'] / proj['Proj_MIN']) * mins
    elif market == 'AST': base_lambda = (proj['Proj_AST'] / proj['Proj_MIN']) * mins
    elif market == '3PM': base_lambda = (proj['Proj_3PM'] / proj['Proj_MIN']) * mins
    elif market == 'PRA': base_lambda = (proj['Proj_PRA'] / proj['Proj_MIN']) * mins
    else: return {"error": "Mercato non supportato."}
    
    # Poiché Poisson lavora con numeri interi, la probabilità di Over 24.5 
    # equivale a P(X >= 25). Quindi 1 - P(X <= 24)
    target_int = int(np.floor(line))
    
    prob_under = poisson.cdf(target_int, base_lambda)
    prob_over = 1.0 - prob_under
    
    # Expected Value
    ev_over = (prob_over * ((over_odds * 100) - 100)) - (prob_under * 100)
    ev_under = (prob_under * ((under_odds * 100) - 100)) - (prob_over * 100)
    
    return {
        'Player': player_name,
        'Market': market,
        'Line': line,
        'Projected_Minutes': mins,
        'Expected_Value_Stat': base_lambda,
        'Prob_Over': prob_over,
        'Prob_Under': prob_under,
        'EV_Over': ev_over,
        'EV_Under': ev_under
    }

if __name__ == "__main__":
    df = fetch_player_data()
    projs = calculate_player_projections(df)
    
    print("\n--- TEST ANALISI PLAYER PROP ---")
    # Esempio: LeBron James Over/Under 25.5 Punti
    res = analyze_player_prop(projs, "LeBron James", 'PTS', 25.5)
    print("LeBron James Punti (Linea 25.5):")
    print(f"  Proiezione AI: {res['Expected_Value_Stat']:.1f} Punti")
    print(f"  Probabilità Over: {res['Prob_Over']*100:.1f}%")
    print(f"  Probabilità Under: {res['Prob_Under']*100:.1f}%")
