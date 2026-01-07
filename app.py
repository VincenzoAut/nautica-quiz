# --- VERSIONE APP: v39.2 (Clean Logic & Layout Stabile) ---
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import time
import datetime
import random
import urllib.parse
from PIL import Image

# --- IMPORT MODULI PROPRIETARI ---
import database as db_engine
import logic as brain
import ui 

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Patente Nautica v39.2", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

# UI SETUP
ui.set_backgrounds(os.path.join(BASE_DIR, "background.jpg"), os.path.join(BASE_DIR, "background2.jpg"))
ui.load_css()

# --- CSS MIRATO ---
st.markdown("""
<style>
    button[title^="Sposta"] { background-color: #28a745 !important; color: white !important; border-color: #28a745 !important; }
    button[title^="Sposta"]:hover { background-color: #218838 !important; }
    button[title^="Segna"] { background-color: #dc3545 !important; color: white !important; border-color: #dc3545 !important; }
    button[title^="Segna"]:hover { background-color: #c82333 !important; }
    .cart-result { background-color: #d1e7dd; border-left: 5px solid #198754; padding: 10px; margin-bottom: 5px; border-radius: 5px; color: #0f5132; font-weight: bold; }
    .result-box { padding: 10px; border-radius: 5px; margin-bottom: 5px; color: black; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE STATO ---
if 'init' not in st.session_state:
    st.session_state.current_user = None
    st.session_state.quiz_mode = "Quiz Base"
    st.session_state.exam_mode = False
    st.session_state.review_mode = False
    st.session_state.stats_mode = False
    st.session_state.admin_mode = False
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.exam_questions = []
    st.session_state.current_row = None
    st.session_state.answered = False
    st.session_state.shuffled_options = []
    st.session_state.end_timestamp = 0 
    st.session_state.start_time = 0     
    st.session_state.exam_finished = False
    st.session_state.history = {} 
    st.session_state.init = True

# --- 3. LOGICA IMMAGINI (NUOVA & PULITA) ---

@st.cache_data(show_spinner=False)
def load_raccordo_map():
    """Carica il file Raccordo e crea una mappa {ID: NomeFile}."""
    if not os.path.exists(FILE_RACCORDO): return {}
    try:
        df = pd.read_excel(FILE_RACCORDO)
        df.columns = [str(c).strip() for c in df.columns]
        
        col_id = 'ID Progressivo' if 'ID Progressivo' in df.columns else ('Progressivo' if 'Progressivo' in df.columns else None)
        col_img = 'Immagine' if 'Immagine' in df.columns else None
        
        if col_id and col_img:
            # Crea dizionario pulendo gli ID
            return dict(zip(
                df[col_id].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(),
                df[col_img].astype(str).str.strip()
            ))
    except: return {}
    return {}

def get_image_path_for_question(question_id):
    """Restituisce il path dell'immagine per un dato ID domanda."""
    if not question_id: return None
    
    # 1. Cerca nel mapping Excel
    raccordo_map = load_raccordo_map()
    clean_id = str(question_id).replace('.0','').strip()
    img_name = raccordo_map.get(clean_id)
    
    if not img_name: return None 
    
    # 2. Cerca il file su disco
    target_path = os.path.join(CARTELLA_IMMAGINI, img_name)
    
    if os.path.exists(target_path): return target_path
    
    # Fallback: cerca file con estensione diversa o senza
    name_no_ext = os.path.splitext(img_name)[0].lower()
    for f in os.listdir(CARTELLA_IMMAGINI):
        if os.path.splitext(f)[0].lower() == name_no_ext:
            return os.path.join(CARTELLA_IMMAGINI, f)
            
    return None

# --- 4. CARICAMENTO DATI (SEMPLIFICATO) ---
@st.cache_data
def load_data(mode):
    # Carica SOLO il database delle domande, senza merge inutili
    target_file = FILE_CARTEGGIO if "Carteggio" in mode else (FILE_QUIZ_VELA if "Vela" in mode else FILE_QUIZ_BASE)
    if not os.path.exists(target_file): return None
    try:
        df = pd.read_excel(target_file)
        df.columns = [str(c).strip() for c in df.columns]
        if 'ID Progressivo' in df.columns: 
            df['ID Progressivo'] = df['ID Progressivo'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        if 'Spiegazione' not in df.columns: df['Spiegazione'] = ""
        df['Spiegazione'] = df['Spiegazione'].fillna("")
        return df
    except Exception as e:
        st.error(f"Errore DB: {e}")
        return None

# --- 5. UTILS GIOCO ---
def get_user_rank(mastered_count):
    if mastered_count < 100: return "🧹 Mozzo", 100
    if mastered_count < 300: return "⚓ Marinaio", 300
    if mastered_count < 500: return "🧭 Nostromo", 500
    if mastered_count < 700: return "🛳️ Comandante", 700
    return "🐺 Lupo di Mare", 1000

def finalize_exam(): st.session_state.exam_finished = True

def check_time_limit():
    if st.session_state.exam_mode and st.session_state.end_timestamp > 0:
        if time.time() > (st.session_state.end_timestamp + 2): finalize_exam(); return False
    return True

def reset_game(exam=False, review=False, stats=False):
    st.session_state.exam_mode = exam
    st.session_state.review_mode = review
    st.session_state.stats_mode = stats
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.answered = False
    st.session_state.exam_finished = False
    st.session_state.exam_questions = [] 
    st.session_state.start_time = time.time()
    
    duration = 0
    if exam:
        if "Vela" in st.session_state.quiz_mode: duration = 15 * 60
        elif "Carteggio" in st.session_state.quiz_mode: duration = 60 * 60
        else: duration = 30 * 60
        st.session_state.end_timestamp = st.session_state.start_time + duration
    else: st.session_state.end_timestamp = 0

    db = load_data(st.session_state.quiz_mode)
    if db is None: return

    if not stats:
        if review:
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Ripasso")
            if len(subset) == 0: st.success("🎉 Nessun ripasso!"); st.session_state.review_mode = False; return
            st.session_state.exam_questions = subset.to_dict('records'); load_question()
        elif exam:
            if "Vela" in st.session_state.quiz_mode: st.session_state.exam_questions = db.sample(5).to_dict('records')
            elif "Carteggio" in st.session_state.quiz_mode: st.session_state.exam_questions = db.sample(5).to_dict('records')
            else: st.session_state.exam_questions = brain.get_balanced_exam_questions(db).to_dict('records')
            load_question()
        else:
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Allenamento")
            st.session_state.exam_questions = subset.to_dict('records'); load_question()

def load_question():
    if st.session_state.exam_questions and st.session_state.exam_index < len(st.session_state.exam_questions):
        st.session_state.current_row = st.session_state.exam_questions[st.session_state.exam_index]
        prepare_options()
    else: finalize_exam()

def prepare_options():
    row = st.session_state.current_row
    if row is not None and "Carteggio" not in st.session_state.quiz_mode:
        corretta = str(row.get('Risposta Esatta','')).strip().upper()
        opts = [{'txt': row.get('Risposta A'), 'ok': corretta=='A'},
                {'txt': row.get('Risposta B'), 'ok': corretta=='B'},
                {'txt': row.get('Risposta C'), 'ok': corretta=='C'}]
        st.session_state.shuffled_options = [o for o in opts if pd.notna(o['txt'])]
        random.shuffle(st.session_state.shuffled_options)

def answer(is_correct):
    if not check_time_limit(): return 
    if not st.session_state.answered:
        st.session_state.answered = True
        id_dom = str(st.session_state.current_row.get('ID Progressivo')).strip()
        item_data = st.session_state.history.get(id_dom, {'score': 0, 'date': ''})
        new_score = item_data['score'] + 1 if (is_correct and item_data['score'] > 0) else (1 if is_correct else -1)
        st.session_state.history[id_dom] = {'score': new_score, 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        db_engine.upsert_answer(st.session_state.current_user, id_dom, new_score)
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

def skip_current_question():
    if not check_time_limit(): return
    remaining = len(st.session_state.exam_questions) - st.session_state.exam_index
    if remaining <= 1: st.warning("⚠️ È l'ultima!"); return
    current_q = st.session_state.exam_questions.pop(st.session_state.exam_index)
    st.session_state.exam_questions.append(current_q); st.session_state.answered = False; st.toast("Saltata!"); load_question()

def next_question():
    if not check_time_limit(): return
    st.session_state.answered = False
    if st.session_state.exam_index + 1 < len(st.session_state.exam_questions):
        st.session_state.exam_index += 1; load_question()
    else: finalize_exam()

# --- 6. LOGIN ---
if st.session_state.current_user is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        ui.draw_login_header("v39.2 • Stable")
        st.markdown("### 🔐 Accesso Allievi")
        c_in1, c_in2 = st.columns(2)
        with c_in1: name_input = st.text_input("👤 Nome").strip()
        with c_in2: pin_input = st.text_input("🔑 PIN", type="password", max_chars=4).strip()
        st.markdown("<br>", unsafe_allow_html=True)
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("REGISTRATI 📝", use_container_width=True):
                 if not name_input or len(pin_input) < 3: st.error("Dati invalidi")
                 elif db_engine.check_user_exists(name_input): st.warning("Esistente")
                 elif db_engine.register_user(name_input, pin_input): st.success("Ok")
        with cb2:
            if st.button("ENTRA ✅", type="primary", use_container_width=True):
                if name_input and db_engine.verify_pin(name_input, pin_input):
                    with st.spinner("Accesso..."):
                        raw = db_engine.fetch_user_history(name_input)
                        st.session_state.history = {str(k).replace('.0','').strip(): v for k, v in raw.items()}
                        st.session_state.current_user = name_input; st.rerun()
                elif name_input.lower() == "admin" and pin_input == "0000":
                     st.session_state.current_user = "Ammiraglio"; st.session_state.admin_mode = True; st.rerun()
                else: st.error("Credenziali Errate")

        st.markdown("---")
        with st.expander("ℹ️ INFO E GUIDA ALL'USO"):
            st.markdown("""
            **⚓ A cosa serve questa App?**
            Questa applicazione è uno strumento professionale progettato per portarti al conseguimento della **Patente Nautica** (Entro 12 miglia e Senza Limiti), simulando fedelmente l'esperienza d'esame e ottimizzando i tempi di studio.

            ---

            ### **1. 🎓 SIMULAZIONE ESAME (Due Logiche diverse)**
            Questa modalità replica l'esame ufficiale secondo il **Decreto Direttoriale n. 131 del 31/05/2022**.

            * **🅰️ QUIZ BASE (Motore): Logica "A Cassetti"**
                Il sistema **NON** pesca 20 domande a caso, ma rispetta la distribuzione rigida di legge:
                * 1 Teoria dello Scafo, 1 Motori
                * 3 Sicurezza, 4 Manovra e Condotta
                * 2 Colreg/Segnalamento, 2 Meteorologia
                * 4 Navigazione, 3 Normativa
                * *Regole:* Tempo 30 min | Max 4 Errori.

            * **⛵ QUIZ VELA (Integrazione): Logica "Pura Casuale"**
                A differenza del Base, qui non ci sono sottocategorie vincolanti. Il sistema estrae **5 domande casuali** dall'intero database specifico della Vela.
                * *Regole:* Tempo 15 min | Max 1 Errore.

            ---

            ### **2. ♾️ ALLENAMENTO SMART (Metodo SRS)**
            Qui l'obiettivo non è valutarti, ma insegnarti. L'algoritmo **SRS (Spaced Repetition System)** si adatta al tuo livello:
            * 🔴 **Se sbagli:** La domanda viene riproposta subito.
            * 🟢 **Se indovini:** L'algoritmo la nasconde per 3 giorni.
            * 🟢🟢 **Se confermi:** La nasconde per 7, poi 15 giorni.
            * *Il sistema ti interroga solo su ciò che stai per dimenticare.*

            ---

            ### **3. 🔄 RIPASSO ERRORI**
            Un filtro speciale che isola dal database solo i quiz attualmente "rossi" (sbagliati e non ancora corretti), permettendoti di azzerare le tue lacune.
            
            ---
            
            ### **4. ⚡ GESTIONE DOMANDE**
            * **⏭️ SALTA (Verde):** Se hai un dubbio, sposta la domanda in fondo alla lista. Ti verrà riproposta alla fine, se rimane tempo.
            * **🚩 NON LA SO! (Rosso):** Segna la risposta come errata ma ti mostra subito la soluzione e la spiegazione.
            """)
    ui.draw_login_footer(); st.stop()

# --- 7. ADMIN ---
db = load_data(st.session_state.quiz_mode)
if st.session_state.admin_mode:
    st.markdown("## 👮‍♂️ Plancia Ammiraglio")
    if st.button("Esci (Logout)"):
        st.session_state.current_user = None
        st.session_state.admin_mode = False
        st.rerun()
    
    st.info("Monitoraggio Globale.")
    all_data = db_engine.fetch_all_stats()
    
    if all_data:
        df_all = pd.DataFrame(all_data)
        df_all.columns = [str(c).strip().lower() for c in df_all.columns]
        
        col_u = next((c for c in df_all.columns if 'utente' in c), None)
        col_t = next((c for c in df_all.columns if 'timestamp' in c), None)
        
        tot_users = df_all[col_u].nunique() if col_u else 0
        tot_answers = len(df_all)
        
        active_today = 0
        if col_t and col_u:
             df_all['dt'] = pd.to_datetime(df_all[col_t], errors='coerce')
             active_today = df_all[df_all['dt'].dt.date == datetime.date.today()][col_u].nunique()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Studenti Totali", tot_users)
        c2.metric("Attivi Oggi", active_today)
        c3.metric("Quiz Svolti", tot_answers)
        
        st.divider()
        if col_u:
            ranking = df_all.groupby(col_u).size().reset_index(name='Risposte').sort_values('Risposte', ascending=False)
            st.dataframe(ranking.head(50), use_container_width=True, hide_index=True)
            
        with st.expander("📥 Scarica Log Completo"):
            st.dataframe(df_all, use_container_width=True)
    else: st.warning("DB Vuoto.")
    st.stop()

# --- 8. SIDEBAR ---
with st.sidebar:
    st.title("⚓ Patente Nautica")
    st.markdown(f"👤 **{st.session_state.current_user}**")
    if st.button("🚪 Esci"): st.session_state.current_user = None; st.rerun()
    
    mastered = len([v for v in st.session_state.history.values() if v['score'] > 0])
    rank_n, rank_t = get_user_rank(mastered)
    ui.draw_rank_box(rank_n, mastered, rank_t)
    st.progress(min(mastered / rank_t, 1.0))

    mode = st.radio("Materia:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"])
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode; st.session_state.current_row = None
        st.session_state.exam_questions = []; st.session_state.exam_mode = False; st.session_state.stats_mode = False; st.rerun()

    st.button("🎓 SIMULAZIONE ESAME", type="primary", on_click=reset_game, kwargs={'exam': True})
    st.button("♾️ ALLENAMENTO SMART", on_click=reset_game, kwargs={'exam': False})
    st.divider()
    
    if db is not None:
        curr_ids = set(db['ID Progressivo'].astype(str))
        errs = 0
        for k, v in st.session_state.history.items():
            if v['score'] == -1 and str(k).replace('.0','').strip() in curr_ids: errs += 1
        if errs > 0: 
            st.error(f"⚠️ **{errs} Errori Attivi**")
            st.button("🔄 RIPASSA ERRORI", on_click=reset_game, kwargs={'review': True})
    
    st.button("📊 STATISTICHE", on_click=reset_game, kwargs={'stats': True})
    st.markdown("---")
    with st.expander("⚠️ SEGNALA ERRORE"):
        with st.form("rep"):
            msg = st.text_area("Msg:"); sent = st.form_submit_button("Invia")
            if sent: db_engine.save_report_to_db(st.session_state.current_user, str(st.session_state.current_row.get('ID Progressivo','')), msg); st.success("Inviato")
    st.markdown(f"<div class='footer-sidebar'><b>v39.2</b> • {datetime.datetime.now().strftime('%d/%m')}</div>", unsafe_allow_html=True)

# --- 9. MAIN ---
icon = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}.get(st.session_state.quiz_mode, '⚓')

if st.session_state.stats_mode:
    # --- DASHBOARD STATISTICHE ---
    st.markdown(f"## 📊 Dashboard: {st.session_state.quiz_mode}")
    mem_data = []
    current_ids = set(db['ID Progressivo'].astype(str))
    
    for k, v in st.session_state.history.items():
        if k in current_ids: mem_data.append({'ID Progressivo': k, 'Score': v['score'], 'Date': v['date']})
    
    if len(mem_data) > 0:
        df_mem = pd.DataFrame(mem_data)
        df_full = pd.merge(db, df_mem, on='ID Progressivo', how='inner')
    else: df_full = pd.DataFrame(columns=list(db.columns) + ['Score', 'Date'])

    tot_risposte = len(df_full)
    tot_master = len(df_full[df_full['Score'] > 0])
    tot_errori = len(df_full[df_full['Score'] == -1])
    
    c1, c2, c3 = st.columns(3)
    with c1: ui.draw_stat_metric("Domande Svolte", tot_risposte, "Totale", "blue")
    with c2: ui.draw_stat_metric("Consolidate", f"{tot_master}", "Risposte OK", "green")
    with c3: ui.draw_stat_metric("Errori Attivi", tot_errori, "Urgenti", "red")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 Dettaglio", "📉 Punti Deboli", "🗓️ Trend"])
    
    with tab1:
        st.markdown("### 📋 Stato Avanzamento")
        if 'Argomento' in db.columns:
            df_full['IsMaster'] = df_full['Score'] > 0
            df_full['IsError'] = df_full['Score'] == -1
            
            user_stats = df_full.groupby('Argomento').agg(Consolidate=('IsMaster', 'sum'), Errori=('IsError', 'sum')).reset_index()
            total_stats = db.groupby('Argomento').agg(Totale=('ID Progressivo', 'count')).reset_index()
            
            final_table = pd.merge(total_stats, user_stats, on='Argomento', how='left').fillna(0)
            final_table['% Completamento'] = (final_table['Consolidate'] / final_table['Totale'] * 100).astype(int)
            final_table = final_table.sort_values(by='% Completamento', ascending=False)
            
            sum_totale = final_table['Totale'].sum()
            sum_consolidate = final_table['Consolidate'].sum()
            sum_errori = final_table['Errori'].sum()
            perc_totale = int((sum_consolidate / sum_totale * 100) if sum_totale > 0 else 0)
            
            total_row = pd.DataFrame([{
                'Argomento': '--- TOTALE GENERALE ---', 
                'Totale': sum_totale,
                'Consolidate': sum_consolidate, 
                'Errori': sum_errori, 
                '% Completamento': perc_totale
            }])
            
            final_table = pd.concat([final_table, total_row], ignore_index=True)
            st.dataframe(final_table, hide_index=True, use_container_width=True)
    
    with tab2:
        if len(df_full) > 0 and 'Argomento' in df_full.columns:
            err_df = df_full[df_full['Score'] == -1]
            if len(err_df) > 0:
                st.bar_chart(err_df['Argomento'].value_counts(), color="#ff4b4b")
            else: st.success("Nessun errore attivo!")
            
    with tab3:
        if len(df_full) > 0 and 'Date' in df_full.columns:
            df_trend = df_full[df_full['Date'] != ""].copy()
            if not df_trend.empty:
                df_trend['Day'] = pd.to_datetime(df_trend['Date']).dt.date
                st.line_chart(df_trend.groupby('Day').count()['ID Progressivo'])

    if st.button("Torna al Quiz"): st.session_state.stats_mode = False; st.rerun()

else:
    t_suffix = "Ripasso" if st.session_state.review_mode else ("Simulazione" if st.session_state.exam_mode else "Allenamento")
    
    if st.session_state.exam_mode and st.session_state.end_timestamp > 0 and not st.session_state.exam_finished:
        end_js = int(st.session_state.end_timestamp * 1000)
        components.html(f"""
        <div style="font-family:sans-serif; display:flex; justify-content:space-between; align-items:center; background:white; padding:10px; border-radius:8px; border: 1px solid #ddd; box-sizing: border-box; height: 100%;">
            <div style="font-weight:bold; color: #333;">{icon} {st.session_state.quiz_mode} - <i>{t_suffix}</i></div>
            <div id="cnt" style="background:#f8f9fa; border:2px solid #ff4b4b; color:#d9534f; padding:5px 15px; border-radius:8px; font-weight:bold; font-size:20px;"></div>
        </div>
        <script>
        setInterval(function() {{
            var dist = {end_js} - new Date().getTime();
            if (dist < 0) {{ document.getElementById("cnt").innerHTML = "SCADUTO"; }}
            else {{
                var m = Math.floor((dist % (1000*60*60))/(1000*60));
                var s = Math.floor((dist % (1000*60))/1000);
                document.getElementById("cnt").innerHTML = "⏱️ " + (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
            }}
        }}, 1000);
        </script>
        """, height=85)
        if time.time() > (st.session_state.end_timestamp + 2): finalize_exam(); st.rerun()
    else: st.markdown(f"## {icon} {st.session_state.quiz_mode} - *{t_suffix}*")

    if not st.session_state.exam_finished:
        done = st.session_state.score_ok + st.session_state.score_ko
        tot = len(st.session_state.exam_questions)
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-box"><div>Fatte</div><div>{done}/{tot}</div></div>
            <div class="metric-box"><div>Esatte</div><div style="color:green">{st.session_state.score_ok}</div></div>
            <div class="metric-box"><div>Errori</div><div style="color:red">{st.session_state.score_ko}</div></div>
        </div>
        """, unsafe_allow_html=True)
        if tot > 0: st.progress(done/tot)
        st.caption(f"📝 **Domanda {done + 1} di {tot}**")

    if st.session_state.exam_finished:
        st.markdown('<div class="question-card">', unsafe_allow_html=True)
        limit = 4 if "Base" in st.session_state.quiz_mode else 1
        if st.session_state.exam_mode:
            if st.session_state.score_ko <= limit: st.markdown(f"<div class='exam-pass'><h1>🎉 SUPERATO!</h1><p>Errori: {st.session_state.score_ko}</p></div>", unsafe_allow_html=True); st.balloons()
            else: st.markdown(f"<div class='exam-fail'><h1>🚫 NON SUPERATO</h1><p>Errori: {st.session_state.score_ko}</p></div>", unsafe_allow_html=True)
        else: st.markdown("<div class='review-end'><h1>✅ Fine Sessione</h1></div>", unsafe_allow_html=True)
        st.button("🔄 NUOVA SESSIONE", type="primary", on_click=reset_game, kwargs={'exam': st.session_state.exam_mode})
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.current_row is not None:
        row = st.session_state.current_row
        
        if "Carteggio" in st.session_state.quiz_mode:
             c1, c2 = st.columns([1, 2], gap="small")
             with c1:
                 # Immagine Carteggio (width=350)
                 path_img = get_image_path_for_question(row.get('ID Progressivo'))
                 if path_img: st.image(Image.open(path_img), width=350)

             with c2:
                 st.markdown(f"**Esercizio {row.get('ID Progressivo')}**")
                 st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
                 with st.expander("🧮 TOOLBOX", expanded=False):
                    tabs = st.tabs(["V/S/T", "Carburante", "Rotta"])
                    with tabs[0]:
                        cm = st.radio("Calcola:", ["V", "S", "T"], horizontal=True)
                        if cm=="V": s=st.number_input("S (Nm)"); t=st.number_input("T (min)"); st.write(f"V = {s/(t/60):.2f}" if t else "")
                        elif cm=="S": v=st.number_input("V (Kn)"); t=st.number_input("T (min)"); st.write(f"S = {v*(t/60):.2f}")
                        else: s=st.number_input("S (Nm)"); v=st.number_input("V (Kn)"); st.write(f"T = {int(s/v*60)}" if v else "")
                 st.markdown("---")
                 if not st.session_state.answered:
                     if st.button("👁️ MOSTRA SOLUZIONE", type="primary", use_container_width=True): st.session_state.answered = True; st.rerun()
                 else:
                     cols = sorted([c for c in row.keys() if str(c).startswith('Soluzione')])
                     st.success("✅ SOLUZIONE UFFICIALE")
                     for c in cols: 
                         if pd.notna(row.get(c)): st.markdown(f"<div class='cart-result'>{c}: {row.get(c)}</div>", unsafe_allow_html=True)
                     c1_b, c2_b = st.columns(2)
                     if c1_b.button("GIUSTO ✅", use_container_width=True): answer(True); next_question(); st.rerun()
                     if c2_b.button("SBAGLIATO ❌", type="primary", use_container_width=True): answer(False); next_question(); st.rerun()
        else:
            # Layout Quiz Base - 2 Colonne
            c1, c2 = st.columns([1, 2], gap="small")
            
            with c1:
                # Immagine ridimensionata 350px
                path_img = get_image_path_for_question(row.get('ID Progressivo'))
                if path_img: 
                    st.image(Image.open(path_img), width=350)
                else:
                    pass

            with c2:
                ui.draw_question_card(row.get('ID Progressivo'), row.get('Argomento'), row.get('Voce', ''), row.get('Domanda'))
                if st.session_state.answered:
                    for i, opt in enumerate(st.session_state.shuffled_options):
                        bg = "#d1e7dd" if opt['ok'] else "#f8d7da"; icon = "✅" if opt['ok'] else "❌"
                        st.markdown(f"<div class='result-box' style='background:{bg};'>{icon} {opt['txt']}</div>", unsafe_allow_html=True)
                    st.divider()
                    expl = str(row.get('Spiegazione', '')).strip()
                    if expl: st.info(f"📘 Spiegazione: {expl}")
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("PROSSIMA ➡", type="primary", use_container_width=True): next_question(); st.rerun()
                else:
                    for i, opt in enumerate(st.session_state.shuffled_options):
                        if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}", use_container_width=True): answer(opt['ok']); st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    c_skip, c_idk = st.columns(2)
                    with c_skip:
                        if st.session_state.exam_mode and st.button("⏭️ SALTA", use_container_width=True): skip_current_question(); st.rerun()
                    with c_idk:
                        if st.button("🚩 Non la so!", use_container_width=True): answer(False); st.rerun()
    if st.session_state.current_row is None: reset_game(False); st.rerun()