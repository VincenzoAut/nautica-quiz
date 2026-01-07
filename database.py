# database.py - v25.1 (Fix Anagrafica & Login)
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd
import threading

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- CONFIGURAZIONE NOMI FOGLI ---
# Qui impostiamo i nomi esatti presenti nel tuo Google Sheet
SHEET_USERS_NAME = "Anagrafica"  # <--- CORRETTO: Prima era "Utenti"
SHEET_REPORT_NAME = "Segnalazioni"

def get_client():
    """Recupera il client GSpread dai secrets."""
    if "connections" in st.secrets and "gsheets_v2" in st.secrets["connections"]:
        secrets_dict = dict(st.secrets["connections"]["gsheets_v2"])
        creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    return None

def get_spreadsheet():
    """Apre lo spreadsheet principale."""
    client = get_client()
    if client:
        try:
            url = st.secrets["connections"]["gsheets_v2"]["spreadsheet"]
            return client.open_by_url(url)
        except Exception as e:
            print(f"Errore connessione GSheets: {e}")
            return None
    return None

def get_worksheet_by_index(index=0):
    """
    Recupera il foglio dei RISULTATI (default: primo foglio a sinistra).
    Se i risultati non sono nel primo foglio, cambia l'indice qui.
    """
    sh = get_spreadsheet()
    if sh:
        try:
            return sh.get_worksheet(index)
        except: return None
    return None

# --- SEZIONE 1: AUTENTICAZIONE (Login) ---

def check_user_exists(username):
    sh = get_spreadsheet()
    if not sh: return False
    try:
        # Cerca nel foglio "Anagrafica"
        ws = sh.worksheet(SHEET_USERS_NAME)
        # Cerca username nella colonna A (1)
        cell = ws.find(username, in_column=1) 
        return cell is not None
    except Exception as e:
        print(f"Errore check_user: {e}")
        return False

def verify_pin(username, pin):
    sh = get_spreadsheet()
    if not sh: return False
    try:
        ws = sh.worksheet(SHEET_USERS_NAME)
        cell = ws.find(username, in_column=1)
        if cell:
            # Assume PIN in colonna B (Col 2), come da tua indicazione
            real_pin = ws.cell(cell.row, 2).value
            # Confrontiamo come stringhe per evitare errori (es. 1609 vs "1609")
            return str(real_pin).strip() == str(pin).strip()
    except Exception as e:
        # Questo stampava "Utenti" nel tuo errore precedente
        print(f"Errore verify_pin: {e}") 
    return False

def register_user(username, pin):
    sh = get_spreadsheet()
    if not sh: return False
    try:
        try:
            ws = sh.worksheet(SHEET_USERS_NAME)
        except:
            # Se non esiste, lo crea con le intestazioni corrette
            ws = sh.add_worksheet(title=SHEET_USERS_NAME, rows=100, cols=3)
            ws.append_row(["Utente", "Pin", "Data"])
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        ws.append_row([username, pin, timestamp])
        return True
    except Exception as e:
        print(f"Errore registrazione: {e}")
        return False

# --- SEZIONE 2: VELOCITÀ (Async Upsert) ---

def _upsert_worker(username, question_id, result):
    """Funzione worker che gira in background."""
    try:
        ws = get_worksheet_by_index(0) # Indice 0 = Foglio Risultati
        if not ws: return

        unique_key = f"{username.strip().lower()}_{str(question_id).strip()}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cerca nella PRIMA colonna (Col A)
        try:
            cell = ws.find(unique_key, in_column=1)
        except gspread.exceptions.CellNotFound:
            cell = None
        
        if cell:
            ws.update_cell(cell.row, 4, result)     # Col D = Risultato
            ws.update_cell(cell.row, 5, timestamp)  # Col E = Timestamp
        else:
            ws.append_row([unique_key, username, str(question_id), result, timestamp])
            
    except Exception as e:
        print(f"Errore salvataggio background: {e}")

def upsert_answer(username, question_id, result):
    """FIRE AND FORGET: Lancia il thread e ritorna subito."""
    thread = threading.Thread(target=_upsert_worker, args=(username, question_id, result))
    thread.start()
    return True

# --- SEZIONE 3: REPORTING (Async) ---

def _report_worker(username, question_id, message):
    try:
        sh = get_spreadsheet()
        if sh:
            try:
                ws = sh.worksheet(SHEET_REPORT_NAME)
            except:
                ws = sh.add_worksheet(title=SHEET_REPORT_NAME, rows=100, cols=5)
                ws.append_row(["Data", "Utente", "ID Domanda", "Messaggio"])
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.append_row([timestamp, username, question_id, message])
    except Exception as e:
        print(f"Errore report background: {e}")

def save_report_to_db(username, question_id, message):
    thread = threading.Thread(target=_report_worker, args=(username, question_id, message))
    thread.start()
    return True

# --- SEZIONE 4: LETTURA DATI & ALIAS PER APP.PY ---

def get_user_history(username):
    """Legge lo storico (Sincrono, serve all'avvio)."""
    ws = get_worksheet_by_index(0) # Assume che i risultati siano nel Foglio 1 (indice 0)
    if not ws: return {}
    try:
        records = ws.get_all_values()
        if not records: return {}
        
        history = {}
        user_lower = username.strip().lower()
        
        # Struttura attesa Risultati: A=Key, B=User, C=ID, D=Res, E=Time
        for row in records[1:]:
            if len(row) >= 4 and row[1].strip().lower() == user_lower:
                q_id = str(row[2]).strip()
                try:
                    # Gestione robusta per evitare errori se c'è testo strano nel DB
                    val = row[3]
                    if str(val).lstrip('-').isdigit(): 
                        score = int(val)
                    else:
                        score = 0
                except: score = 0
                
                history[q_id] = {
                    "score": score,
                    "date": row[4] if len(row) > 4 else ""
                }
        return history
    except Exception as e: 
        print(f"Errore lettura history: {e}")
        return {}

def get_full_db_dump():
    """Per l'admin."""
    ws = get_worksheet_by_index(0)
    if not ws: return []
    try:
        return ws.get_all_records()
    except: return []

# --- ALIAS PER COMPATIBILITÀ ---
fetch_user_history = get_user_history
fetch_all_stats = get_full_db_dump