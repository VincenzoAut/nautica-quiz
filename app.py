# --- VERSIONE APP: v10.25 (UI Fixes & Layout Domanda) ---
import streamlit as st
import pandas as pd
import os
import time
import datetime
import random
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import base64

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Patente Nautica App Pro", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

# NOMI FILES SFONDO
MAIN_BG_IMAGE = "background.jpg"      # Sfondo Principale (Veliero)
SIDEBAR_BG_IMAGE = "background2.jpg"  # Sfondo Sidebar (Mappa chiara)

# --- 2. GESTIONE DATABASE (GOOGLE SHEETS) ---
def get_google_sheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            secrets_dict = dict(st.secrets["connections"]["gsheets"])
        else: return None
        creds = Credentials.from_service_account_info(secrets_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_url(secrets_dict["spreadsheet"]).sheet1 
    except: return None

def load_user_history(username):
    ws = get_google_sheet()
    if ws:
        try:
            records = ws.get_all_records()
            history = {}
            for row in records:
                r_user = str(row.get('Utente', row.get('utente', '')))
                r_id = str(row.get('ID_Domanda', row.get('id_domanda', '')))
                r_esito = row.get('Esito', row.get('esito', 0))
                if r_user.lower() == username.lower():
                    history[r_id] = int(r_esito)
            return history
        except: return {}
    return {}

def save_answer_cloud(user, question_id, result):
    ws = get_google_sheet()
    if ws:
        try:
            ws.append_row([user, question_id, result])
            return True
        except: return False
    return False

# --- 3. CSS & GESTIONE SFONDI ---

# Funzione per lo sfondo principale (Main App)
def add_main_bg(image_file):
    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/{"jpg"};base64,{encoded_string});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Funzione per lo sfondo della Sidebar
