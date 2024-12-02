import os
import re
from datetime import datetime
import pandas as pd
from typing import Dict, List

def extraire_informations(contenu: str) -> Dict:
    """Extrait les informations importantes du fichier de log"""
    info = {}
    
    # Extraction de la période
    periode_match = re.search(r'Loading data from (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) up to (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', contenu)
    if periode_match:
        info['debut'] = periode_match.group(1)
        info['fin'] = periode_match.group(2)
    
    # Extraction du profit total
    profit_match = re.search(r'Total profit %\s*\|\s*([-\d.]+)', contenu)
    if profit_match:
        info['profit_total'] = float(profit_match.group(1))
    
    # Extraction du nombre de trades
    trades_match = re.search(r'Total/Daily Avg Trades\s*\|\s*(\d+)\s*/\s*[\d.]+', contenu)
    if trades_match:
        info['nombre_trades'] = int(trades_match.group(1))
    
    # Extraction des balances min/max
    min_balance_match = re.search(r'Min balance\s*\|\s*([\d.]+)', contenu)
    max_balance_match = re.search(r'Max balance\s*\|\s*([\d.]+)', contenu)
    if min_balance_match and max_balance_match:
        info['min_balance'] = float(min_balance_match.group(1))
        info['max_balance'] = float(max_balance_match.group(1))
    
    # Extraction du meilleur et pire pair
    best_pair_match = re.search(r'Best Pair\s*\|\s*([A-Z]+/[A-Z]+)\s*([-\d.]+)', contenu)
    worst_pair_match = re.search(r'Worst Pair\s*\|\s*([A-Z]+/[A-Z]+)\s*([-\d.]+)', contenu)
    if best_pair_match and worst_pair_match:
        info['meilleur_pair'] = f"{best_pair_match.group(1)} ({best_pair_match.group(2)}%)"
        info['pire_pair'] = f"{worst_pair_match.group(1)} ({worst_pair_match.group(2)}%)"
    
    # Win rate
    win_rate_match = re.search(r'Win%.*?\|\s*([\d.]+)', contenu)
    if win_rate_match:
        info['win_rate'] = float(win_rate_match.group(1))
    
    # Debug: afficher les informations extraites
    print(f"Informations extraites: {info}")
    
    return info

def analyser_dossier_resultats(chemin_dossier: str) -> pd.DataFrame:
    """Analyse tous les fichiers de résultats dans le dossier spécifié"""
    resultats = []
    
    for fichier in os.listdir(chemin_dossier):
        if fichier.startswith('Test'):
            chemin_complet = os.path.join(chemin_dossier, fichier)
            try:
                with open(chemin_complet, 'r', encoding='utf-8') as f:
                    contenu = f.read()
                    info = extraire_informations(contenu)
                    # Vérifier si toutes les informations nécessaires sont présentes
                    required_keys = ['profit_total', 'win_rate', 'nombre_trades', 
                                   'min_balance', 'max_balance', 'meilleur_pair', 
                                   'pire_pair', 'debut', 'fin']
                    if all(key in info for key in required_keys):
                        info['nom_fichier'] = fichier
                        resultats.append(info)
                    else:
                        print(f"Fichier {fichier} incomplet - ignoré")
            except Exception as e:
                print(f"Erreur lors de la lecture du fichier {fichier}: {e}")
    
    if not resultats:
        print("Aucun résultat valide trouvé dans les fichiers")
        return pd.DataFrame()
    
    # Création du DataFrame
    df = pd.DataFrame(resultats)
    
    # Tri par profit total décroissant
    df = df.sort_values('profit_total', ascending=False)
    
    # Sélection du top 10
    df_top10 = df.head(10)
    
    # Réorganisation des colonnes
    colonnes = ['nom_fichier', 'profit_total', 'win_rate', 'nombre_trades',
                'min_balance', 'max_balance', 'meilleur_pair', 'pire_pair',
                'debut', 'fin']
    
    return df_top10[colonnes]

def main():
    # Chemin vers le dossier contenant les résultats
    chemin_resultats = "user_data/results"
    
    # Vérifier si le dossier existe
    if not os.path.exists(chemin_resultats):
        print(f"Le dossier {chemin_resultats} n'existe pas")
        return
    
    # Analyse des résultats
    resultats_df = analyser_dossier_resultats(chemin_resultats)
    
    if resultats_df.empty:
        return
        
    # Affichage des résultats
    print("\nTop 10 des meilleurs résultats de backtesting:")
    print("=" * 100)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(resultats_df.to_string(index=False))

if __name__ == "__main__":
    main()