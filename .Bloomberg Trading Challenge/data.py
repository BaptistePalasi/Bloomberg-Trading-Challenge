import os
from pathlib import Path

import pdblp

from xbbg import blp

import pandas as pd
from datetime import datetime

import re


con = pdblp.BCon(port=8194, timeout=5000)
con.start()


def membres_index(index_ticker, date = datetime.now().strftime("%Y-%m-%d")):
    safe_tiker = index_ticker.replace(" ","_")
    csv_membre_name = f"membres_{safe_tiker}_date_\'{date}\'.csv"

    repertoir_projet = Path(__file__).resolve().parent

    csv_path = repertoir_projet / "DATA" / csv_membre_name

    print(f"Donnee membre {safe_tiker}, date \'{date}\'")

    if csv_path.exists():
        print(" - CSV lue")
        return pd.read_csv("DATA\\membres_WORLD_Index_date_'2026-10-10'.csv")

    date = date.replace("-","")

    df = con.bulkref(
        tickers=index_ticker,
        flds = 'INDX_MEMBERS',
        ovrds=[("END_DATE_OVERRIDE", date)],
    )

    tickers_value = df['value'].rename(columns={'value': 'Ticker'})

    if not df.empty:
        tickers_value.to_csv(csv_path, index = False)
        print(" - CSV cree")
    else: 
        print(" - Aucune Donnee")
    return tickers_value


def TURNOVER(tikers, date):
    end_date = date.replace("-","")
    start_date = (pd.to_datetime(date) - pd.Timedelta(days=30)).strftime('%Y%m%d')

    safe_tiker = tikers.replace(" ","_")
    csv_name = f"Turnovers_{safe_tiker}_date_\'{date}\'.csv"

    repertoir_projet = Path(__file__).resolve().parent

    csv_path = repertoir_projet / "DATA" / csv_name

    print(f"Donnee membre {safe_tiker}, date \'{date}\'")

    if csv_path.exists():
        print(" - CSV lue")
        return pd.read_csv_path

    date = date.replace("-","")
    

    df = con.bulkref(
        tikers,
        flds=[
            'EQY_TURNOVER_USD_REALTIME' 
        ],
        VWAP_START_TIME=start_date,
        VWAP_END_TIME=end_date,
    )




def parse_dates_from_filename(filename, safe_ticker):
    """
    Extrait start_date et end_date (format YYYYMMDD) du nom du fichier.
    Exemple: micro_AAPL_US_Sdate_'20250101'_Edate_'20260101'.xlsx
    """
    pattern = rf"^micro_{safe_ticker}_Sdate_'(\d{{8}})'_Edate_'(\d{{8}})'\.xlsx$"
    match = re.match(pattern, filename)
    if match:
        s_str, e_str = match.groups()
        return pd.to_datetime(s_str, format="%Y%m%d"), pd.to_datetime(e_str, format="%Y%m%d"), s_str, e_str
    return None, None, None, None