def add_sidebar_bg(image_file):
    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode()
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background-image: url(data:image/{"jpg"};base64,{encoded_string});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        /* Rendi trasparente il div interno per vedere l'immagine */
        [data-testid="stSidebar"] > div:first-child {{
            background-color: transparent;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# APPLICAZIONE SFONDI (Se i file esistono)
if os.path.exists(MAIN_BG_IMAGE):
    add_main_bg(MAIN_BG_IMAGE)

if os.path.exists(SIDEBAR_BG_IMAGE):
    add_sidebar_bg(SIDEBAR_BG_IMAGE)

# CSS STILI GENERALI AGGIORNATI (v10.25)
st.markdown("""
<style>
    /* Layout Generale */
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    
    /* --- BOTTONI (Correzione Visibilità) --- */
    /* Stile base per TUTTI i bottoni */
    div.stButton > button {
        width: 100%; 
        border-radius: 8px; 
        height: auto; 
        padding: 12px; 
        font-size: 16px; 
        margin-bottom: 5px; 
        background-color: #ffffff !important; /* Sfondo Bianco Solido SEMPRE */
        border: 1px solid #ced4da !important; /* Bordo Grigio visibile */
        color: #212529 !important; /* Testo Scuro */
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    
    /* Effetto Hover (quando passi sopra) */
    div.stButton > button:hover {
        border-color: #0d6efd !important;
        color: #0d6efd !important;
        background-color: #f8f9fa !important;
        transform: translateY(-1px);
    }

    /* --- BOTTONE PRIMARIO (ACCEDI / NUOVA SIMULAZIONE) --- */
    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b !important; 
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        font-size: 18px !important; 
        padding: 15px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #ff3333 !important;
        box-shadow: 0 6px 8px rgba(0,0,0,0.3);
    }

    /* --- TITOLI E TESTI --- */
    h2 { color: white !important; text-shadow: 2px 2px 4px #000000; font-weight: 800 !important; }
    
    /* --- BOX DOMANDA AGGIORNATO (Argomento in alto) --- */
    .question-box {
        background-color: #e3f2fd;
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #1565c0;
        margin-bottom: 20px;
        color: #0d47a1;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Intestazione Domanda */
    .question-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        border-bottom: 1px solid rgba(13, 71, 161, 0.2);
        padding-bottom: 8px;
        flex-wrap: wrap;
    }
    
    .question-id { 
        font-size: 14px; 
        font-weight: 900; 
        color: #1565c0; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
    }
    
    .question-topic {
        font-size: 13px;
        color: #455a64;
        font-style: italic;
        text-align: right;
        font-weight: 600;
    }

    .question-text { 
        font-size: 20px; 
        font-weight: 700; 
        line-height: 1.5; 
        color: #0d47a1; 
    }
    
    /* Metriche */
    .metric-container { display: flex; justify-content: space-between; background-color: white; padding: 5px 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); margin-bottom: 15px; }
    .metric-box { text-align: center; width: 100%; }
    .metric-label { font-size: 10px; color: #888; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 18px; font-weight: 800; color: #333; }
    
    /* Bottone Esci */
    div[data-testid="column"] button { padding: 5px 0px; font-size: 20px; border: 1px solid #ddd; background-color: transparent !important; color: #d63384 !important; font-weight: bold; }
    div[data-testid="column"] button:hover { background-color: #fce4ec !important; border-color: #d63384 !important; }
    
    /* Box Risultati */
    .result-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; color: #000; font-weight: 600; border: 1px solid rgba(0,0,0,0.1); font-size: 15px; }
    
    /* Rank Box */
    .rank-box { background: linear-gradient(135deg, #0061f2 0%, #00c6f7 100%); padding: 15px; border-radius: 8px; color: white; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .rank-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; font-weight: bold; }
    .rank-name { font-size: 22px; font-weight: 800; margin: 5px 0; }
    
    /* Footer Sidebar */
    .footer-sidebar { font-size: 11px; color: #444; text-align: center; margin-top: 30px; padding-top: 10px; border-top: 1px solid #999; line-height: 1.6; font-weight: 500; }
    .footer-sidebar a { color: #0061f2; text-decoration: none; font-weight: bold; }
    
    /* Esiti */
    .exam-pass { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #c3e6cb; margin-bottom: 20px; }
    .exam-fail { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #f5c6cb; margin-bottom: 20px; }
    .review-end { background-color: #e2e3e5; color: #383d41; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #d6d8db; margin-bottom: 20px; }
    
    /* Login */
    .login-container { background-color: rgba(255, 255, 255, 0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); text-align: center; border: 1px solid rgba(255, 255, 255, 0.18); }
    .login-title { font-size: 32px; font-weight: 800; color: #0061f2; margin-bottom: 5px; }
    .login-subtitle { font-size: 14px; color: #555; margin-bottom: 25px; font-weight: 500; }
    .footer-login { position: fixed; bottom: 20px; right: 20px; text-align: right; color: white; font-size: 14px; font-weight: bold; background-color: rgba(0,0,0,0.5); padding: 10px 15px; border-radius: 10px; backdrop-filter: blur(5px); }
    
    .debug-info { font-size: 11px; color: #495057; background: #e9ecef; padding: 5px; border-radius: 4px; margin-bottom: 10px; border: 1px dashed #adb5bd; }
</style>
""", unsafe_allow_html=True)

# --- 4. GESTIONE STATO ---
if 'init' not in st.session_state:
    st.session_state.current_user = None
    st.session_state.quiz_mode = "Quiz Base"
    st.session_state.exam_mode = False
    st.session_state.review_mode = False
    st.session_state.stats_mode = False
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.exam_questions = []
    st.session_state.current_row = None
    st.session_state.answered = False
    st.session_state.shuffled_options = []
    st.session_state.start_time = None
    st.session_state.exam_finished = False
    st.session_state.history = {}
    st.session_state.debug_mode = False
    st.session_state.init = True

# --- 5. CARICAMENTO DATI ---
@st.cache_resource
def get_image_index():
    index = {}
    if os.path.exists(CARTELLA_IMMAGINI):
        for f in os.listdir(CARTELLA_IMMAGINI):
            if not f.startswith("."):
                index[os.path.splitext(f)[0].lower().strip()] = os.path.join(CARTELLA_IMMAGINI, f)
    return index

def get_image_path(img_name):
    if pd.isna(img_name) or str(img_name).strip() == "": return None
    return get_image_index().get(str(img_name).strip().lower())

@st.cache_data
def load_data(mode):
    f = FILE_CARTEGGIO if "Carteggio" in mode else (FILE_QUIZ_VELA if "Vela" in mode else FILE_QUIZ_BASE)
    if not os.path.exists(f): return None
    try:
        df = pd.read_csv(f) if f.endswith('.csv') else pd.read_excel(f)
        df.columns = [str(c).strip() for c in df.columns]
        if 'ID Progressivo' in df.columns: df['ID Progressivo'] = df['ID Progressivo'].astype(str)
        if "Carteggio" not in mode:
            fr = FILE_RACCORDO
            if not os.path.exists(fr): fr = fr.replace(".xlsx", ".csv")
            if os.path.exists(fr):
                dfr = pd.read_csv(fr) if fr.endswith('.csv') else pd.read_excel(fr)
                dfr.columns = [c.strip() for c in dfr.columns]
                if 'Progressivo' in dfr.columns: dfr['Progressivo'] = dfr['Progressivo'].astype(str)
                if 'Progressivo' in dfr.columns and 'Immagine' in dfr.columns:
                    df = pd.merge(df, dfr[['Progressivo', 'Immagine']], left_on='ID Progressivo', right_on='Progressivo', how='left')
                    df.rename(columns={'Immagine_y': 'NomeImmagine'}, inplace=True)
        return df
    except: return None

# --- 6. LOGIN ---
if st.session_state.current_user is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("""
        <div class="login-container">
            <div class="login-title">⚓ Patente Nautica App Pro</div>
            <div class="login-subtitle">Cloud Edition v10.25</div>
        </div>
        """, unsafe_allow_html=True)
        
        name_input = st.text_input("Inserisci il tuo nome per accedere:", placeholder="Es. Vincenzo").strip()
        st.markdown("<br>", unsafe_allow_html=True)
        
        # AGGIORNATO: use_container_width=True per bottone grande
        if st.button("ACCEDI AL SISTEMA", type="primary", use_container_width=True):
            if name_input:
                with st.spinner("Accesso al database in corso..."):
                    hist = load_user_history(name_input)
                    st.session_state.history = hist
                    st.session_state.current_user = name_input
                    st.rerun()
        
        with st.expander("ℹ️ INFO E GUIDA ALL'USO"):
            st.markdown("""
            **A cosa serve questa App?**
            Questa applicazione è uno strumento professionale per supportarti nello studio dei quiz ministeriali per il conseguimento della **Patente Nautica**.

            **Come funziona:**
            * 🎓 **Simulazione Esame:** Riproduce l'esame reale.
            * ♾️ **Allenamento Continuo:** Esercitazione libera.
            * 🔄 **Ripasso Errori:** Una modalità speciale per rivedere solo i quiz che hai sbagliato in passato.
            """)

    st.markdown("""
    <div class='footer-login'>
        <b>Footer & Credits</b><br>
        Developed by Vincenzo Autolitano
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 7. LOGICA GIOCO ---
db = load_data(st.session_state.quiz_mode)
if db is None or len(db) == 0: st.stop()

def get_unique_key(id_dom): return f"{st.session_state.quiz_mode}_{id_dom}"

def calculate_weight(val):
    if val is None: return 1.0        
    if val == -1: return 10.0          
    if val > 0: return 1.0 / (1.0 + val) 
    return 1.0

def get_user_rank(mastered_count):
    if mastered_count < 100: return "🧹 Mozzo", 100
    if mastered_count < 300: return "⚓ Marinaio", 300
    if mastered_count < 500: return "🧭 Nostromo", 500
    if mastered_count < 700: return "🛳️ Comandante", 700
    return "🐺 Lupo di Mare", 1000

def get_weighted_question(dataset, num=1):
    df = dataset.copy()
    def assign_weight(id_dom):
        unique_key = get_unique_key(id_dom)
        val = st.session_state.history.get(unique_key)
        return calculate_weight(val)
    df['peso'] = df['ID Progressivo'].apply(assign_weight)
    return df.sample(n=min(len(df), num), weights='peso')

def reset_game(exam=False, review=False, stats=False):
    st.session_state.exam_mode = exam
    st.session_state.review_mode = review
    st.session_state.stats_mode = stats
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.answered = False
    st.session_state.exam_finished = False
    st.session_state.start_time = time.time() if exam else None
    st.session_state.exam_questions = [] 
    
    if not stats:
        if review:
            prefix = f"{st.session_state.quiz_mode}_"
            target_ids = []
            for key, val in st.session_state.history.items():
                if val == -1 and key.startswith(prefix):
                    target_ids.append(key.replace(prefix, ""))
            filtered_db = db[db['ID Progressivo'].isin(target_ids)]
            if len(filtered_db) == 0:
                st.warning("Nessun errore da ripassare!")
                st.session_state.review_mode = False
                return
            st.session_state.exam_questions = filtered_db.sample(len(filtered_db)).to_dict('records')
            load_question()
        elif exam:
            num = 5 if ("Carteggio" in st.session_state.quiz_mode or "Vela" in st.session_state.quiz_mode) else 20
            st.session_state.exam_questions = get_weighted_question(db, num).to_dict('records')
            load_question()
        else:
            next_question()

def next_question():
    st.session_state.answered = False
    if st.session_state.exam_mode or st.session_state.review_mode:
        st.session_state.exam_index += 1
        load_question()
    elif len(db) > 0:
        st.session_state.current_row = get_weighted_question(db, 1).iloc[0]
        prepare_options()

def load_question():
    if st.session_state.exam_questions and st.session_state.exam_index < len(st.session_state.exam_questions):
        st.session_state.current_row = st.session_state.exam_questions[st.session_state.exam_index]
        prepare_options()
    else: st.session_state.exam_finished = True

def prepare_options():
    row = st.session_state.current_row
    if row is not None and "Carteggio" not in st.session_state.quiz_mode:
        corretta = str(row.get('Risposta Esatta','')).strip().upper()
        opts = [{'txt': row.get('Risposta A'), 'ok': corretta=='A'},
                {'txt': row.get('Risposta B'), 'ok': corretta=='B'},
                {'txt': row.get('Risposta C'), 'ok': corretta=='C'}]
        opts = [o for o in opts if pd.notna(o['txt'])]
        random.shuffle(opts)
        st.session_state.shuffled_options = opts

def answer(is_correct):
    if not st.session_state.answered:
        st.session_state.answered = True
        id_dom = str(st.session_state.current_row.get('ID Progressivo'))
        unique_key = get_unique_key(id_dom)
        current_val = st.session_state.history.get(unique_key)
        new_val = 1
        if is_correct:
            new_val = 1 if (current_val is None or current_val == -1) else current_val + 1
        else:
            new_val = -1
        st.session_state.history[unique_key] = new_val
        save_answer_cloud(st.session_state.current_user, unique_key, new_val)
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

# --- 8. SIDEBAR ---
with st.sidebar:
    st.title("⚓ Patente Nautica")
    col_u1, col_u2 = st.columns([4,1])
    with col_u1: st.markdown(f"👤 **{st.session_state.current_user}**")
    with col_u2:
        if st.button("⏻", help="Esci / Disconnetti"):
            st.session_state.current_user = None
            st.rerun()
    
    current_prefix = f"{st.session_state.quiz_mode}_"
    mastered_count = len([k for k, v in st.session_state.history.items() if k.startswith(current_prefix) and v > 0])
    rank_name, rank_target = get_user_rank(mastered_count)
    
    st.markdown(f"""
    <div class="rank-box">
        <div class="rank-title">IL TUO GRADO</div>
        <div class="rank-name">{rank_name}</div>
        <div class="rank-next">{mastered_count} / {rank_target} Consolidate</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(mastered_count / rank_target, 1.0))

    st.markdown("### 1. Scegli Materia:")
    mode = st.radio("Materia:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"], label_visibility="collapsed")
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode
        st.session_state.current_row = None
        st.session_state.exam_questions = []
        st.session_state.exam_mode = False
        st.session_state.review_mode = False
        st.session_state.stats_mode = False
        st.rerun()

    st.markdown("### 2. Azione:")
    st.button("🎓 SIMULAZIONE ESAME", type="primary", on_click=reset_game, kwargs={'exam': True})
    st.button("♾️ ALLENAMENTO", on_click=reset_game, kwargs={'exam': False})
    
    st.divider()
    
    err_count = 0
    for k, v in st.session_state.history.items():
        if v == -1 and k.startswith(current_prefix): err_count += 1
    if err_count > 0:
        st.error(f"⚠️ **{err_count} Errori**")
        st.button("🔄 RIPASSA ERRORI", on_click=reset_game, kwargs={'review': True})
    
    st.button("📊 STATISTICHE", on_click=reset_game, kwargs={'stats': True})
    
    with st.expander("🧠 DEBUG MEMORIA", expanded=False):
        st.session_state.debug_mode = st.checkbox("🛠️ Attiva Debug Mode")
        total_mem = len([k for k in st.session_state.history if k.startswith(current_prefix)])
        errors_debug = len([k for k,v in st.session_state.history.items() if k.startswith(current_prefix) and v == -1])
        st.markdown(f"**Dati Tecnici:**")
        st.markdown(f"- Totale ID in memoria: {total_mem}")
        st.markdown(f"- Errori Attivi: {errors_debug}")
        if st.checkbox("Mostra Elenco ID Completo"):
             debug_list = {k.replace(current_prefix, ""): v for k,v in st.session_state.history.items() if k.startswith(current_prefix)}
             st.write(debug_list)
    
    if st.session_state.exam_mode and st.session_state.start_time and not st.session_state.exam_finished:
        mm, ss = divmod(int(time.time() - st.session_state.start_time), 60)
        st.markdown(f"<h2 style='text-align:center; color:{'red' if mm>=20 else '#444'}'>{mm:02d}:{ss:02d}</h2>", unsafe_allow_html=True)

    today = datetime.datetime.now().strftime("%d/%m")
    
    subject_email = urllib.parse.quote(f"Segnalazione Errori Patente Nautica App Pro")
    
    st.markdown(f"""
    <div class='footer-sidebar'>
        <b>v10.25 Ultimate</b> • {today}<br>
        by Vincenzo Autolitano<br>
        <a href='mailto:vincenzo.autolitano@gmail.com?subject={subject_email}'>⚠️ SEGNALA ERRORE</a>
    </div>
    """, unsafe_allow_html=True)

# --- 9. INTERFACCIA PRINCIPALE ---
current_icon = icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}.get(st.session_state.quiz_mode, '⚓')

