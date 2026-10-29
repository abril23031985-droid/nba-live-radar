import pandas as pd
import numpy as np
import time
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams

def get_nba_data(season='2023-24'):
    print(f"Scaricando i dati per la stagione {season}...")
    gamefinder = leaguegamefinder.LeagueGameFinder(season_nullable=season, league_id_nullable='00')
    games = gamefinder.get_data_frames()[0]
    games = games[games['SEASON_ID'].str[0].isin(['2', '4'])]
    return games

def calculate_advanced_stats(df):
    print("Calcolando statistiche avanzate (Pace, Off Rating, e Four Factors parziali)...")
    cols_to_convert = ['FGA', 'TOV', 'FTA', 'OREB', 'DREB', 'PTS', 'FGM', 'FG3M', 'FG3A', 'FTM']
    for col in cols_to_convert:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Possessi stimati
    df['POSSESSIONS'] = 0.96 * (df['FGA'] + df['TOV'] + 0.44 * df['FTA'] - df['OREB'])
    
    # 1. Shooting Efficiency (eFG%)
    df['eFG_PCT'] = (df['FGM'] + 0.5 * df['FG3M']) / df['FGA']
    
    # 2. Turnover Avoidance (TOV% secondo formula Dean Oliver)
    df['TOV_PCT'] = df['TOV'] / (df['FGA'] + 0.44 * df['FTA'] + df['TOV'])
    
    # 4. Free Throw Factor (FTr)
    df['FTr'] = df['FTM'] / df['FGA']  # Usiamo FTM o FTA, scegliamo FTM per valutare punti effettivi, o FTA per viaggi in lunetta
    
    df['OFF_RATING'] = (df['PTS'] / df['POSSESSIONS']) * 100
    
    return df

def prepare_matchup_dataset(df):
    print("Preparando il dataset dei matchup per il Machine Learning...")
    
    # Calcolo dei giorni di riposo (REST_DAYS)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by=['TEAM_ID', 'GAME_DATE'])
    df['REST_DAYS'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    df['REST_DAYS'] = df['REST_DAYS'].fillna(7).clip(upper=7) # Cap a 7 giorni
    
    df['HOME_GAME'] = df['MATCHUP'].str.contains(' vs. ').astype(int)
    home_games = df[df['HOME_GAME'] == 1].copy()
    away_games = df[df['HOME_GAME'] == 0].copy()
    
    home_cols = {col: f'HOME_{col}' for col in home_games.columns if col not in ['GAME_ID', 'GAME_DATE']}
    away_cols = {col: f'AWAY_{col}' for col in away_games.columns if col not in ['GAME_ID', 'GAME_DATE']}
    
    home_games.rename(columns=home_cols, inplace=True)
    away_games.rename(columns=away_cols, inplace=True)
    
    matchups = pd.merge(home_games, away_games, on=['GAME_ID', 'GAME_DATE'])
    
    # 3. Rebounding (ORB%) - Calcolato in base ai rimbalzi difensivi avversari
    matchups['HOME_ORB_PCT'] = matchups['HOME_OREB'] / (matchups['HOME_OREB'] + matchups['AWAY_DREB'])
    matchups['AWAY_ORB_PCT'] = matchups['AWAY_OREB'] / (matchups['AWAY_OREB'] + matchups['HOME_DREB'])
    
    # Defensive Rating (Punti concessi per 100 possessi)
    matchups['HOME_DEF_RATING'] = (matchups['AWAY_PTS'] / matchups['HOME_POSSESSIONS']) * 100
    matchups['AWAY_DEF_RATING'] = (matchups['HOME_PTS'] / matchups['AWAY_POSSESSIONS']) * 100
    
    # Targets (Vittoria, Totale Punti, Handicap/Scarto)
    matchups['TARGET_HOME_WIN'] = (matchups['HOME_WL'] == 'W').astype(int)
    matchups['TOTAL_POINTS'] = matchups['HOME_PTS'] + matchups['AWAY_PTS']
    matchups['POINT_DIFF'] = matchups['HOME_PTS'] - matchups['AWAY_PTS']
    
    # Gestione infiniti/NaN risultanti dalle divisioni
    matchups = matchups.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    return matchups

def run_pipeline():
    games_df = get_nba_data('2023-24')
    games_df = calculate_advanced_stats(games_df)
    matchup_df = prepare_matchup_dataset(games_df)
    
    matchup_df.to_csv('nba_matchups_2023_24.csv', index=False)
    print("Dati salvati con successo in 'nba_matchups_2023_24.csv'")
    
if __name__ == "__main__":
    run_pipeline()