def data_micro(tickers, end_date=None, start_date = None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if start_date is None:
        start_date = (pd.to_datetime(end_date, format = "%Y%m%d") - pd.Timedelta(years = 5)).strftime("%Y-%m-%d")


    if isinstance(tickers, str):
        tickers = [tickers]

    req_end_dt = pd.to_datetime(end_date)
    req_start_dt = pd.to_datetime(start_date)
    
    req_end_str = req_end_dt.strftime('%Y%m%d')
    req_start_str = req_start_dt.strftime('%Y%m%d')

    repertoir_projet = Path(__file__).resolve().parent
    data_dir = repertoir_projet / "DATA" / "Micro"

    fields = [
        'PX_LAST',
        'PX_VOLUME',
        'YTM_AVG',
        'VOLATILITY_30D',
        '1M_IMPLIED_VOLATILITY'
    ]   

    results = {}

    for ticker in tickers:
        safe_ticker = ticker.replace(" ", "_").replace("/", "_")
        print(f"\n--- Traitement {safe_ticker} [Demande: {req_start_str} -> {req_end_str}] ---")

        # 1. Inspecter tous les fichiers existants pour ce ticker
        matching_files = []
        for file_path in data_dir.glob(f"micro_{safe_ticker}_Sdate_*_Edate_*.xlsx"):
            f_start_dt, f_end_dt , f_s_str, f_e_str = parse_dates_from_filename(file_path.name, safe_ticker)
            if f_start_dt is not None:
                # Vérifie s'il y a un chevauchement ou une contiguïté avec la plage demandée
                if not (f_end_dt < req_start_dt or f_start_dt > req_end_dt):
                    matching_files.append({
                        'path': file_path,
                        'start_dt': f_start_dt,
                        'end_dt': f_end_dt
                    })

        dfs_to_combine = []
        files_to_delete = []

        # 2. Charger les fichiers chevauchants existants
        if matching_files:
            print(f" - {len(matching_files)} fichier(s) chevauchant(s) trouvé(s) localement.")
            for item in matching_files:
                df_old = pd.read_excel(item['path'], index_col=0, parse_dates=True)
                dfs_to_combine.append(df_old)
                files_to_delete.append(item['path'])

            # Plage globale couverte par les fichiers locaux
            min_local_start = min(m['start_dt'] for m in matching_files)
            max_local_end = max(m['end_dt'] for m in matching_files)

            # Calcul du nouvel intervalle global [min(x, a), max(y, b)]
            final_start_dt = min(req_start_dt, min_local_start)
            final_end_dt = max(req_end_dt, max_local_end)
        else:
            print(" - Aucun fichier local d'historique compatible.")
            final_start_dt = req_start_dt
            final_end_dt = req_end_dt

        # 3. Récupérer uniquement les trous de données via Bloomberg (si besoin)
        # S'il n'y avait pas de fichiers locaux, on télécharge tout [req_start, req_end]
        if not matching_files:
            fetch_ranges = [(req_start_dt, req_end_dt)]
        else:
            fetch_ranges = []
            # Trou avant le début des données locales
            if req_start_dt < min_local_start:
                fetch_ranges.append((req_start_dt, min_local_start - pd.Timedelta(days=1)))
            # Trou après la fin des données locales
            if req_end_dt > max_local_end:
                fetch_ranges.append((max_local_end + pd.Timedelta(days=1), req_end_dt))

        for f_start, f_end in fetch_ranges:
            if f_start <= f_end:
                s_str = f_start.strftime('%Y%m%d')
                e_str = f_end.strftime('%Y%m%d')
                print(f" - Requête Bloomberg pour les données manquantes : {s_str} -> {e_str}")
                
                df_new = blp.bdh(
                    securities=ticker,
                    flds=fields,
                    start_date=s_str,
                    end_date=e_str
                )

                if not df_new.empty:
                    if isinstance(df_new.columns, pd.MultiIndex):
                        df_new = df_new.droplevel(0, axis=1)
                    dfs_to_combine.append(df_new)

        # 4. Fusionner, dédoublonner et sauvegarder
        if dfs_to_combine:
            df_final = pd.concat(dfs_to_combine)
            # Dédoublonnage sur les dates (index)
            df_final = df_final[~df_final.index.duplicated(keep='first')].sort_index()

            # Mettre à jour les dates effectives du fichier final
            actual_start_str = df_final.index.min().strftime('%Y%m%d')
            actual_end_str = df_final.index.max().strftime('%Y%m%d')

            new_filename = f"micro_{safe_ticker}_Sdate_'{actual_start_str}'_Edate_'{actual_end_str}'.xlsx"
            new_file_path = data_dir / new_filename

            # Enregistrer le nouveau fichier consolidé
            df_final.to_excel(new_file_path)
            print(f" - Nouveau fichier créé : {new_filename}")

            # Supprimer les anciens fichiers combinés
            for file_to_del in files_to_delete:
                if file_to_del != new_file_path and file_to_del.exists():
                    file_to_del.unlink()
                    print(f" - Ancien fichier supprimé : {file_to_del.name}")

            results[ticker] = df_final
        else:
            print(" - Aucune donnée disponible.")
            results[ticker] = pd.DataFrame()

    return results if len(tickers) > 1 else results[tickers[0]]


print(membres_index("WORLD Index",'2026-10-09').head(10))