# logic.py - v26.0 (Target 20 Questions)
import pandas as pd
import random
import datetime

# --- CONFIGURAZIONE REGOLE ESAME BASE ---
# Decreto Direttoriale n. 131 del 31/05/2022
RULES_BASE = {
    "Scafo": 1,          # Teoria dello Scafo
    "Motori": 1,         # Motori
    "Sicurezza": 3,      # Sicurezza
    "Manovra": 4,        # Manovra e Condotta
    "Colreg": 2,         # Colreg e Segnalamento
    "Meteorologia": 2,   # Meteorologia
    "Navigazione": 4,    # Navigazione
    "Normativa": 3       # Normativa
}

def get_balanced_exam_questions(df):
    """Genera scheda esame bilanciata."""
    exam_questions = []
    df.columns = [c.strip() for c in df.columns]
    
    if 'Argomento' not in df.columns:
        return df.sample(min(len(df), 20))

    work_df = df.copy()
    
    for keyword, count in RULES_BASE.items():
        subset = work_df[work_df['Argomento'].astype(str).str.contains(keyword, case=False, na=False)]
        if len(subset) >= count:
            selected = subset.sample(n=count)
            exam_questions.append(selected)
        else:
            if not subset.empty: exam_questions.append(subset)
    
    if exam_questions:
        final_exam = pd.concat(exam_questions)
        return final_exam.sample(frac=1).reset_index(drop=True)
    else:
        return df.sample(0)

def get_next_session_questions(df, history, mode="Allenamento"):
    """
    Logica SRS (Spaced Repetition System).
    Target: 20 domande per sessione Allenamento.
    """
    df.columns = [c.strip() for c in df.columns]
    TARGET_QUESTIONS = 20  # <--- MODIFICA QUI: DA 10 A 20
    
    if not history and mode == "Ripasso":
        return df.iloc[0:0]
        
    if not history and mode == "Allenamento":
        return df.sample(min(len(df), TARGET_QUESTIONS))

    today = datetime.datetime.now()
    ids_error = []
    ids_review_due = []
    
    for q_id, data in history.items():
        score = data['score']
        date_str = data['date']
        try:
            last_seen = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            days_passed = (today - last_seen).days
        except: days_passed = 100

        if score <= -1: ids_error.append(q_id)
        elif score > 0:
            threshold = 3
            if score == 2: threshold = 7
            elif score >= 3: threshold = 15
            if days_passed >= threshold: ids_review_due.append(q_id)

    df['ID Str'] = df['ID Progressivo'].astype(str)

    if mode == "Ripasso":
        subset = df[df['ID Str'].isin(ids_error)]
        if subset.empty: return subset
        return subset.sample(frac=1).head(TARGET_QUESTIONS)

    else: # Allenamento
        q_errors = df[df['ID Str'].isin(ids_error)]
        q_reviews = df[df['ID Str'].isin(ids_review_due)]
        
        all_history_ids = set(history.keys())
        q_new = df[~df['ID Str'].isin(all_history_ids)]
        
        selection = []
        
        # Logica di riempimento: un po' di errori, un po' di ripassi, il resto nuove
        if not q_errors.empty: selection.append(q_errors.sample(min(len(q_errors), 5)))
        if not q_reviews.empty: selection.append(q_reviews.sample(min(len(q_reviews), 5)))
            
        current_len = sum([len(x) for x in selection])
        needed = TARGET_QUESTIONS - current_len
        
        if needed > 0 and not q_new.empty:
            selection.append(q_new.sample(min(len(q_new), needed)))
            
        if not selection and not q_new.empty:
             selection.append(q_new.sample(min(len(q_new), TARGET_QUESTIONS)))
             
        if selection:
            final_df = pd.concat(selection)
            # Se ne abbiamo prese troppe, taglia a 20
            if len(final_df) > TARGET_QUESTIONS:
                return final_df.sample(TARGET_QUESTIONS).reset_index(drop=True)
            return final_df.sample(frac=1).reset_index(drop=True)
        else:
            return df.sample(min(len(df), TARGET_QUESTIONS))