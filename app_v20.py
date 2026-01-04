# --- VERSIONE APP: v20.32 (Full Info Restored & Admin Features) ---
import streamlit as st
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
st.set_page_config(page_title="Patente Nautica v20.32", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

# UI SETUP
MAIN_BG_IMAGE = "background.jpg"
SIDEBAR_BG_IMAGE = "background2.jpg"
ui.set_backgrounds(MAIN_BG_IMAGE, SIDEBAR_BG_IMAGE)
ui.load_css()

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
    st.session_state.start_time = None
    st.session_state.exam_finished = False
    st.session_state.history = {} 
    st.session_state.debug_mode = False
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

# --- 4. LOGIN & ADMIN ---
if st.session_state.current_user is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        ui.draw_login_header("v20.32 • Pro & Admin")
        name_input = st.text_input("Inserisci il tuo nome per accedere:", placeholder="Es. Vincenzo").strip()
        
        # LOGICA ADMIN SEGRETA
        if name_input.lower() == "admin":
            pwd = st.text_input("🔑 Password Ammiraglio:", type="password")
            if pwd == "nautica2025":
                if st.button("ENTRA IN PLANCIA", type="primary", use_container_width=True):
                    st.session_state.current_user = "Ammiraglio"
                    st.session_state.admin_mode = True
                    st.rerun()
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ACCEDI AL SISTEMA", type="primary", use_container_width=True):
                if name_input:
                    with st.spinner("Caricamento Profilo Utente..."):
                        hist = db_engine.fetch_user_history(name_input)
                        st.session_state.history = hist
                        st.session_state.current_user = name_input
                        st.session_state.admin_mode = False
                        st.rerun()
        
        # --- TESTO INFO RIPRISTINATO E COMPLETO ---
        with st.expander("ℹ️ INFO E GUIDA ALL'USO"):
            st.markdown("""
            **A cosa serve questa App?**
            Questa applicazione è uno strumento professionale per supportarti nello studio dei quiz ministeriali per il conseguimento della **Patente Nautica** (Entro 12 miglia e Senza Limiti) presso le Capitanerie di Porto Italiane.

            **Come funziona:**
            * 🎓 **Simulazione Esame:** Riproduce l'esame reale.
                * *Quiz Base:* 20 domande (Max 4 errori ammessi).
                * *Vela / Carteggio:* 5 domande (Max 1 errore ammesso).
            * ♾️ **Allenamento Continuo:** Esercitazione libera su tutto il database.
            * 🔄 **Ripasso Errori:** Una modalità speciale per rivedere solo i quiz che hai sbagliato.

            **🆕 Novità v20: Metodo SRS (Spaced Repetition)**
            L'algoritmo intelligente ti interroga quando stai per dimenticare:
            * Se sbagli 🔴 -> Ti interrogo domani.
            * Se indovini 🟢 (1 volta) -> Ti interrogo tra 3 giorni.
            * Se indovini 🟢🟢 (2 volte) -> Ti interrogo tra 7 giorni.
            * Se sei esperto 🎓 -> Ti interrogo tra 15 giorni.
            """)
    ui.draw_login_footer()
    st.stop()

# --- 5. LOGICA GIOCO E AMMIRAGLIO ---
db = load_data(st.session_state.quiz_mode)

# === SEZIONE ADMIN (AMMIRAGLIO) ===
if st.session_state.admin_mode:
    st.markdown("## 👮‍♂️ Plancia Ammiraglio (Admin Dashboard)")
    if st.button("Esci da Admin"):
        st.session_state.current_user = None
        st.session_state.admin_mode = False
        st.rerun()
    
    st.info("Monitoraggio attività studenti.")
    
    all_data = db_engine.fetch_all_stats()
    if all_data:
        df_all = pd.DataFrame(all_data)
        
        if 'Timestamp' in df_all.columns:
            df_all['DT'] = pd.to_datetime(df_all['Timestamp'])
            df_all['Giorno'] = df_all['DT'].dt.date
        else:
            df_all['DT'] = datetime.datetime.now()
            df_all['Giorno'] = datetime.date.today()

        tot_answers = len(df_all)
        tot_users = df_all['Utente'].nunique()
        last_active_str = df_all['DT'].max().strftime("%d/%m/%Y %H:%M")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Studenti Iscritti", tot_users)
        c2.metric("Quiz Totali Svolti", tot_answers)
        c3.metric("Ultimo Ingresso", last_active_str)
        
        st.divider()
        st.markdown("### 🏆 Classifica & Attività")
        
        summary = df_all.groupby('Utente').agg(
            Domande_Svolte=('Esito', 'count'),
            Giorni_Attività=('Giorno', 'nunique'),
            Ultimo_Accesso=('DT', 'max')
        ).reset_index().sort_values('Ultimo_Accesso', ascending=False)
        
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Utente": st.column_config.TextColumn("Studente", width="medium"),
                "Domande_Svolte": st.column_config.NumberColumn("Quiz Fatti", format="%d"),
                "Giorni_Attività": st.column_config.NumberColumn("Giorni Studio", help="Giorni diversi di collegamento"),
                "Ultimo_Accesso": st.column_config.DatetimeColumn("Ultima Attività", format="DD/MM/YYYY HH:mm")
            }
        )
        
        with st.expander("🔍 Vedi Log Completo (Raw Data)"):
            st.dataframe(df_all.sort_values('Timestamp', ascending=False).head(200), use_container_width=True)
    else:
        st.warning("Database vuoto o errore connessione.")
    st.stop() 

