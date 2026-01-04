# logic.py - Algoritmo Spaced Repetition (SRS)
import datetime
import pandas as pd
import random

# --- CONFIGURAZIONE INTERVALLI (In Giorni) ---
# Se streak (risposte di fila) è 0 (errore) -> Rivedi dopo 0 giorni (subito/domani)
# Se streak è 1 -> Rivedi dopo 3 giorni
# Se streak è 2 -> Rivedi dopo 7 giorni
# Se streak è 3+ -> Rivedi dopo 15 giorni
SRS_INTERVALS = {0: 0, 1: 3, 2: 7, 3: 15}

def get_days_diff(date_str):
    """Calcola quanti giorni sono passati da una data stringa."""
    if not date_str or date_str == "": return 9999 # Mai vista
    try:
        # Tenta di leggere il formato YYYY-MM-DD
        last_date = datetime.datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        today = datetime.date.today()
        delta = (today - last_date).days
        return delta
    except:
        return 9999 # In caso di errore data, trattala come vecchia

def is_due_for_review(item_data):
    """
    Decide se una domanda va studiata oggi in base alla logica SRS.
    item_data: {'score': -1/1/2..., 'date': '2024-01-01'}
    """
    score = item_data.get('score', 0)
    last_date = item_data.get('date', '')
    
    # 1. Se è un errore (-1), va rivista SUBITO (domani o oggi stesso)
    if score == -1: return True
    
    # 2. Se lo score è 0 o nullo, è nuova (o mai fatta giusta), quindi Sì
    if score == 0: return True
    
    # 3. Calcolo giorni passati
    days_passed = get_days_diff(last_date)
    
    # 4. Recupera intervallo target
    # Se score è 4, usa il valore di 3 (max 15 giorni)
    target_wait = SRS_INTERVALS.get(score, 15)
    
    # 5. VERDETTO: È passato abbastanza tempo?
    return days_passed >= target_wait

def get_next_session_questions(full_db, user_history, mode="Allenamento", num_questions=20):
    """
    Genera il pacchetto di domande per la sessione.
    Mischia domande SCADUTE (SRS) + domande NUOVE.
    """
    # Filtra il DB per la materia corrente (es. solo domande Base)
    # Nota: Assumiamo che full_db sia già il dataframe corretto caricato in app.py
    
    due_ids = [] # Domande scadute (da ripassare)
    new_ids = [] # Domande mai viste
    
    all_ids = full_db['ID Progressivo'].astype(str).tolist()
    
    for q_id in all_ids:
        if q_id in user_history:
            # La conosciamo: verifichiamo se è scaduta
            data = user_history[q_id]
            if is_due_for_review(data):
                due_ids.append(q_id)
        else:
            # Mai vista: è nuova
            new_ids.append(q_id)
            
    # LOGICA DI SELEZIONE
    if mode == "Ripasso":
        # Nel ripasso prendiamo SOLO quelle scadute o con errori
        # Priorità assoluta agli errori (-1)
        error_ids = [k for k,v in user_history.items() if v['score'] == -1 and k in all_ids]
        other_due = [qid for qid in due_ids if qid not in error_ids]
        
        final_selection = error_ids + other_due
        # Se sono troppe, ne prendiamo un campione, se poche tutte
        if len(final_selection) > num_questions:
            return full_db[full_db['ID Progressivo'].isin(random.sample(final_selection, num_questions))]
        return full_db[full_db['ID Progressivo'].isin(final_selection)]

    else: # Modalità Allenamento / Esame
        # Mix Bilanciato: 70% Ripasso Scaduto, 30% Cose Nuove
        n_review = int(num_questions * 0.7)
        n_new = num_questions - n_review
        
        selected_review = []
        selected_new = []
        
        if due_ids:
            # Prendi fino a n_review dalle scadute
            k = min(len(due_ids), n_review)
            selected_review = random.sample(due_ids, k)
            
        # Riempi il resto con le nuove
        remaining_slots = num_questions - len(selected_review)
        if new_ids:
            k = min(len(new_ids), remaining_slots)
            selected_new = random.sample(new_ids, k)
            
        # Se ho ancora spazio (es. ho finito le nuove), riempio con altre di ripasso (anche non scadute, a caso)
        final_ids = selected_review + selected_new
        
        # Estrai le righe dal DB
        return full_db[full_db['ID Progressivo'].isin(final_ids)]