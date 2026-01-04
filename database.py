# database.py - Modulo gestione dati v20.30 (Reports & Admin)
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_client():
    if "connections" in st.secrets and "gsheets_v2" in st.secrets["connections"]:
        secrets_dict = dict(st.secrets["connections"]["gsheets_v2"])
        creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    return None

def get_worksheet(sheet_name="Sheet1"): # Modificato per scegliere il foglio
    client = get_client()
    if client:
        try:
            url = st.secrets["connections"]["gsheets_v2"]["spreadsheet"]
            # Se il nome è "Segnalazioni", cerca quel tab specifico
            if sheet_name == "Segnalazioni":
                return client.open_by_url(url).worksheet("Segnalazioni")
            return client.open_by_url(url).sheet1
        except Exception as e:
            st.error(f"Errore DB ({sheet_name}): {e}")
            return None
    return None

def fetch_user_history(username):
    ws = get_worksheet()
    if not ws: return {}
    try:
        records = ws.get_all_records()
        history = {}
        target_user = username.strip().lower()
        for row in records:
            r_user = str(row.get('Utente', row.get('utente', ''))).strip().lower()
            if r_user == target_user:
                r_id = str(row.get('ID_Domanda', row.get('id_domanda', '')))
                r_esito = row.get('Esito', row.get('esito', 0))
                r_date = str(row.get('Timestamp', row.get('timestamp', '')))
                history[r_id] = {'score': int(r_esito), 'date': r_date}
        return history
    except Exception as e:
        st.error(f"Errore lettura storico: {e}")
        return {}

def upsert_answer(username, question_id, result):
    ws = get_worksheet()
    if not ws: return False
    unique_key = f"{username.strip().lower()}_{str(question_id).strip()}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cell = ws.find(unique_key, in_column=1)
        if cell:
            ws.update_cell(cell.row, 4, result)
            ws.update_cell(cell.row, 5, timestamp)
        else:
            ws.append_row([unique_key, username, str(question_id), result, timestamp])
        return True
    except Exception as e:
        print(f"Errore salvataggio: {e}")
        return False

# --- NUOVE FUNZIONI PER REPORT E ADMIN ---

def save_report_to_db(username, question_id, message):
    """Salva una segnalazione nel foglio 'Segnalazioni'"""
    ws = get_worksheet("Segnalazioni")
    if not ws: return False
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Colonne: Data, Utente, ID, Messaggio, Stato
        ws.append_row([timestamp, username, question_id, message, "Aperto"])
        return True
    except Exception as e:
        st.error(f"Errore invio report: {e}")
        return False

def fetch_all_stats():
    """Scarica TUTTO il database per l'Admin Dashboard"""
    ws = get_worksheet()
    if not ws: return []
    try:
        return ws.get_all_records()
    except: return []