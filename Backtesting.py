import pandas as pd
from datetime import datetime
from colored import fg,attr
from colorama import Fore
from datetime import timedelta
from dateutil.relativedelta import relativedelta, MO
from alive_progress import alive_bar
from about_time import about_time
from unittest.mock import patch
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib as mpl
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle
from timeit import timeit
import re
import json
import sys
import openpyxl
import time
import tkinter as tk
import os 
import textwrap

# Obtenir le répertoire du script ou de l'exécutable
base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

# Construir les chemins vers les fichiers
BDD = os.path.join(base_dir, 'historique.xlsx')
Resultats_excel = os.path.join(base_dir, 'Résultats.xlsx')
json_file = os.path.join(base_dir, 'Setup.json')
log_file = os.path.join(base_dir, 'Logs.txt')

dates = []
prices = []
periodes_rappel = []
periodes_coupon = []

# Récupère les variables dans le .json et les converties en %
with open(json_file) as f:
    data = json.load(f)

degressivite = float(data['degressivite']) / 100.0
floor = float(data['floor']) / 100.0
NC = data['NC']
barriere_autocall = float(data['barriere_autocall']) / 100.0
maturite = data['maturite']
frequence = data['frequence']
start_periode = data['start_periode']
phoenix_memoire = data['phoenix_memoire']
airbag = float(data['airbag']) / 100.0
PDI = float(data['PDI']) / 100.0
barriere_coupon = float(data['barriere_coupon']) / 100.0



# FONCTION POUR RECUPERER LE SJ EN FONCTION DU RIC
def sous_jacent():

    print("\nOuverture du fichier excel historique..")
    # Charger le fichier Excel
    df = pd.read_excel(BDD, sheet_name="BDD_BT")

    # Demander à l'utilisateur d'entrer le Ric
    global ric_input
    ric_input = input("\nEntrez le Ric : ")

    row = 0
    i=0
    # Cherche le Ric dans BBDSJ
    for col in range(5, len(df.columns), 3):
        if ric_input == df.iloc[row, col]:
            print("Le RIC {} se trouve à la colonne {}.".format(ric_input, col+1))
            break

    row = 3

    # Récupère les dates & prix du SJ
    for ligne in df.iloc[:,col-1]:
        while ligne is not None :
            date = df.iloc[row, col-2]
            if not pd.isna(date):
                #date = date.strftime('%d-%m-%Y')
                price = df.iloc[row, col-1]
                row += 1
                dates.append(date)
                prices.append(price)
                print("{} {}".format(date, price))
            else:
                break
    return dates, prices
    


# FONCTION EXCEL
def excel():
    # Ouvrir le fichier Excel
    wb = openpyxl.load_workbook(Resultats_excel)
    resultats_worksheet = wb.active

    # Supprimer les données des colonnes A et B à partir de la deuxième ligne
    resultats_worksheet.delete_rows(2, resultats_worksheet.max_row)

    # Créer un DataFrame avec les résultats
    resultats = pd.DataFrame(columns=['Période', 'Nombre de rappels'])
    for i in range(observation):
        nb_rappel_periode_i = periodes_rappel.count(i+1)
        resultats = pd.concat([resultats, pd.DataFrame({'Période': [i+1], 'Nombre de rappels': [nb_rappel_periode_i]})], ignore_index=True)

    # Ajouter les périodes sans rappel avec le nombre 0
    for i in range(1, observation+1):
        if not any(resultats['Période'] == i):
           resultats = pd.concat([resultats, pd.DataFrame({'Période': [i], 'Nombre de rappels': [0]})], ignore_index=True)

    # Trier le DataFrame par ordre de période
    resultats = resultats.sort_values(by='Période')

    # Exporter les résultats dans un fichier Excel
    with pd.ExcelWriter(Resultats_excel) as writer:
        resultats.to_excel(writer, index=False)

        # Ajouter les informations supplémentaires dans le fichier Excel
        worksheet = writer.book.active
        worksheet['D5'] = "Isin du SJ :"
        worksheet['E5'] = ric_input
        worksheet['D6'] = "Date dé début de la simulation :"
        worksheet['E6'] = strike_date1.strftime("%d/%m/%Y")
        worksheet['D7'] = "Nombres de simulations :"
        worksheet['E7'] = compteur_simulation
        worksheet['D8'] = "Coupons à maturité :"
        worksheet['E8'] = rappel_maturite
        worksheet['D9'] = "Perte en capital à maturité :"
        worksheet['E9'] = nb_perte
        worksheet['D10'] = "Capital protégé à maturité"
        worksheet['E10'] = nb_capitalprotege
        worksheet['D11'] = "Probabilités de perte en capital"
        worksheet['E11'] = proba_perte
        worksheet['D12'] = "Probabilités de rappel totale :"
        worksheet['E12'] = proba_rappel_total
        worksheet['D13'] = "Probabilités de protection par le PDI :"
        worksheet['E13'] = proba_pdi
        if choix == 2:
            worksheet['D14'] = "Nombre de coupons total versés :"
            worksheet['E14'] = coupon

    print(fg(26) +"\n[STATUT] : Résultats excel chargés !\n"+ Fore.RESET)