# === SEZIONE UTENTE NORMALE ===
if db is None or len(db) == 0: st.stop()

def get_user_rank(mastered_count):
    if mastered_count < 100: return "🧹 Mozzo", 100
    if mastered_count < 300: return "⚓ Marinaio", 300
    if mastered_count < 500: return "🧭 Nostromo", 500
    if mastered_count < 700: return "🛳️ Comandante", 700
    return "🐺 Lupo di Mare", 1000

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
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Ripasso")
            if len(subset) == 0:
                st.success("🎉 Nessun ripasso in scadenza!")
                st.session_state.review_mode = False
                return
            st.session_state.exam_questions = subset.to_dict('records')
            load_question()
        elif exam:
            num = 5 if ("Carteggio" in st.session_state.quiz_mode or "Vela" in st.session_state.quiz_mode) else 20
            st.session_state.exam_questions = db.sample(num).to_dict('records')
            load_question()
        else:
            subset = brain.get_next_session_questions(db, st.session_state.history, mode="Allenamento")
            st.session_state.exam_questions = subset.to_dict('records')
            load_question()

def next_question():
    st.session_state.answered = False
    if st.session_state.exam_index + 1 < len(st.session_state.exam_questions):
        st.session_state.exam_index += 1
        load_question()
    elif not st.session_state.exam_mode and not st.session_state.review_mode:
        st.session_state.exam_index = 0
        subset = brain.get_next_session_questions(db, st.session_state.history, mode="Allenamento")
        st.session_state.exam_questions = subset.to_dict('records')
        load_question()
    else:
        st.session_state.exam_finished = True

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
        item_data = st.session_state.history.get(id_dom, {'score': 0, 'date': ''})
        new_score = 1 if is_correct else -1
        if is_correct and item_data['score'] > 0: new_score = item_data['score'] + 1
        st.session_state.history[id_dom] = {'score': new_score, 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        db_engine.upsert_answer(st.session_state.current_user, id_dom, new_score)
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("⚓ Patente Nautica")
    col_u1, col_u2 = st.columns([4,1])
    with col_u1: st.markdown(f"👤 **{st.session_state.current_user}**")
    with col_u2:
        if st.button("⏻", help="Esci"):
            st.session_state.current_user = None
            st.rerun()
    
    mastered_count = len([v for v in st.session_state.history.values() if v['score'] > 0])
    rank_name, rank_target = get_user_rank(mastered_count)
    ui.draw_rank_box(rank_name, mastered_count, rank_target)
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
    st.button("♾️ ALLENAMENTO SMART", on_click=reset_game, kwargs={'exam': False})
    st.divider()
    
    current_ids = set(db['ID Progressivo'].astype(str))
    err_count = len([k for k, v in st.session_state.history.items() if v['score'] == -1 and k in current_ids])
    if err_count > 0:
        st.error(f"⚠️ **{err_count} Errori Attivi**")
        st.button("🔄 RIPASSA ERRORI", on_click=reset_game, kwargs={'review': True})
    
    st.button("📊 STATISTICHE", on_click=reset_game, kwargs={'stats': True})
    
    # --- MODULO SEGNALAZIONE ERRORI ---
    st.markdown("---")
    with st.expander("⚠️ SEGNALA ERRORE", expanded=False):
        with st.form("report_form"):
            st.caption("Hai trovato un errore in una domanda?")
            report_msg = st.text_area("Descrivi l'errore:", placeholder="Es. La risposta giusta è la B, non la A.")
            submitted = st.form_submit_button("Invia Segnalazione")
            if submitted and report_msg:
                curr_id = "Generico"
                if st.session_state.current_row is not None:
                    curr_id = str(st.session_state.current_row.get('ID Progressivo', 'Generico'))
                ok = db_engine.save_report_to_db(st.session_state.current_user, curr_id, report_msg)
                if ok: st.success("Inviato! Grazie.")
                else: st.error("Errore invio.")

    today = datetime.datetime.now().strftime("%d/%m")
    st.markdown(f"""<div class='footer-sidebar'><b>v20.32 Pro</b> • {today}<br>Developed by Vincenzo Autolitano</div>""", unsafe_allow_html=True)

# --- 7. INTERFACCIA PRINCIPALE ---
current_icon = icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}.get(st.session_state.quiz_mode, '⚓')

