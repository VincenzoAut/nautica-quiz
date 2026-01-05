# --- VERSIONE APP: v31.0 (Progress Bar Restore & Full Features) ---
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
# Assicurati che i file database.py, logic.py e ui.py siano nella stessa cartella
import database as db_engine
import logic as brain
import ui 

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Patente Nautica v31.0", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

# UI SETUP
ui.set_backgrounds(os.path.join(BASE_DIR, "background.jpg"), os.path.join(BASE_DIR, "background2.jpg"))
ui.load_css()

# --- CSS MIRATO (Colori Bottoni) ---
st.markdown("""
<style>
    /* Bottone SALTA -> VERDE (Identificato dal tooltip 'Sposta...') */
    button[title^="Sposta"] {
        background-color: #28a745 !important;
        border-color: #28a745 !important;
        color: white !important;
    }
    button[title^="Sposta"]:hover {
        background-color: #218838 !important;
        border-color: #1e7e34 !important;
    }

    /* Bottone NON LA SO -> ROSSO (Identificato dal tooltip 'Segna...') */
    button[title^="Segna"] {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
        color: white !important;
    }
    button[title^="Segna"]:hover {
        background-color: #c82333 !important;
        border-color: #bd2130 !important;
    }
    
    /* Box Carteggio */
    .cart-result {
        background-color: #d1e7dd;
        border-left: 5px solid #198754;
        padding: 10px;
        margin-bottom: 5px;
        border-radius: 5px;
        color: #0f5132;
        font-weight: bold;
    }
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

# --- 3. CARICAMENTO DATI ---
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
        df = pd.read_excel(f)
        df.columns = [str(c).strip() for c in df.columns]
        if 'ID Progressivo' in df.columns: df['ID Progressivo'] = df['ID Progressivo'].astype(str)
        
        if 'Spiegazione' not in df.columns: df['Spiegazione'] = ""
        df['Spiegazione'] = df['Spiegazione'].fillna("")

        if "Base" in mode and os.path.exists(FILE_RACCORDO):
            dfr = pd.read_excel(FILE_RACCORDO)
            dfr.columns = [c.strip() for c in dfr.columns]
            if 'Progressivo' in dfr.columns and 'Immagine' in dfr.columns:
                df = pd.merge(df, dfr[['Progressivo', 'Immagine']], left_on='ID Progressivo', right_on='Progressivo', how='left')
                df.rename(columns={'Immagine': 'NomeImmagine'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return None

# --- 4. FUNZIONI UTILI ---
def get_user_rank(mastered_count):
    if mastered_count < 100: return "🧹 Mozzo", 100
    if mastered_count < 300: return "⚓ Marinaio", 300
    if mastered_count < 500: return "🧭 Nostromo", 500
    if mastered_count < 700: return "🛳️ Comandante", 700
    return "🐺 Lupo di Mare", 1000

def finalize_exam():
    st.session_state.exam_finished = True

def check_time_limit():
    if st.session_state.exam_mode and st.session_state.end_timestamp > 0:
        now = time.time()
        if now > (st.session_state.end_timestamp + 2):
            finalize_exam()
            return False
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
    
    now = time.time()
    st.session_state.start_time = now
    
    duration = 0
    if exam:
        if "Vela" in st.session_state.quiz_mode: duration = 15 * 60
        elif "Carteggio" in st.session_state.quiz_mode: duration = 60 * 60
        else: duration = 30 * 60
        st.session_state.end_timestamp = now + duration
    else:
        st.session_state.end_timestamp = 0

    db = load_data(st.session_state.quiz_mode)
    if db is None: return

    if not stats:
        if review:
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Ripasso")
            if len(subset) == 0:
                st.success("🎉 Nessun ripasso in scadenza!")
                st.session_state.review_mode = False
                return
            st.session_state.exam_questions = subset.to_dict('records')
            load_question()
        elif exam:
            if "Vela" in st.session_state.quiz_mode:
                st.session_state.exam_questions = db.sample(5).to_dict('records')
            elif "Carteggio" in st.session_state.quiz_mode:
                st.session_state.exam_questions = db.sample(5).to_dict('records')
            else:
                balanced_df = brain.get_balanced_exam_questions(db)
                st.session_state.exam_questions = balanced_df.to_dict('records')
            load_question()
        else:
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Allenamento")
            st.session_state.exam_questions = subset.to_dict('records')
            load_question()

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
        opts = [o for o in opts if pd.notna(o['txt'])]
        random.shuffle(opts)
        st.session_state.shuffled_options = opts

def answer(is_correct):
    if not check_time_limit(): return 

    if not st.session_state.answered:
        st.session_state.answered = True
        id_dom = str(st.session_state.current_row.get('ID Progressivo'))
        item_data = st.session_state.history.get(id_dom, {'score': 0, 'date': ''})
        new_score = 1 if is_correct else -1
        if is_correct and item_data['score'] > 0: new_score = item_data['score'] + 1
        st.session_state.history[id_dom] = {'score': new_score, 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        db_engine.upsert_answer(st.session_state.current_user, id_dom, new_score)
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

def skip_current_question():
    if not check_time_limit(): return
    
    remaining = len(st.session_state.exam_questions) - st.session_state.exam_index
    if remaining <= 1:
        st.warning("⚠️ È l'ultima domanda rimasta! Devi rispondere.")
        return

    current_q = st.session_state.exam_questions.pop(st.session_state.exam_index)
    st.session_state.exam_questions.append(current_q)
    st.session_state.answered = False
    
    st.toast("Domanda rimandata alla fine! ⏭️")
    load_question()

def next_question():
    if not check_time_limit(): return
    st.session_state.answered = False
    if st.session_state.exam_index + 1 < len(st.session_state.exam_questions):
        st.session_state.exam_index += 1
        load_question()
    else: finalize_exam()

# --- 5. LOGIN SYSTEM ---
if st.session_state.current_user is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        ui.draw_login_header("v31.0 • Stable")
        
        st.markdown("### 🔐 Accesso Allievi")
        col_in1, col_in2 = st.columns(2)
        with col_in1: name_input = st.text_input("👤 Nome", placeholder="Es. Vincenzo").strip()
        with col_in2: pin_input = st.text_input("🔑 PIN (4 cifre)", type="password", max_chars=4).strip()
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            if st.button("REGISTRATI 📝", type="secondary", use_container_width=True):
                 if not name_input or len(pin_input) < 3: st.error("Inserisci Nome e PIN valido.")
                 elif name_input.lower() == "admin": st.error("Nome riservato.")
                 else:
                    if db_engine.check_user_exists(name_input): st.warning("Utente già registrato.")
                    elif db_engine.register_user(name_input, pin_input): st.success("Registrato! Entra.")
                    else: st.error("Errore DB.")

        with col_b2:
            if st.button("ENTRA ✅", type="primary", use_container_width=True):
                if name_input and db_engine.verify_pin(name_input, pin_input):
                    with st.spinner("Caricamento..."):
                        hist = db_engine.fetch_user_history(name_input)
                        st.session_state.history = hist
                        st.session_state.current_user = name_input
                        st.rerun()
                elif name_input.lower() == "admin" and pin_input == "0000":
                     st.session_state.current_user = "Ammiraglio"; st.session_state.admin_mode = True; st.rerun()
                else: st.error("Credenziali Errate.")

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
             
    ui.draw_login_footer()
    st.stop()

# --- 6. ADMIN & LOGIC ---
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

# --- 7. SIDEBAR ---
with st.sidebar:
    st.title("⚓ Patente Nautica")
    st.markdown(f"👤 **{st.session_state.current_user}**")
    if st.button("🚪 Esci"): st.session_state.current_user = None; st.rerun()
    
    mastered_count = len([v for v in st.session_state.history.values() if v['score'] > 0])
    rank_name, rank_target = get_user_rank(mastered_count)
    ui.draw_rank_box(rank_name, mastered_count, rank_target)
    st.progress(min(mastered_count / rank_target, 1.0))

    mode = st.radio("Materia:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"])
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode
        st.session_state.current_row = None
        st.session_state.exam_questions = []
        st.session_state.exam_mode = False; st.session_state.review_mode = False; st.session_state.stats_mode = False
        st.rerun()

    st.button("🎓 SIMULAZIONE ESAME", type="primary", on_click=reset_game, kwargs={'exam': True})
    st.button("♾️ ALLENAMENTO SMART", on_click=reset_game, kwargs={'exam': False})
    st.divider()
    
    current_ids = set(db['ID Progressivo'].astype(str))
    err_count = len([k for k, v in st.session_state.history.items() if v['score'] == -1 and k in current_ids])
    if err_count > 0:
        st.error(f"⚠️ **{err_count} Errori Attivi**")
        st.button("🔄 RIPASSA ERRORI", on_click=reset_game, kwargs={'review': True})
        
    st.button("📊 STATISTICHE", on_click=reset_game, kwargs={'stats': True})
    
    st.markdown("---")
    with st.expander("⚠️ SEGNALA ERRORE", expanded=False):
        with st.form("report_form"):
            report_msg = st.text_area("Descrivi:", placeholder="Errore...")
            if st.form_submit_button("Invia"):
                curr_id = str(st.session_state.current_row.get('ID Progressivo', 'Gen')) if st.session_state.current_row is not None else "Gen"
                db_engine.save_report_to_db(st.session_state.current_user, curr_id, report_msg)
                st.success("Inviato!")
    
    st.markdown(f"<div class='footer-sidebar'><b>v31.0</b> • {datetime.datetime.now().strftime('%d/%m')}</div>", unsafe_allow_html=True)

# --- 8. MAIN INTERFACE ---
current_icon = icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}.get(st.session_state.quiz_mode, '⚓')

if st.session_state.stats_mode:
    # --- DASHBOARD STATISTICHE COMPLETE ---
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
    title_suffix = "Ripasso" if st.session_state.review_mode else ("Simulazione Esame" if st.session_state.exam_mode else "Allenamento Smart")
    
    if st.session_state.exam_mode and st.session_state.end_timestamp > 0 and not st.session_state.exam_finished:
        end_time_js = int(st.session_state.end_timestamp * 1000)
        timer_code = f"""
        <!DOCTYPE html><html><head><style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .timer-box {{ display: flex; justify-content: space-between; align-items: center; background-color: white; padding: 10px; border-radius: 8px; }}
            .title {{ font-size: 18px; font-weight: bold; color: #333; }}
            .countdown {{ background-color: #f8f9fa; border: 2px solid #ff4b4b; color: #d9534f; padding: 5px 15px; border-radius: 8px; font-weight: bold; font-size: 24px; }}
        </style></head><body>
            <div class="timer-box">
                <div class="title">{current_icon} {st.session_state.quiz_mode} - <i>{title_suffix}</i></div>
                <div id="display" class="countdown">Calcolo...</div>
            </div>
            <script>
                var countDownDate = {end_time_js};
                var x = setInterval(function() {{
                    var now = new Date().getTime(); var distance = countDownDate - now;
                    if (distance < 0) {{ clearInterval(x); document.getElementById("display").innerHTML = "SCADUTO"; document.getElementById("display").style.backgroundColor = "#ffcccc"; }} 
                    else {{
                        var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                        var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                        document.getElementById("display").innerHTML = "⏱️ " + (minutes<10?"0"+minutes:minutes) + ":" + (seconds<10?"0"+seconds:seconds);
                    }}
                }}, 1000);
            </script>
        </body></html>
        """
        components.html(timer_code, height=60)
        if time.time() > (st.session_state.end_timestamp + 2):
            finalize_exam()
            st.rerun()
    else:
        st.markdown(f"## {current_icon} {st.session_state.quiz_mode} - *{title_suffix}*")

    if not st.session_state.exam_finished:
        tot_questions = len(st.session_state.exam_questions)
        answered_cnt = st.session_state.score_ok + st.session_state.score_ko
        
        # --- METRICHE & BARRA PROGRESSO (RIPRISTINATA) ---
        st.markdown(f'<div class="metric-container"><div class="metric-box"><div class="metric-label">Fatte</div><div class="metric-value">{answered_cnt}/{tot_questions}</div></div><div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div><div class="metric-box"><div class="metric-label">Errori</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div></div>', unsafe_allow_html=True)
        
        if tot_questions > 0: 
            st.progress(answered_cnt / tot_questions)
        
        # Logica caption: Se ho risposto a 5 domande, sto facendo la 6^.
        # Se ho saltato, l'indice non conta, conta quante ne ho fatte.
        current_q_num = answered_cnt + 1
        if current_q_num <= tot_questions:
            st.caption(f"📝 **Domanda {current_q_num} di {tot_questions}**")
        else:
            st.caption("🚀 Ultima domanda!")

    if st.session_state.exam_finished:
        st.markdown('<div class="question-card">', unsafe_allow_html=True)
        if st.session_state.exam_mode:
            allowed = 4 if "Base" in st.session_state.quiz_mode else 1
            if st.session_state.score_ko <= allowed:
                st.markdown(f"""<div class="exam-pass"><h1>🎉 SUPERATO! 🎉</h1><p>Errori: {st.session_state.score_ko}</p></div>""", unsafe_allow_html=True)
                st.balloons()
            else:
                st.markdown(f"""<div class="exam-fail"><h1>🚫 NON SUPERATO</h1><p>Errori: {st.session_state.score_ko}</p></div>""", unsafe_allow_html=True)
        else:
             st.markdown(f"""<div class="review-end"><h1>✅ Sessione Completata</h1></div>""", unsafe_allow_html=True)
        st.button("🔄 NUOVA SESSIONE", type="primary", on_click=reset_game, kwargs={'exam': st.session_state.exam_mode})
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.current_row is not None:
        row = st.session_state.current_row
        
        # --- CARTEGGIO LOGIC ---
        if "Carteggio" in st.session_state.quiz_mode:
             st.markdown(f"**Esercizio {row.get('ID Progressivo')}**")
             
             # Immagine
             pth = get_image_path(row.get('NomeImmagine'))
             if pth: st.image(Image.open(pth), use_container_width=True)
             
             # Testo
             st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
             
             # TOOLBOX SOTTO DOMANDA
             with st.expander("🧮 TOOLBOX NAVIGATORE (Calcolatrice)", expanded=False):
                tabs = st.tabs(["V/S/T", "Carburante", "Rotta"])
                with tabs[0]:
                    calc_mode = st.radio("Calcola:", ["Velocità (Kn)", "Spazio (Nm)", "Tempo (min)"], horizontal=True)
                    if calc_mode == "Velocità (Kn)":
                        s = st.number_input("Spazio (Nm)", 0.0, step=0.1)
                        t = st.number_input("Tempo (min)", 0.0, step=1.0)
                        if t>0: st.markdown(f"**V = {s/(t/60):.2f} kn**")
                    elif calc_mode == "Spazio (Nm)":
                        v = st.number_input("Vel (Kn)", 0.0, step=0.1)
                        t = st.number_input("Tempo (min)", 0.0, step=1.0)
                        if v>0: st.markdown(f"**S = {v*(t/60):.2f} nm**")
                    else:
                        s = st.number_input("Spazio (Nm)", 0.0, step=0.1)
                        v = st.number_input("Vel (Kn)", 0.0, step=0.1)
                        if v>0: st.markdown(f"**T = {int((s/v)*60)} min**")
                with tabs[1]:
                    cons = st.number_input("Litri/h", 0.0)
                    ore = st.number_input("Ore", 0.0)
                    st.write(f"Totale (+30%): **{(cons*ore*1.3):.1f} L**")
                with tabs[2]:
                    pb = st.number_input("Pb", 0, 360)
                    d = st.number_input("d (+/-)", -20.0, 20.0, step=0.1)
                    dev = st.number_input("δ (+/-)", -20.0, 20.0, step=0.1)
                    st.write(f"Pv = {pb+d+dev:.1f}°")
             
             st.markdown("---")
             
             if not st.session_state.answered:
                 if st.button("👁️ MOSTRA SOLUZIONE", type="primary", use_container_width=True): 
                     st.session_state.answered = True
                     st.rerun()
             else:
                 # MOSTRA TUTTE LE SOLUZIONI DISPONIBILI
                 sol_cols = [c for c in row.keys() if str(c).startswith('Soluzione')]
                 sol_cols.sort()
                 
                 st.success("✅ SOLUZIONE UFFICIALE")
                 for col in sol_cols:
                     val = row.get(col)
                     if pd.notna(val) and str(val).strip() != "":
                         st.markdown(f"<div class='cart-result'>{col}: {val}</div>", unsafe_allow_html=True)
                 
                 c1, c2 = st.columns(2)
                 if c1.button("HO FATTO GIUSTO ✅", use_container_width=True): 
                     answer(True); next_question(); st.rerun()
                 if c2.button("HO SBAGLIATO ❌", type="primary", use_container_width=True): 
                     answer(False); next_question(); st.rerun()

        # --- BLOCCO QUIZ STANDARD (Base/Vela) ---
        else:
            c1, c2 = st.columns([1, 2], gap="small")
            with c1:
                pth = get_image_path(row.get('NomeImmagine'))
                if pth: st.image(Image.open(pth), use_container_width=True)
                else: st.markdown("<div class='placeholder-img'>⚓<br>NO IMMAGINE</div>", unsafe_allow_html=True)
            with c2:
                ui.draw_question_card(row.get('ID Progressivo'), row.get('Argomento'), row.get('Voce', ''), row.get('Domanda'))
                
                if st.session_state.answered:
                    for i, opt in enumerate(st.session_state.shuffled_options):
                        bg = "#d1e7dd" if opt['ok'] else "#f8d7da" 
                        icon = "✅" if opt['ok'] else "❌"
                        style_extra = "border: 2px solid #198754;" if opt['ok'] else "opacity: 0.7;"
                        st.markdown(f"<div class='result-box' style='background:{bg}; {style_extra} padding:10px; border-radius:5px; margin-bottom:5px; color:black;'>{icon} {opt['txt']}</div>", unsafe_allow_html=True)
                    
                    st.divider()
                    
                    spiegazione_db = str(row.get('Spiegazione', '')).strip()
                    if spiegazione_db:
                        st.markdown(f"""<div style="background-color:#e7f3fe; padding:15px; border-radius:10px; border-left:5px solid #2196F3;"><h4>📘 Spiegazione</h4><p>{spiegazione_db}</p></div>""", unsafe_allow_html=True)

                    q_url = urllib.parse.quote(f"Patente nautica spiegazione {row.get('Domanda','')}")
                    st.markdown(f'<div style="text-align:center; margin-top:10px;"><a href="https://www.google.com/search?q={q_url}" target="_blank" style="text-decoration:none; color:#555; border:1px solid #ccc; padding:5px 10px; border-radius:5px;">🔍 Cerca approfondimento su Google</a></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("PROSSIMA DOMANDA ➡", type="primary", use_container_width=True): 
                        next_question()
                        st.rerun()
                
                else:
                    for i, opt in enumerate(st.session_state.shuffled_options):
                        if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}", use_container_width=True):
                            answer(opt['ok'])
                            st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    c_skip, c_idk = st.columns(2)
                    with c_skip:
                        if st.session_state.exam_mode:
                            if st.button("⏭️ SALTA (In coda)", help="Sposta questa domanda alla fine.", use_container_width=True):
                                skip_current_question()
                                st.rerun()
                    with c_idk:
                        if st.button("🚩 Non la so!", help="Segna errore e impara.", use_container_width=True):
                            answer(False)
                            st.rerun()

    if st.session_state.current_row is None: 
        reset_game(False)
        st.rerun()