##### FONCTION GRAPHIQUE #####
def graphique():
    # Modifier la police pour toute la figure
    mpl.rcParams['font.family'] = 'Arial'

    plt.style.use('ggplot')

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.suptitle("Backtesting i-Kapital", fontsize=16, fontweight='bold', color=(0.12, 0.46, 0.70), y=0.96)
    gs = gridspec.GridSpec(3, 3, height_ratios=[0.75, 0.60, 1])  # Modifiez les ratios de hauteur
    ax0 = plt.subplot(gs[0, :])
    ax1 = plt.subplot(gs[2, 0])
    ax2 = plt.subplot(gs[2, 1])
    ax_table = plt.subplot(gs[2, 2])
    ax4 = plt.subplot(gs[1, :])
 

    # HISTOGRAMME DE RAPPEL PAR DATE D'OBSERVATION
    periodes, counts = np.unique(periodes_rappel, return_counts=True)
    ax0.bar(periodes, counts, color=(0.12, 0.46, 0.70), edgecolor='white', linewidth=0.25)
    ax0.set_title("Rappel par date d'observation", fontweight='bold', fontsize=10)
    ax0.set_xlabel("Date d'observations")
    ax0.set_ylabel("Nombre de rappels")
    ax0.set_aspect('auto')
    ax0.tick_params(axis='x', labelcolor=(0.12, 0.46, 0.70), labelsize=10)
    ax0.tick_params(axis='y', labelcolor=(0.12, 0.46, 0.70), labelsize=10)
    
    # Gère le pas de l'axe des abscisses en fonction de la maturité
    if maturite > 5:
        ax0.set_xticks(np.arange(min(periodes), max(periodes) + 1, step=4))  # Utiliser des graduations entières
        ax0.set_xticklabels(np.arange(min(periodes), max(periodes) + 1, step=4))  # Appliquer les graduations entières et ajuster la rotation des étiquettes
    else:
        ax0.set_xticks(np.arange(min(periodes), max(periodes) + 1, step=1))  # Utiliser des graduations entières
        ax0.set_xticklabels(np.arange(min(periodes), max(periodes) + 1, step=1))  # Appliquer les graduations entières et ajuster la rotation des étiquettes

    # TABLEAU RECAP
    if choix == "1":
        structure = "Autocall"
    elif choix == "2":
        structure = "Phoenix"

    if bonus == "1":
        specificite = "Airbag"
    elif bonus == "2":
        specificite = "Dégressif"
    elif bonus == "3":
        specificite = "Vanille"

    if frequence == 360:
        freq = "Quotidienne"
        fq = "jour"
    elif frequence == 12:
        freq = "Mensuelle"
        fq = "mois"
    elif frequence == 4:
        freq = "Trimestrielle"
        fq = "trim"
    elif frequence == 2:
        freq = "Semestrielle"
        fq = "sem"
    elif frequence == 1:
        freq = "Annuelle"
        fq = "année"

    # Convertir la date au format souhaité
    formatted_date = strike_date1.strftime("%d/%m/%Y")
    if bonus == "1" :
        table_data = [["Type", structure],["Maturité", str(maturite) + " ans"], ["Sous-Jacent", ric_input],["Fréquence", freq], ["Barrière de protection", str(PDI*100) + "%"],["Début de simulation", formatted_date],["Nb de simulations", compteur_simulation], ["Airbag à Maturité", str(100*airbag) + "%"]]
    elif bonus == "2":
        table_data = [["Type", structure],["Maturité", str(maturite) + " ans"], ["Sous-Jacent", ric_input],["Fréquence", freq], ["Barrière de protection", str(PDI*100) + "%"],["Début de simulation", formatted_date],["Nb de simulations", compteur_simulation], ["Dégréssivité", "-" + str(100*degressivite) + "%" + "/" + fq]]
    else:
        table_data = [["Type", structure],["Maturité", str(maturite) + " ans"], ["Sous-Jacent", ric_input],["Fréquence", freq], ["Barrière de protection", str(PDI*100) + "%"],["Début de simulation", formatted_date],["Nb de simulations", compteur_simulation]]
   
    # Créer le tableau avec les données de table_data
    table = ax_table.table(cellText=table_data, cellLoc='center', loc='center')
    ax_table.set_title('Détails de la structure :', fontweight='bold', fontsize=10, y=0.78)

    # Personnaliser l'apparence du tableau
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.auto_set_column_width(col=list(range(len(table_data[0]))))
    

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('#1f77b4')
            cell.set_text_props(va='center')
        elif row % 2 == 0:
            cell.set_facecolor('#f7f7f7')
        else:
            cell.set_facecolor('#ebebeb')

    # Désactiver les axes et le cadre pour l'axe ax_table
    ax_table.set_axis_off()

    # Ajuster l'espacement des cellules en modifiant la hauteur et la largeur des cellules
    table.scale(1.25, 1.25)

    # ajuster les sous-graphiques pour qu'ils soient bien espacés
    fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.5, hspace=0.1)

    # DIAGRAMME TAUX RAPPEL PREMIERE OBSERVATION
    first_observation_rappel = counts[0] / compteur_simulation * 100
    palette = plt.get_cmap('Blues')
    values_new = [first_observation_rappel, 100 - first_observation_rappel]
    color_cycle = [palette(1. * (i + 0.3) / len(values_new)) if i == 0 else palette(1. * i / len(values_new)) for i in range(len(values_new))]
    wedges_new, _ = ax1.pie(values_new, colors=color_cycle, wedgeprops=dict(edgecolor='black', linewidth=1))  # Retirer autopct et autotexts
    ax1.axis('equal')  # Pour que le diagramme soit un cercle parfait
    ax1.set_title('Taux rappel 1ère obs :', fontweight='bold', fontsize=10, y=0.78)


    # Ajouter une légende pour le premier diagramme circulaire en dessous du diagramme
    legende_premier_diagramme = f"Rappel première observation: {first_observation_rappel:.1f}%"
    ax1.legend([legende_premier_diagramme], loc='upper center', bbox_to_anchor=(0.5, 0.15), fontsize='x-small')

   # DIAGRAMME DE PROBABILITE GENERALES
    if rappel_maturite > 0 or nb_perte > 0 or nb_capitalprotege > 0:
        values = [rappel_total, nb_perte, nb_capitalprotege]
        percentages = [value / sum(values) * 100 for value in values]
        labels = [f"Rappel total: {round(values[0])} ({round(percentages[0], 2)}%)",
        f"Perte en capital: {round(values[1])} ({round(percentages[1], 2)}%)",
        f"Capital protégé: {round(values[2])} ({round(percentages[2], 2)}%)"]
        palette = plt.get_cmap('Blues')
        color_cycle = [palette(1. * (i + 0.3) / len(values)) if i == 0 else palette(1. * i / len(values)) for i in range(len(values))]

        wedges, _ = ax2.pie(values, colors=color_cycle, wedgeprops=dict(edgecolor='black', linewidth=1))  # Retirer autopct et autotexts

        # Ajouter les légendes en dessous du deuxième diagramme circulaire
        ax2.legend(wedges, labels, loc='upper center', bbox_to_anchor=(0.5, -0.02), fontsize='x-small')
        ax2.set_title('Probabilités générales', fontweight='bold', fontsize=10, y=1.08)
    else:
        ax2.set_title('Pas de scénarios à maturité', fontweight='bold', fontsize=10)
        ax2.set_axis_off()  # Désactiver les axes et le cadre

    # HISTOGRAMME PROBA CUMULEE
    annees = [i+1 for i in range(maturite)]
    # Création du graphique
    ax4.bar(annees, p_rappel_annee, color=(0.12, 0.46, 0.70), width=0.35, edgecolor='white', linewidth=1)
    # Configuration du graphique
    ax4.set_xlabel('Probabilité de rappels cumulés par années (%)')
    ax4.set_ylabel('Pourcentages')
    ax4.set_ylim(0, 100)
    ax4.set_xlim(0, maturite+1)
    ax4.xaxis.grid(True)  # Affiche la grille horizontalement
    ax4.yaxis.grid(True)  # Affiche la grille verticalement
    ax4.set_xticks(annees)
    ax4.set_xticklabels(annees)
    ax4.tick_params(axis='x', labelcolor=(0.12, 0.46, 0.70), labelsize=10)
    ax4.tick_params(axis='y', labelcolor=(0.12, 0.46, 0.70), labelsize=10)


 
    # Ajout des pourcentages au dessus de chaque barre
    for i, v in enumerate(p_rappel_annee):
        ax4.text(i + 1 - 0.1, v + 1, str(int(round(v))) + "%", color=(0.12, 0.46, 0.70), fontweight='bold', fontsize=9)

    # Ajouter un axe de texte pour le disclaimer
    disclaimer_text = "Disclaimer : Les données du backtesting présentées dans ce fichier sont fournies à titre indicatif uniquement et ne constituent en aucun cas une garantie ou une promesse de performance future des produits structurés ou des sous-jacents concernés. Les résultats obtenus lors du backtesting sont basés sur des données historiques et des hypothèses qui pourraient ne pas être représentatives des conditions réelles de marché ou des fluctuations futures des sous-jacents. En utilisant ces données, vous reconnaissez et acceptez que ni l'auteur du fichier, ni les partenaires associés, ne pourront être tenus responsables de toute décision d'investissement ou de perte financière résultant de l'utilisation ou de la confiance accordée aux informations de backtesting fournies."
    disclaimer_ax = fig.add_axes([0, 0, 1, 0.1], frame_on=False)  # Changer la position et la taille de l'axe si nécessaire
    disclaimer_ax.text(0.01, 0.5, disclaimer_text, fontsize=8, ha='left', va='center', wrap=True, style='italic')
    disclaimer_ax.set_axis_off()  # Désactiver les axes et le cadre
	
    fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.5, hspace=0.40)
    
    
    # Obtenir le chemin du répertoire où se trouve le script/exécutable
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.realpath(__file__))

    # Créer le sous-dossier pour les fichiers PDF exportés
    pdf_folder = os.path.join(script_dir, "pdf_exports")
    os.makedirs(pdf_folder, exist_ok=True)

    # Choisir le chemin pour sauvegarder le fichier PDF
    nom_fichier = os.path.join(pdf_folder, f"Backtesting - {ric_input} - {structure} - {specificite} - {freq} - {maturite} ans.pdf")

    # créer un objet PDF / ajouter la figure au PDF / fermer l'objet PDF
    pdf_pages = PdfPages(nom_fichier)
    pdf_pages.savefig(fig)
    pdf_pages.close()
    print(fg(26) +"\n[STATUT] : PDF Exporté avec succès !\n"+ Fore.RESET)



