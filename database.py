# database.py - v23.3 (Logic: First Sheet Index - Universal Compatibility)
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_client():
    if "connections" in st.secrets and "gsheets_v2" in st.secrets["connections"]:
        secrets_dict = dict(st.secrets["connections"]["gsheets_v2"])
        creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    return None

def get_worksheet_by_index(index=0):
    """
    Recupera il foglio in base alla POSIZIONE (0 = Primo foglio a sinistra).
    Ignora completamente il nome (Foglio1, Sheet1, etc).
    """
    client = get_client()
    if client:
        try:
            url = st.secrets["connections"]["gsheets_v2"]["spreadsheet"]
            sh = client.open_by_url(url)
            return sh.get_worksheet(index)
        except Exception as e:
            return None
    return None

def get_anagrafica_sheet():
    """Cerca l'Anagrafica. Se non c'è, prova a usare il secondo foglio o crea."""
    client = get_client()
    if client:
        try:
            url = st.secrets["connections"]["gsheets_v2"]["spreadsheet"]
            sh = client.open_by_url(url)
            try:
                return sh.worksheet("Anagrafica")
            except:
                # Se non trova 'Anagrafica', prova a creare o return None
                try: 
                    ws = sh.add_worksheet(title="Anagrafica", rows=1000, cols=5)
                    ws.append_row(["Utente", "Pin", "Data"])
                    return ws
                except: return None
        except: return None
    return None

# --- GESTIONE UTENTI (ANAGRAFICA) ---
def check_user_exists(username):
    ws = get_anagrafica_sheet()
    if not ws: return False
    try:
        # Cerca nella colonna 1 (Utente)
        users = ws.col_values(1)
        return username.strip().lower() in [u.strip().lower() for u in users]
    except: return False

def verify_pin(username, pin):
    ws = get_anagrafica_sheet()
    if not ws: return True
    try:
        records = ws.get_all_records()
        target = username.strip().lower()
        for row in records:
            # Cerca le chiavi in modo flessibile
            r_user = str(row.get('Utente', row.get('utente', list(row.values())[0]))).strip().lower()
            if r_user == target:
                # Assume che il PIN sia nella seconda colonna se i nomi non coincidono
                r_pin = str(row.get('Pin', row.get('pin', list(row.values())[1]))).strip()
                return r_pin == str(pin).strip()
    except: pass
    return False

def register_user(username, pin):
    ws = get_anagrafica_sheet()
    if not ws: return False
    try:
        ws.append_row([username.strip(), str(pin).strip(), datetime.datetime.now().strftime("%Y-%m-%d")])
        return True
    except: return False

# --- GESTIONE STORICO (FOGLIO 1 - INDEX 0) ---
def fetch_user_history(username):
    # Prende il PRIMO FOGLIO (Indice 0) qualunque nome abbia
    ws = get_worksheet_by_index(0)
    if not ws: return {}
    
    try:
        # Scarica tutto come lista di liste (più veloce e sicuro dei record dict)
        # Struttura attesa: [ID_Univoco, Utente, ID_Domanda, Esito, Timestamp]
        rows = ws.get_all_values()
        
        if len(rows) < 2: return {} # Solo intestazione o vuoto
        
        target = username.strip().lower()
        history = {}
        
        # Salta la riga 0 (intestazione)
        for row in rows[1:]:
            if len(row) >= 4: # Assicurati che ci siano abbastanza colonne
                # Colonna B (indice 1) = Utente
                r_user = str(row[1]).strip().lower()
                
                if r_user == target:
                    # Colonna C (indice 2) = ID Domanda
                    q_id = str(row[2]).strip()
                    # Colonna D (indice 3) = Esito
                    try: score = int(row[3])
                    except: score = 0
                    # Colonna E (indice 4) = Timestamp
                    ts = str(row[4]) if len(row) > 4 else ""
                    
                    history[q_id] = {'score': score, 'date': ts}
                    
        return history
    except Exception as e:
        return {}

def fetch_all_stats():
    ws = get_worksheet_by_index(0)
    if not ws: return []
    try:
        # Per l'admin serve il dizionario per i nomi colonne
        return ws.get_all_records()
    except: return []

def upsert_answer(username, question_id, result):
    ws = get_worksheet_by_index(0)
    if not ws: return False
    
    unique_key = f"{username.strip().lower()}_{str(question_id).strip()}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Cerca nella PRIMA colonna (Col A)
        cell = ws.find(unique_key, in_column=1)
        
        if cell:
            # Aggiorna Colonna 4 (D - Esito) e 5 (E - Timestamp)
            ws.update_cell(cell.row, 4, result)
            ws.update_cell(cell.row, 5, timestamp)
        else:
            # Aggiunge in coda
            ws.append_row([unique_key, username, str(question_id), result, timestamp])
        return True
    except: return False

def save_report_to_db(username, question_id, message):
    client = get_client()
    if client:
        try:
            url = st.secrets["connections"]["gsheets_v2"]["spreadsheet"]
            sh = client.open_by_url(url)
            # Cerca o crea Segnalazioni
            try: ws = sh.worksheet("Segnalazioni")
            except: ws = sh.add_worksheet("Segnalazioni", 1000, 5)
            
            ws.append_row([datetime.datetime.now().strftime("%Y-%m-%d"), username, str(question_id), message])
            return True
        except: return False
    return False