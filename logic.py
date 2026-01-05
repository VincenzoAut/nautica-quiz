import datetime
import pandas as pd
import random

# --- CONFIGURAZIONE SRS ---
SRS_INTERVALS = {0: 0, 1: 3, 2: 7, 3: 15}

# --- NUOVO: DISTRIBUZIONE MINISTERIALE ---
DISTRIBUZIONE_BASE = {
    "TEORIA DELLO SCAFO": 1,
    "MOTORI": 1,
    "SICUREZZA DELLA NAVIGAZIONE": 3,
    "MANOVRA E CONDOTTA": 4,
    "COLREG E SEGNALAMENTO MARITTIMO": 2,
    "METEOROLOGIA": 2,
    "NAVIGAZIONE CARTOGRAFICA ED ELETTRONICA": 4,
    "NORMATIVA DIPORTISTICA E AMBIENTALE": 3
}

def get_days_diff(date_str):
    if not date_str: return 9999
    try:
        last_date = datetime.datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        return (datetime.date.today() - last_date).days
    except: return 9999

def is_due_for_review(item_data):
    score = item_data.get('score', 0)
    if score <= 0: return True
    days_passed = get_days_diff(item_data.get('date', ''))
    return days_passed >= SRS_INTERVALS.get(score, 15)

# --- NUOVO: FUNZIONE ESTRAZIONE BILANCIATA ---
def get_balanced_exam_questions(full_db):
    if full_db is None or full_db.empty: return pd.DataFrame()
    
    exam_pool = []
    # Itera su ogni argomento e pesca il numero esatto
    for argomento, quantita in DISTRIBUZIONE_BASE.items():
        subset = full_db[full_db['Argomento'] == argomento]
        if len(subset) >= quantita:
            exam_pool.append(subset.sample(quantita))
        else:
            # Fallback se non trova l'argomento (evita crash)
            exam_pool.append(full_db.sample(min(quantita, len(full_db))))
            
    return pd.concat(exam_pool).sample(frac=1).reset_index(drop=True)

def get_next_session_questions(full_db, user_history, mode="Allenamento", num_questions=20):
    if full_db is None or full_db.empty: return pd.DataFrame()
    
    all_ids = full_db['ID Progressivo'].astype(str).tolist()
    due_ids = []
    new_ids = []
    
    for q_id in all_ids:
        if q_id in user_history:
            if is_due_for_review(user_history[q_id]): due_ids.append(q_id)
        else: new_ids.append(q_id)
            
    if mode == "Ripasso":
        error_ids = [k for k,v in user_history.items() if v['score'] == -1 and k in all_ids]
        final = error_ids + [qid for qid in due_ids if qid not in error_ids]
        if not final: return pd.DataFrame()
        picked = random.sample(final, min(len(final), num_questions))
        return full_db[full_db['ID Progressivo'].isin(picked)]
    else:
        n_rev = int(num_questions * 0.7)
        sel_rev = random.sample(due_ids, min(len(due_ids), n_rev))
        rem = num_questions - len(sel_rev)
        sel_new = random.sample(new_ids, min(len(new_ids), rem))
        return full_db[full_db['ID Progressivo'].isin(sel_rev + sel_new)]