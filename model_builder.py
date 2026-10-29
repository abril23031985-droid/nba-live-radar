import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error
import pickle
import os

def build_model(csv_path='nba_matchups_2023_24.csv'):
    if not os.path.exists(csv_path):
        print(f"Errore: il file {csv_path} non esiste. Esegui prima data_pipeline.py.")
        return

    print("Caricamento dataset...")
    df = pd.read_csv(csv_path)

    # Nuove feature incluse: 4 Factors Completi (eFG%, TOV%, ORB%, FTr), Defensive Rating e Rest Days
    features = [
        'HOME_OFF_RATING', 'AWAY_OFF_RATING',
        'HOME_DEF_RATING', 'AWAY_DEF_RATING',
        'HOME_eFG_PCT', 'AWAY_eFG_PCT',
        'HOME_TOV_PCT', 'AWAY_TOV_PCT',
        'HOME_ORB_PCT', 'AWAY_ORB_PCT',
        'HOME_FTr', 'AWAY_FTr',
        'HOME_REST_DAYS', 'AWAY_REST_DAYS'
    ]
    
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=features + ['TARGET_HOME_WIN', 'TOTAL_POINTS', 'POINT_DIFF'])

    X = df[features]
    
    # 1. Modello per Testa a Testa (Vittoria)
    y_win = df['TARGET_HOME_WIN']
    X_train, X_test, y_train, y_test = train_test_split(X, y_win, test_size=0.2, random_state=42)
    model_win = LogisticRegression(max_iter=1000)
    model_win.fit(X_train, y_train)
    print(f"Accuratezza Modello Vittoria: {accuracy_score(y_test, model_win.predict(X_test))*100:.2f}%")
    
    # 2. Modello per Over/Under (Punti Totali)
    y_total = df['TOTAL_POINTS']
    X_train, X_test, y_train, y_test = train_test_split(X, y_total, test_size=0.2, random_state=42)
    model_total = Ridge(alpha=1.0)
    model_total.fit(X_train, y_train)
    print(f"Errore Medio Modello Totali (MAE): {mean_absolute_error(y_test, model_total.predict(X_test)):.1f} punti")
    
    # 3. Modello per Handicap (Scarto Punti)
    y_diff = df['POINT_DIFF']
    X_train, X_test, y_train, y_test = train_test_split(X, y_diff, test_size=0.2, random_state=42)
    model_spread = Ridge(alpha=1.0)
    model_spread.fit(X_train, y_train)
    print(f"Errore Medio Modello Scarto (MAE): {mean_absolute_error(y_test, model_spread.predict(X_test)):.1f} punti")

    # Salvataggio dei 3 modelli
    with open('nba_model_win.pkl', 'wb') as f: pickle.dump(model_win, f)
    with open('nba_model_total.pkl', 'wb') as f: pickle.dump(model_total, f)
    with open('nba_model_spread.pkl', 'wb') as f: pickle.dump(model_spread, f)
        
    print("Modelli salvati con successo!")

if __name__ == "__main__":
    build_model()