##### FONCTION AUTOCALL + AUTOCALL AIRBAG #####
def calculs_autocall(dates, prices):
    sys.stdout = open(log_file, 'w')

    #récupére la dernière date et lui soustrait la maturité convertie en année + ajoute une marge de 10j
    derniere_date = dates[-1] - relativedelta(years=maturite)
    last_launch = derniere_date - relativedelta(days=10)
    print(last_launch)

    global observation
    observation = frequence * maturite
    global j 
    i = 0
    j = 1
    
    global compteur_simulation
    global nb_rappel
    global rappel_maturite
    global nb_perte
    global proba_perte
    global nb_capitalprotege
    global compteur_matu
    global rappel_total
    global proba_rappel_total
    global proba_pdi

    compteur_simulation = 0
    nb_rappel = 0
    rappel_maturite = 0
    nb_perte = 0
    proba_perte = 0
    nb_capitalprotege = 0
    compteur_matu = 0
    perte_totale = 0
    rappel_total = 0
    proba_rappel_total = 0
    periodes_rappel_annee = []


    # Récupération du nombre total de simulation et initiations des variables
    for i, date in enumerate(dates):
        if date.date() <= last_launch.date():
            print("\n\nSimulation : ", i+1 )
            compteur_simulation = compteur_simulation +1
            strike_price = prices[i]
            print("strike price : ", strike_price)
            strike_date = date
            if i == 0:
                global strike_date1
                strike_date1 = date
                
            prix_rappel = barriere_autocall * strike_price
            global date_observation
            date_observation = strike_date 
            
            date_nc = strike_date + relativedelta(months=NC)      
   
            print("Date de strike :", strike_date)

            # Boucle individuelle pour chaque simulation
            
            for j in range(observation) : 

                # Etablis la nouvelle date d'observation exacte dans le calendrier    
                if frequence == 1:
                    date_observation = strike_date + relativedelta(years=j+1)
                elif frequence == 2:
                    date_observation = strike_date + relativedelta(months=((j+1)*6))
                elif frequence == 4:
                    date_observation = strike_date + relativedelta(months=((j+1)*3))
                elif frequence == 12:
                    date_observation = strike_date + relativedelta(months=j+1)
                elif frequence == 360:
                    date_observation = strike_date + relativedelta(days=j+1)
                    
                if j == 0:
                    print("Last launch :", last_launch)

                if date_observation >= date_nc:
                    print("date d'observation n°",j+1)

                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si le produit est rappelé
                    if price_observation >= prix_rappel and j+1 < observation :
                        nb_rappel = nb_rappel + 1
                        periodes_rappel.append(j+1)
                        periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                        print("Produit rappelé car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                        break
                    elif price_observation < prix_rappel and j+1 < observation :
                        print("Produit NON rappelé car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                    # Scénario Maturité
                    if j+1 == observation :

                        compteur_matu = compteur_matu + 1
                        prix_pdi = PDI * strike_price

                        # Avec Airbag
                        if bonus == "1":
                
                            prix_airbag = airbag * strike_price
                            if price_observation >= prix_airbag :
                                rappel_maturite = rappel_maturite + 1
                                periodes_rappel.append(j+1)
                                periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                                print("Produit rappelé à maturité car le prix {} est superieur à son airbag {}" .format(price_observation, prix_airbag))
                            
                            elif price_observation > prix_pdi:
                                nb_capitalprotege = nb_capitalprotege + 1
                                print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau d'airbag {}" .format(price_observation, prix_airbag))
                            
                            elif price_observation < prix_pdi:
                                nb_perte = nb_perte + 1
                                print("Perte en capital")

                        # Sans Airbag
                        elif bonus == "3":
                         
                            if price_observation >= prix_rappel :
                                rappel_maturite = rappel_maturite + 1
                                periodes_rappel.append(j+1)
                                periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                                print("Produit rappelé à maturité car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                                
                            elif price_observation > prix_pdi and price_observation < prix_rappel:
                                nb_capitalprotege = nb_capitalprotege + 1
                                print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                            elif price_observation < prix_pdi:
                                nb_perte = nb_perte + 1
                                montant_perte = (price_observation / prix_rappel -1) *100
                                perte_totale = perte_totale + montant_perte 
                                print("Perte en capital")
    sys.stdout.close()
    sys.stdout = sys.__stdout__

    # Calcul de la probabilité de rappel cumulée par année
    global p_rappel_annee
    p_rappel_annee = [0] * maturite
    print(fg(26) + "\n[Détails]" + Fore.RESET)
    for i in range(maturite):
        p_rappel_annee[i] = periodes_rappel_annee.count(i) / compteur_simulation * 100
        if i > 0:
            p_rappel_annee[i] += p_rappel_annee[i-1]
        print("Probabilité de rappel cumulée année {} : {:.2f}%".format(i+1, p_rappel_annee[i]))


    rappel_total = nb_rappel + rappel_maturite
    proba_rappel_total = rappel_total / compteur_simulation * 100
    proba_perte = nb_perte / compteur_simulation * 100
    proba_pdi = nb_capitalprotege / compteur_simulation * 100  
    print("\nNombre de simulations : {}".format(compteur_simulation))
    print("Nombre de rappel anticipé : {}".format(nb_rappel))
    print(fg(26) + "\n[Scénarios à maturité]" + Fore.RESET)    
    print("Nombre de scénarios à maturité : ", compteur_matu)
    print("Nombre de rappels à maturité : {}".format(rappel_maturite))
    print("Nombre de pertes en capital : {}".format(nb_perte))
    print("Nombre capital protege par le pdi : {}".format(nb_capitalprotege))
    print(fg(26) + "\n[Probabilités générales]" + Fore.RESET)
    print("Probabilités de perte en capital : {:.2f}%".format(proba_perte))
    print("Probabilités de rappel totale : {:.2f}%".format(proba_rappel_total))
    print("Probabilités de protection par le PDI : {:.2f}%".format(proba_pdi))

##### FONCTION AUTOCALL DEGRESSIF ##### 
def autocall_degressif(dates, prices):
    sys.stdout = open(log_file, 'w')

    #récupére la dernière date et lui soustrait la maturité convertie en année
    derniere_date = dates[-1] - relativedelta(years=maturite)
    last_launch = derniere_date - relativedelta(days=10)
    print(last_launch)
    global observation
    observation = frequence * maturite
    i = 0
    j = 1
    global compteur_simulation
    global nb_rappel
    global rappel_maturite
    global nb_perte
    global proba_perte 
    global nb_capitalprotege
    global compteur_matu
    global rappel_total
    global proba_rappel_total 
    global proba_pdi

    compteur_simulation = 0
    nb_rappel = 0
    rappel_maturite = 0
    nb_perte = 0
    proba_perte = 0
    nb_capitalprotege = 0
    compteur_matu = 0
    perte_totale = 0
    rappel_total = 0
    proba_rappel_total = 0
    periodes_rappel_annee = []

    # Récupération du nombre total de simulation et initiations des variables
    for i, date in enumerate(dates):
        if date.date() <= last_launch.date():
            print("\n\nSimulation : ", i+1 )
            compteur_simulation = compteur_simulation +1
            strike_price = prices[i]
            strike_date = date
            if i == 0:
                global strike_date1
                strike_date1 = strike_date
            barriere_atc = barriere_autocall
            date_observation = strike_date 
            date_nc = strike_date + relativedelta(months=NC)      
            print("Date de strike {} & Prix de Strike {}".format(strike_date, strike_price))
            prix_rappel = barriere_autocall * strike_price

            # Boucle individuelle pour chaque simulation
            for j in range(observation) : 

                # Module de Dégréssivité
                if j+1 >= start_periode:
                    barriere_atc = barriere_atc - degressivite
                    prix_rappel = barriere_atc * strike_price
                    print("Nouveau prix de rappel : ", prix_rappel)

                    # Variable floor
                    prix_floor = floor * strike_price
                    if prix_rappel < prix_floor:
                        prix_rappel = prix_floor
                        print("Le prix à été flooré !", prix_rappel)
            
                                  
                # Etablis la nouvelle date d'observation exacte dans le calendrier
                if frequence == 1:
                    date_observation = strike_date + relativedelta(years=j+1)
                elif frequence == 2:
                    date_observation = strike_date + relativedelta(months=((j+1)*6))
                elif frequence == 4:
                    date_observation = strike_date + relativedelta(months=((j+1)*3))
                elif frequence == 12:
                    date_observation = strike_date + relativedelta(months=j+1)
                elif frequence == 360:
                    date_observation = strike_date + relativedelta(days=j+1)    
                    
                if j == 0:
                    print("Last launch :", last_launch)

                if date_observation >= date_nc:
                    print("date d'observation n°",j+1)
                    
                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si le produit est rappelé & ajoute la date d'observation dans la liste periode_rappel
                    if price_observation >= prix_rappel and j+1 < observation:
                        nb_rappel = nb_rappel + 1
                        periodes_rappel.append(j+1)
                        periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                        print("Produit rappelé car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                        break
                    elif price_observation < prix_rappel and j+1 < observation :
                        print("Produit NON rappelé car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                    # Scénario Maturité
                    if j+1 == observation :
                        compteur_matu = compteur_matu + 1
                        prix_pdi = PDI * strike_price

                        if price_observation >= prix_rappel :
                            rappel_maturite = rappel_maturite + 1
                            periodes_rappel.append(j+1)
                            periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                            print("Produit rappelé à maturité car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                        elif price_observation > prix_pdi and price_observation < prix_rappel:
                            nb_capitalprotege = nb_capitalprotege + 1
                            print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                            
                        elif price_observation < prix_pdi:
                            nb_perte = nb_perte + 1
                            montant_perte = (price_observation / prix_rappel -1) *100
                            perte_totale = perte_totale + montant_perte 
                            print("Perte en capital car le prix est inférieur au PDI :", prix_pdi)


    sys.stdout.close()
    sys.stdout = sys.__stdout__

    # Calcul de la probabilité de rappel cumulée par année
    global p_rappel_annee
    p_rappel_annee = [0] * maturite
    print(fg(26) + "\n[Détails]" + Fore.RESET)
    for i in range(maturite):
        p_rappel_annee[i] = periodes_rappel_annee.count(i) / compteur_simulation * 100
        if i > 0:
            p_rappel_annee[i] += p_rappel_annee[i-1]
        print("Probabilité de rappel cumulée année {} : {:.2f}%".format(i+1, p_rappel_annee[i]))


    rappel_total = nb_rappel + rappel_maturite
    proba_rappel_total = rappel_total / compteur_simulation * 100
    proba_perte = nb_perte / compteur_simulation * 100
    proba_pdi = nb_capitalprotege / compteur_simulation * 100  
    print("\nNombre de simulations : {}".format(compteur_simulation))
    print("Nombre de rappel anticipé : {}".format(nb_rappel))
    print(fg(26) + "\n[Scénarios à maturité]" + Fore.RESET)    
    print("Nombre de scénarios à maturité : ", compteur_matu)
    print("Nombre de rappels à maturité : {}".format(rappel_maturite))
    print("Nombre de pertes en capital : {}".format(nb_perte))
    print("Nombre capital protege par le pdi : {}".format(nb_capitalprotege))
    print(fg(26) + "\n[Probabilités générales]" + Fore.RESET)
    print("Probabilités de perte en capital : {:.2f}%".format(proba_perte))
    print("Probabilités de rappel totale : {:.2f}%".format(proba_rappel_total))
    print("Probabilités de protection par le PDI : {:.2f}%".format(proba_pdi))
    

##### FONCTION PHOENIX + PM VANILLE & AIRBAG #####
def phoenix(dates, prices):
    sys.stdout = open(log_file, 'w')

    #récupére la dernière date et lui soustrait la maturité convertie en année
    derniere_date = dates[-1] - relativedelta(years=maturite)
    last_launch = derniere_date - relativedelta(days=10)
    print(last_launch)

    global observation
    observation = frequence * maturite
    i = 0
    j = 1
    memoire = 0
    
    global compteur_simulation
    global nb_rappel
    global rappel_maturite
    global nb_perte
    global proba_perte
    global nb_capitalprotege
    global compteur_matu
    global coupon
    global pourcentage_perte
    global rappel_total
    global proba_rappel_total 
    global proba_pdi

    compteur_simulation = 0
    nb_rappel = 0
    rappel_maturite = 0
    nb_perte = 0
    nb_capitalprotege = 0
    compteur_matu = 0
    perte_totale = 0
    proba_perte = 0
    coupon = 0
    pourcentage_perte = 0
    rappel_total = 0
    proba_rappel_total = 0
    periodes_rappel_annee = []

# Récupération du nombre total de simulation et initiations des variables
    for i, date in enumerate(dates):
        if date.date() <= last_launch.date():
            print("\n\nSimulation : ", i+1 )
            compteur_simulation = compteur_simulation +1
            strike_price = prices[i]
            strike_date = date
            if i == 0:
                global strike_date1
                strike_date1 = date
            
            prix_rappel = barriere_autocall * strike_price
            prix_coupon = barriere_coupon * strike_price
            global date_observation
            date_observation = strike_date 
            
            date_nc = strike_date + relativedelta(months=NC)      
   
            print("Date de strike :", strike_date)

            # Boucle individuelle pour chaque simulation
            for j in range(observation) : 

                # Etablis la nouvelle date d'observation exacte dans le calendrier1    
                if frequence == 1:
                    date_observation = strike_date + relativedelta(years=j+1)
                elif frequence == 2:
                    date_observation = strike_date + relativedelta(months=((j+1)*6))
                elif frequence == 4:
                    date_observation = strike_date + relativedelta(months=((j+1)*3))
                elif frequence == 12:
                    date_observation = strike_date + relativedelta(months=j+1)
                elif frequence == 360:
                    date_observation = strike_date + relativedelta(days=j+1)
                    
                if j == 0:
                    print("Last launch :", last_launch)

                # Gestion des versements de coupon avant NC
                if date_observation < date_nc:
                    print("\ndate d'observation n°",j+1)

                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si un coupon est versé pour les NON mémoires 
                    if phoenix_memoire == "non":
                        if price_observation >= prix_coupon and j+1 < observation :
                            coupon = coupon + 1
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                        elif price_observation < prix_coupon and j+1 < observation :
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                    
                    # Check si un coupon est versé pour les mémoires 
                    if phoenix_memoire == "oui":                    
                        if price_observation >= prix_coupon and j+1 < observation :
                            # ajouter les coupons mis en mémoire puis reset la memoire
                            coupon = coupon + 1 + memoire
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                            print("Nombre de coupon versé : ", (1+memoire))
                            memoire = 0 
                        elif price_observation < prix_coupon and j+1 < observation :
                            memoire = memoire + 1
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))

              
                # Boucle traditionelle après NC
                if date_observation >= date_nc:
                    print("\ndate d'observation n°",j+1)

                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si un coupon est versé pour les NON mémoires 
                    if phoenix_memoire == "non":
                        if price_observation >= prix_coupon and j+1 < observation :
                            coupon = coupon + 1
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                        elif price_observation < prix_coupon and j+1 < observation :
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                    
                    # Check si un coupon est versé pour les mémoires 
                    if phoenix_memoire == "oui":                    
                        if price_observation >= prix_coupon and j+1 < observation :
                            # ajouter les coupons mis en mémoire puis reset la memoire
                            coupon = coupon + 1 + memoire
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                            print("Nombre de coupon versé : ", (1+memoire))
                            memoire = 0 
                        elif price_observation < prix_coupon and j+1 < observation :
                            memoire = memoire + 1
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))

                    # Check si le produit est rappelé
                    if price_observation >= prix_rappel and j+1 < observation :
                        nb_rappel = nb_rappel + 1
                        periodes_rappel.append(j+1)
                        periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                        print("Produit rappelé car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                        break
                    elif price_observation < prix_rappel and j+1 < observation :
                        print("Produit NON rappelé car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))


                    # Scénario Maturité
                    if j+1 == observation :

                        compteur_matu = compteur_matu + 1
                        prix_pdi = PDI * strike_price

                        # Avec Airbag
                        if bonus == "1":
                
                            prix_airbag = airbag * strike_price
                            if price_observation >= prix_airbag :
                                rappel_maturite = rappel_maturite + 1
                                periodes_rappel.append(j+1)
                                periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                                print("Produit rappelé à maturité car le prix {} est superieur à son airbag {}" .format(price_observation, prix_airbag))
                            
                            elif price_observation > prix_pdi:
                                nb_capitalprotege = nb_capitalprotege + 1
                                print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau d'airbag {}" .format(price_observation, prix_airbag))
                            
                            elif price_observation < prix_pdi:
                                nb_perte = nb_perte + 1
                                print("Perte en capital")

                        # Sans Airbag
                        elif bonus == "3":
                         
                            if price_observation >= prix_rappel :
                                rappel_maturite = rappel_maturite + 1
                                periodes_rappel.append(j+1)
                                periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                                print("Produit rappelé à maturité car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                                
                            elif price_observation > prix_pdi and price_observation < prix_rappel:
                                nb_capitalprotege = nb_capitalprotege + 1
                                print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                            elif price_observation < prix_pdi:
                                nb_perte = nb_perte + 1
                                montant_perte = (price_observation / prix_rappel -1) *100
                                perte_totale = perte_totale + montant_perte 
                                print("Perte en capital")

    sys.stdout.close()
    sys.stdout = sys.__stdout__

    # Calcul de la probabilité de rappel cumulée par année
    global p_rappel_annee
    p_rappel_annee = [0] * maturite
    print(fg(26) + "\n[Détails]" + Fore.RESET)
    for i in range(maturite):
        p_rappel_annee[i] = periodes_rappel_annee.count(i) / compteur_simulation * 100
        if i > 0:
            p_rappel_annee[i] += p_rappel_annee[i-1]
        print("Probabilité de rappel cumulée année {} : {:.2f}%".format(i+1, p_rappel_annee[i]))


    rappel_total = nb_rappel + rappel_maturite
    proba_rappel_total = rappel_total / compteur_simulation * 100
    proba_perte = nb_perte / compteur_simulation * 100
    proba_pdi = nb_capitalprotege / compteur_simulation * 100  
    print("\nNombre de simulations : {}".format(compteur_simulation))
    print("Nombre de rappel anticipé : {}".format(nb_rappel))
    print(fg(26) + "\n[Scénarios à maturité]" + Fore.RESET)    
    print("Nombre de scénarios à maturité : ", compteur_matu)
    print("Nombre de rappels à maturité : {}".format(rappel_maturite))
    print("Nombre de pertes en capital : {}".format(nb_perte))
    print("Nombre capital protege par le pdi : {}".format(nb_capitalprotege))
    print(fg(26) + "\n[Probabilités générales]" + Fore.RESET)
    print("Probabilités de perte en capital : {:.2f}%".format(proba_perte))
    print("Probabilités de rappel totale : {:.2f}%".format(proba_rappel_total))
    print("Probabilités de protection par le PDI : {:.2f}%".format(proba_pdi))


##### FONCTION PHOENIX + PM DEGRESSIF #####
def phoenix_degressif(dates, prices):
    sys.stdout = open(log_file, 'w')

    #récupére la dernière date et lui soustrait la maturité convertie en année
    derniere_date = dates[-1] - relativedelta(years=maturite)
    last_launch = derniere_date - relativedelta(days=10)
    print(last_launch)

    global observation
    observation = frequence * maturite
    i = 0
    j = 1
    memoire = 0
    
    global compteur_simulation
    global nb_rappel
    global rappel_maturite
    global nb_perte
    global proba_perte
    global nb_capitalprotege
    global compteur_matu
    global coupon
    global pourcentage_perte
    global rappel_total
    global proba_rappel_total 
    global proba_pdi

    compteur_simulation = 0
    nb_rappel = 0
    rappel_maturite = 0
    nb_perte = 0
    proba_perte = 0
    nb_capitalprotege = 0
    compteur_matu = 0
    perte_totale = 0
    coupon = 0
    pourcentage_perte = 0
    rappel_total = 0
    proba_rappel_total = 0
    periodes_rappel_annee = []

# Récupération du nombre total de simulation et initiations des variables
    for i, date in enumerate(dates):
        if date.date() <= last_launch.date():
            print("\n\nSimulation : ", i+1 )
            compteur_simulation = compteur_simulation +1
            strike_price = prices[i]
            strike_date = date
            if i == 0:
                global strike_date1
                strike_date1 = date
            
            barriere_atc = barriere_autocall
            prix_rappel = barriere_autocall * strike_price
            prix_coupon = barriere_coupon * strike_price
            global date_observation
            date_observation = strike_date 
            
            date_nc = strike_date + relativedelta(months=NC)      
   
            print("Date de strike :", strike_date)

            # Boucle individuelle pour chaque simulation
            for j in range(observation) : 

                # Module de Dégréssivité
                if j+1 >= start_periode:
                    barriere_atc = barriere_atc - degressivite
                    prix_rappel = barriere_atc * strike_price
                    print("Nouveau prix de rappel : ", prix_rappel)

                    # Variable floor
                    prix_floor = floor * strike_price
                    if prix_rappel < prix_floor:
                        prix_rappel = prix_floor
                        print("Le prix à été flooré !", prix_rappel)

                # Etablis la nouvelle date d'observation exacte dans le calendrier1    
                if frequence == 1:
                    date_observation = strike_date + relativedelta(years=j+1)
                elif frequence == 2:
                    date_observation = strike_date + relativedelta(months=((j+1)*6))
                elif frequence == 4:
                    date_observation = strike_date + relativedelta(months=((j+1)*3))
                elif frequence == 12:
                    date_observation = strike_date + relativedelta(months=j+1)
                elif frequence == 360:
                    date_observation = strike_date + relativedelta(days=j+1)
                    
                if j == 0:
                    print("Last launch :", last_launch)

                # Gestion des versements de coupon avant NC
                if date_observation < date_nc:
                    print("\ndate d'observation n°",j+1)

                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si un coupon est versé pour les NON mémoires 
                    if phoenix_memoire == "non":
                        if price_observation >= prix_coupon and j+1 < observation :
                            coupon = coupon + 1
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                        elif price_observation < prix_coupon and j+1 < observation :
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                    
                    # Check si un coupon est versé pour les mémoires 
                    if phoenix_memoire == "oui":                    
                        if price_observation >= prix_coupon and j+1 < observation :
                            # ajouter les coupons mis en mémoire puis reset la memoire
                            coupon = coupon + 1 + memoire
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                            print("Nombre de coupon versé : ", (1+memoire))
                            memoire = 0 
                        elif price_observation < prix_coupon and j+1 < observation :
                            memoire = memoire + 1
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))

              
                # Boucle traditionelle après NC
                if date_observation >= date_nc:
                    print("\ndate d'observation n°",j+1)

                    # Récupère prochaine date si elle n'est pas dans la liste
                    for date2 in (dates):
                            if date2.date() == date_observation.date():
                                print("comparaison réussi, date2 = {} & date_obs = {}".format(date2, date_observation))
                                break
                            elif date2.date() > date_observation.date():
                                date_observation = date2
                                print("nouvelle date d'osbervation :", date_observation)
                                break
                    
                    # Récupère le prix correspondant à la date 
                    index = dates.index(date_observation)
                    price_observation = prices[index]

                    # Check si un coupon est versé pour les NON mémoires 
                    if phoenix_memoire == "non":
                        if price_observation >= prix_coupon and j+1 < observation :
                            coupon = coupon + 1
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                        elif price_observation < prix_coupon and j+1 < observation :
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                    
                    # Check si un coupon est versé pour les mémoires 
                    if phoenix_memoire == "oui":                    
                        if price_observation >= prix_coupon and j+1 < observation :
                            # ajouter les coupons mis en mémoire puis reset la memoire
                            coupon = coupon + 1 + memoire
                            print("Coupon versé car le prix {} est supèrieur à la barrière de coupon {}".format(price_observation, prix_coupon))
                            print("Nombre de coupon versé : ", (1+memoire))
                            memoire = 0 
                        elif price_observation < prix_coupon and j+1 < observation :
                            memoire = memoire + 1
                            print("Pas de coupon car le prix {} est inférieur à la barrière de coupon {}".format(price_observation, prix_coupon))

                    # Check si le produit est rappelé
                    if price_observation >= prix_rappel and j+1 < observation :
                        nb_rappel = nb_rappel + 1
                        periodes_rappel.append(j+1)
                        periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                        print("Produit rappelé car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                        break
                    elif price_observation < prix_rappel and j+1 < observation :
                        print("Produit NON rappelé car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))


                    # Scénario Maturité
                    if j+1 == observation :

                        compteur_matu = compteur_matu + 1
                        prix_pdi = PDI * strike_price
                         
                        if price_observation >= prix_rappel :
                            rappel_maturite = rappel_maturite + 1
                            periodes_rappel.append(j+1)
                            periodes_rappel_annee.append((j)//frequence) # Ajout de la période de rappel par année
                            print("Produit rappelé à maturité car le prix {} est superieur à son niveau de rappel {}" .format(price_observation, prix_rappel))
                            
                        elif price_observation > prix_pdi and price_observation < prix_rappel:
                            nb_capitalprotege = nb_capitalprotege + 1
                            print("Produit non rappelé à maturité mais protégé par le PDI car le prix {} est inférieur à son niveau de rappel {}" .format(price_observation, prix_rappel))

                        elif price_observation < prix_pdi:
                            nb_perte = nb_perte + 1
                            montant_perte = (price_observation / prix_rappel -1) *100
                            perte_totale = perte_totale + montant_perte 
                            print("Perte en capital")

    sys.stdout.close()
    sys.stdout = sys.__stdout__

    # Calcul de la probabilité de rappel cumulée par année
    global p_rappel_annee
    p_rappel_annee = [0] * maturite
    print(fg(26) + "\n[Détails]" + Fore.RESET)
    for i in range(maturite):
        p_rappel_annee[i] = periodes_rappel_annee.count(i) / compteur_simulation * 100
        if i > 0:
            p_rappel_annee[i] += p_rappel_annee[i-1]
        print("Probabilité de rappel cumulée année {} : {:.2f}%".format(i+1, p_rappel_annee[i]))




    rappel_total = nb_rappel + rappel_maturite
    proba_rappel_total = rappel_total / compteur_simulation * 100
    proba_perte = nb_perte / compteur_simulation * 100
    proba_pdi = nb_capitalprotege / compteur_simulation * 100  
    print("\nNombre de simulations : {}".format(compteur_simulation))
    print("Nombre de rappel anticipé : {}".format(nb_rappel))
    print(fg(26) + "\n[Scénarios à maturité]" + Fore.RESET)    
    print("Nombre de scénarios à maturité : ", compteur_matu)
    print("Nombre de rappels à maturité : {}".format(rappel_maturite))
    print("Nombre de pertes en capital : {}".format(nb_perte))

    print("Nombre capital protege par le pdi : {}".format(nb_capitalprotege))
    print(fg(26) + "\n[Probabilités générales]" + Fore.RESET)
    print("Probabilités de perte en capital : {:.2f}%".format(proba_perte))
    print("Probabilités de rappel totale : {:.2f}%".format(proba_rappel_total))
    print("Probabilités de protection par le PDI : {:.2f}%".format(proba_pdi))


def barre_de_chargement():
    with alive_bar(total=100) as bar:
        for i in range(100):
            # Effectuer votre traitement ici
            time.sleep(0.05)  # Simuler une tâche en cours
            
            bar()
            
# CLI
print("")
print(fg(26) +"██████╗  █████╗  ██████╗██╗  ██╗████████╗███████╗███████╗████████╗██╗███╗   ██╗ ██████╗ ")
print(fg(26) +"██╔══██╗██╔══██╗██╔════╝██║ ██╔╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██║████╗  ██║██╔════╝ ")
print(fg(26) +"██████╔╝███████║██║     █████╔╝    ██║   █████╗  ███████╗   ██║   ██║██╔██╗ ██║██║  ███╗")
print(fg(26) +"██╔══██╗██╔══██║██║     ██╔═██╗    ██║   ██╔══╝  ╚════██║   ██║   ██║██║╚██╗██║██║   ██║")
print(fg(26) +"██████╔╝██║  ██║╚██████╗██║  ██╗   ██║   ███████╗███████║   ██║   ██║██║ ╚████║╚██████╔╝")
print(fg(26) +"╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝ "+ Fore.RESET)
print("                                                    made with sharpness for "+ fg(26) +"i-Kapital®"+ Fore.RESET)


#MENU
while True:
    choix = input(fg(26) +"\n\n1/" + Fore.RESET + " Autocall" + fg(26) +"\n2/" + Fore.RESET + " Phoenix" + fg(26) + "\n3/" + Fore.RESET + " Quitter\n\n" + Fore.RESET)
                  
    # Traiter le choix de l'utilisateur

    # CHOIX 1 = AUTOCALL
    if choix == "1":
        while True:
            bonus = input(fg(26) +"\n1/" + Fore.RESET + " Airbag" + fg(26) +"\n2/" + Fore.RESET + " Dégréssif" + fg(26) +"\n3/" + Fore.RESET + " Pas de bonus" + fg(26) +"\n4/" + Fore.RESET + " Retourner au menu\n\n" + Fore.RESET)

            if bonus == "1":
                # variable airbag défini à l'intérieur de calculs_autocall
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                calculs_autocall(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print(" Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print(" Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="2":
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                autocall_degressif(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print(" Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print(" Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="3":
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                calculs_autocall(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print(" Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print(" Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="4":
                break
            else:
                print("Choix invalide. Veuillez réessayer.\n\n")
        print("\nMerci d'avoir utilisé le fichier" + fg(26) + " Backtest"+ Fore.RESET)
        print("Script réalisé par"+fg(26) + " A.R pour i-Kapital\n"+ Fore.RESET)
        time.sleep(1000000)
        break

    # CHOIX 2 = PHOENIX
    elif choix == "2":
        while True:
            bonus = input(fg(26) +"\n1/" + Fore.RESET + " Airbag" + fg(26) +"\n2/" + Fore.RESET + " Dégréssif" + fg(26) +"\n3/" + Fore.RESET + " Pas de bonus" + fg(26) +"\n4/" + Fore.RESET + " Retourner au menu\n\n" + Fore.RESET)

            if bonus =="1":
                # variable airbag défini à l'intérieur de calculs_autocall
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                phoenix(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print("Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print("Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="2":
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                phoenix_degressif(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print("Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print("Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="3":
                dates, prices = sous_jacent()
                print(fg(26) + "\n[STATUT] : Historique récupéré avec succès !\n" + Fore.RESET)
                print("Lancement des simulations..\n")
                phoenix(dates, prices)
                print(fg(26) + "\n[STATUT] : Simulation terminée. Vous pouvez vérifier les logs !\n" + Fore.RESET)
                print("Chargement du fichier excel..")
                barre_de_chargement()
                excel()
                print("Chargement du graphique..")
                barre_de_chargement()
                graphique()
                break
            elif bonus =="4":
                break
            else:
                print("Choix invalide. Veuillez réessayer.\n\n")
        print("\nMerci d'avoir utilisé le fichier" + fg(26) + " Backtest"+ Fore.RESET)
        print("Script réalisé par"+fg(26) + " A.R pour i-Kapital\n"+ Fore.RESET)
        time.sleep(1000000)
        break
            
    elif choix == "3":
        print("\nMerci d'avoir utilisé le fichier" + fg(26) + " Backtest"+ Fore.RESET)
        print("Script réalisé par"+fg(26) + " A.R pour i-Kapital\n"+ Fore.RESET)
        time.sleep(1)
        break
    else:
        print("Choix invalide. Veuillez réessayer.\n\n")
    

                                                                    
    