if st.session_state.stats_mode:
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
    perc_master = int((tot_master / tot_risposte) * 100) if tot_risposte > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    with c1: ui.draw_stat_metric("Domande Svolte", tot_risposte, "Totale in questa materia", "blue")
    with c2: ui.draw_stat_metric("Consolidate", f"{tot_master}", f"{perc_master}% del totale", "green")
    with c3: ui.draw_stat_metric("Errori Attivi", tot_errori, "Da ripassare con urgenza", "red")
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
            st.dataframe(final_table.sort_values(by='% Completamento', ascending=False), hide_index=True, use_container_width=True)
    
    with tab2:
        if len(df_full) > 0 and 'Argomento' in df_full.columns:
            err_df = df_full[df_full['Score'] == -1]
            if len(err_df) > 0:
                st.bar_chart(err_df['Argomento'].value_counts(), color="#ff4b4b")
            else: st.success("Nessun errore attivo!")
    
    with tab3:
        if len(df_full) > 0 and 'Date' in df_full.columns:
            df_full['Day'] = pd.to_datetime(df_full['Date']).dt.date
            st.line_chart(df_full.groupby('Day').count()['ID Progressivo'])

else:
    title_suffix = "Ripasso" if st.session_state.review_mode else ("Simulazione Esame" if st.session_state.exam_mode else "Allenamento Smart")
    st.markdown(f"## {current_icon} {st.session_state.quiz_mode} - *{title_suffix}*")

    if not st.session_state.exam_finished:
        tot = st.session_state.score_ok + st.session_state.score_ko
        perc = int(st.session_state.score_ok / tot * 100) if tot > 0 else 0
        st.markdown(f'<div class="metric-container"><div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div><div class="metric-box"><div class="metric-label">Errate</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div><div class="metric-box"><div class="metric-label">%</div><div class="metric-value">{perc}%</div></div></div>', unsafe_allow_html=True)
        if st.session_state.exam_mode or st.session_state.review_mode:
            st.progress((st.session_state.exam_index + 1) / len(st.session_state.exam_questions))
            st.caption(f"📝 Domanda {st.session_state.exam_index + 1} di {len(st.session_state.exam_questions)}")

    if st.session_state.exam_finished:
        st.markdown('<div class="question-card">', unsafe_allow_html=True)
        if st.session_state.review_mode:
            st.markdown(f"""<div class="review-end"><h1>✅ Ripasso Completato</h1></div>""", unsafe_allow_html=True)
            st.button("TORNA AL MENU", type="primary", on_click=reset_game, kwargs={'exam': False})
        elif st.session_state.exam_mode:
            allowed = 4 if "Base" in st.session_state.quiz_mode else 1
            if st.session_state.score_ko <= allowed:
                st.markdown(f"""<div class="exam-pass"><h1>🎉 SUPERATO! 🎉</h1><p>Errori: {st.session_state.score_ko}</p></div>""", unsafe_allow_html=True)
                st.balloons()
            else:
                st.markdown(f"""<div class="exam-fail"><h1>🚫 NON SUPERATO</h1><p>Errori: {st.session_state.score_ko}</p></div>""", unsafe_allow_html=True)
            st.button("🔄 NUOVA SIMULAZIONE", type="primary", on_click=reset_game, kwargs={'exam': True})
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.current_row is not None:
        row = st.session_state.current_row
        if st.session_state.debug_mode:
            item = st.session_state.history.get(str(row.get('ID Progressivo')), {'score': 0, 'date': ''})
            st.markdown(f"""<div class="debug-info">🔧 <b>SRS:</b> ID {row.get('ID Progressivo')} | Score: {item['score']}</div>""", unsafe_allow_html=True)

        if "Carteggio" in st.session_state.quiz_mode:
            st.markdown(f"**Esercizio {row.get('ID Progressivo')}**")
            st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
            if not st.session_state.answered:
                if st.button("👁️ MOSTRA SOLUZIONE", type="primary"): st.session_state.answered = True; st.rerun()
            else:
                st.markdown("### 📐 Analisi della Soluzione")
                if "velocità" in str(row.get('Domanda')).lower(): st.latex(r"V = \frac{S (Miglia)}{T (Ore)}")
                sol_data = {"Parametro": ["Distanza", "Velocità", "Carburante", "Partenza", "Arrivo"], "Soluzione": [row.get(f'Soluzione {i+1}') for i in range(5)]}
                st.dataframe(pd.DataFrame(sol_data), hide_index=True, use_container_width=True)
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
                ui.draw_question_card(row.get('ID Progressivo'), row.get('Argomento'), row.get('Voce', ''), row.get('Domanda'))
                for i, opt in enumerate(st.session_state.shuffled_options):
                    if st.session_state.answered:
                        bg = "#d1e7dd" if opt['ok'] else "#f8d7da" 
                        icon = "✅" if opt['ok'] else "❌"
                        st.markdown(f"<div class='result-box' style='background:{bg};'>{icon} {opt['txt']}</div>", unsafe_allow_html=True)
                    else:
                        if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}"): answer(opt['ok']); st.rerun()
                if st.session_state.answered:
                    q_url = urllib.parse.quote(f"Patente nautica spiegazione {row.get('Domanda','')}")
                    st.markdown(f'<a href="https://www.google.com/search?q={q_url}" target="_blank" class="google-box" style="text-align:center">💡 <b>Approfondimento:</b> Cerca su Google</a>', unsafe_allow_html=True)
                    if st.button("PROSSIMA DOMANDA ➡", type="primary"): next_question(); st.rerun()

    if st.session_state.current_row is None: 
        reset_game(False)
        st.rerun()