if st.session_state.stats_mode:
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    st.markdown(f"## 📊 Statistiche: {st.session_state.quiz_mode}")
    mem_data = []
    prefix = f"{st.session_state.quiz_mode}_"
    for k, v in st.session_state.history.items():
        if k.startswith(prefix):
            clean_id = k.replace(prefix, "")
            mem_data.append({'ID Progressivo': clean_id, 'Status': v})
    df_mem = pd.DataFrame(mem_data)
    
    if len(df_mem) > 0 and len(db) > 0:
        df_stats = pd.merge(db, df_mem, on='ID Progressivo', how='left')
        df_stats['Status'] = df_stats['Status'].fillna(0)
        df_stats['Masterizzata'] = df_stats['Status'] > 0
        df_stats['Errore'] = df_stats['Status'] == -1
        
        if 'Argomento' in df_stats.columns:
            stats_grp = df_stats.groupby('Argomento').agg(
                Totale=('ID Progressivo', 'count'),
                Masterizzate=('Masterizzata', 'sum'),
                Errori=('Errore', 'sum')
            ).reset_index()
            
            stats_grp['% Completamento'] = (stats_grp['Masterizzate'] / stats_grp['Totale'] * 100).astype(int)
            stats_grp = stats_grp.sort_values(by='% Completamento', ascending=False)
            
            tot_q = stats_grp['Totale'].sum()
            tot_m = stats_grp['Masterizzate'].sum()
            tot_e = stats_grp['Errori'].sum()
            tot_p = int(tot_m / tot_q * 100) if tot_q > 0 else 0
            
            total_row = pd.DataFrame([{
                'Argomento': '🔴 TOTALE GENERALE',
                'Totale': tot_q,
                'Masterizzate': tot_m,
                'Errori': tot_e,
                '% Completamento': tot_p
            }])
            stats_grp = pd.concat([stats_grp, total_row], ignore_index=True)
            stats_grp = stats_grp.rename(columns={'Masterizzate': 'Consolidate'})
            
            st.dataframe(stats_grp, column_config={
                    "% Completamento": st.column_config.ProgressColumn("%", min_value=0, max_value=100, format="%d%%"),
                    "Errori": st.column_config.NumberColumn("⚠️ Errori"),
                    "Consolidate": st.column_config.NumberColumn("✅ OK")
                }, hide_index=True, use_container_width=True)
        else: st.warning("Colonna 'Argomento' mancante.")
    else: st.info("Nessun dato salvato.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    title_suffix = "Ripasso" if st.session_state.review_mode else ("Simulazione Esame" if st.session_state.exam_mode else "Allenamento")
    st.markdown(f"## {current_icon} {st.session_state.quiz_mode} - *{title_suffix}*")

    if not st.session_state.exam_finished:
        tot = st.session_state.score_ok + st.session_state.score_ko
        perc = int(st.session_state.score_ok / tot * 100) if tot > 0 else 0
        st.markdown(f'<div class="metric-container"><div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div><div class="metric-box"><div class="metric-label">Errate</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div><div class="metric-box"><div class="metric-label">%</div><div class="metric-value">{perc}%</div></div></div>', unsafe_allow_html=True)
        
        if st.session_state.exam_mode or st.session_state.review_mode:
            q_current = st.session_state.exam_index + 1
            q_total = len(st.session_state.exam_questions)
            st.progress(q_current / q_total)
            st.caption(f"📝 Domanda {q_current} di {q_total}")

    if st.session_state.exam_finished:
        st.markdown('<div class="question-card">', unsafe_allow_html=True)
        if st.session_state.review_mode:
            prefix = f"{st.session_state.quiz_mode}_"
            errors_left = 0
            for k, v in st.session_state.history.items():
                if v == -1 and k.startswith(prefix):
                    errors_left += 1
            st.markdown(f"""<div class="review-end"><h1>✅ Ripasso Completato</h1><p>Hai terminato questa serie di ripasso.</p></div>""", unsafe_allow_html=True)
            if errors_left == 0:
                st.success("COMPLIMENTI! Hai azzerato tutti gli errori in questa materia! 🏆")
            else:
                st.info(f"⚠️ Nel database rimangono ancora **{errors_left}** errori da correggere.")
            st.button("TORNA AL MENU", type="primary", on_click=reset_game, kwargs={'exam': False})

        elif st.session_state.exam_mode:
            allowed_errors = 4 if "Base" in st.session_state.quiz_mode else 1
            passed = st.session_state.score_ko <= allowed_errors
            if passed:
                st.markdown(f"""<div class="exam-pass"><h1>🎉 SUPERATO! 🎉</h1><p>Hai fatto solo {st.session_state.score_ko} errori.</p></div>""", unsafe_allow_html=True)
                st.balloons()
            else:
                st.markdown(f"""<div class="exam-fail"><h1>🚫 NON SUPERATO</h1><p>Troppi errori ({st.session_state.score_ko}). Il massimo consentito è {allowed_errors}.</p></div>""", unsafe_allow_html=True)
            st.button("🔄 NUOVA SIMULAZIONE", type="primary", on_click=reset_game, kwargs={'exam': True})
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.current_row is not None:
        row = st.session_state.current_row
        
        if st.session_state.debug_mode:
            ukey = get_unique_key(row.get('ID Progressivo'))
            val = st.session_state.history.get(ukey)
            w = calculate_weight(val)
            status_text = "🆕 MAI VISTA"
            if val == -1: status_text = "🔴 ERRORE ATTIVO"
            elif val is not None and val > 0: status_text = f"🟢 CORRETTA {val} VOLTE"
            st.markdown(f"""<div class="debug-info">🔧 <b>DEBUG:</b> ID {row.get('ID Progressivo')} | Status: <b>{status_text}</b> | Peso: <b>{w:.2f}</b></div>""", unsafe_allow_html=True)

        if "Carteggio" in st.session_state.quiz_mode:
            st.markdown(f"**Esercizio {row.get('ID Progressivo')}**")
            st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
            if not st.session_state.answered:
                if st.button("👁️ MOSTRA SOLUZIONE", type="primary"): st.session_state.answered = True; st.rerun()
            else:
                sol_data = {"Parametro": ["Distanza", "Velocità", "Carburante", "Partenza", "Arrivo"], "Soluzione": [row.get(f'Soluzione {i+1}') for i in range(5)]}
                st.table(pd.DataFrame(sol_data))
                c1, c2 = st.columns(2)
                if c1.button("✅ GIUSTO"): answer(True); next_question(); st.rerun()
                if c2.button("❌ SBAGLIATO"): answer(False); next_question(); st.rerun()
        else:
            c1, c2 = st.columns([1, 2], gap="small")
            with c1:
                pth = get_image_path(row.get('NomeImmagine'))
                if pth: st.image(Image.open(pth), use_container_width=True)
                else: st.markdown("<div class='placeholder-img'>⚓<br>NO IMMAGINE</div>", unsafe_allow_html=True)
            with c2:
                # --- QUIZ BOX SOLIDO AGGIORNATO (LAYOUT RICHIESTO) ---
                st.markdown(f"""
                <div class="question-box">
                    <div class="question-header">
                        <span class="question-id">DOMANDA {row.get('ID Progressivo')}</span>
                        <span class="question-topic">{row.get('Argomento')} - <i>{row.get('Voce','')}</i></span>
                    </div>
                    <div class="question-text">{row.get('Domanda')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                for i, opt in enumerate(st.session_state.shuffled_options):
                    if st.session_state.answered:
                        bg = "#d1e7dd" if opt['ok'] else "#f8d7da" 
                        icon = "✅" if opt['ok'] else "❌"
                        st.markdown(f"<div class='result-box' style='background:{bg};'>{icon} {opt['txt']}</div>", unsafe_allow_html=True)
                    else:
                        if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}"): 
                            answer(opt['ok'])
                            st.rerun()
                
                if st.session_state.answered:
                    q_url = urllib.parse.quote(f"Patente nautica spiegazione {row.get('Domanda','')}")
                    st.markdown(f'<a href="https://www.google.com/search?q={q_url}" target="_blank" class="google-box" style="text-align:center">💡 <b>Approfondimento:</b> Cerca su Google</a>', unsafe_allow_html=True)
                    if st.button("PROSSIMA DOMANDA ➡", type="primary"): 
                        next_question()
                        st.rerun()

    if st.session_state.current_row is None: 
        reset_game(False)
        st.rerun()
