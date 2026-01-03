import streamlit as st
import pandas as pd
import os
import random
import time
import datetime
import urllib.parse
from PIL import Image

# --- IMPORT LIBRERIA MEMORIA ---
try:
    from streamlit_local_storage import LocalStorage
    HAS_LOCAL_STORAGE = True
except ImportError:
    HAS_LOCAL_STORAGE = False

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Patente Nautica App Pro", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

local_storage = LocalStorage() if HAS_LOCAL_STORAGE else None

# --- 2. CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 3rem; padding-bottom: 1rem; padding-left: 1rem; padding-right: 1rem; }
    h2 { font-size: 22px !important; margin-bottom: 10px !important; margin-top: 0px !important; }
    .metric-container { display: flex; justify-content: space-between; background-color: white; padding: 10px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 15px; border: 1px solid #e0e0e0; }
    .metric-box { text-align: center; width: 100%; }
    .metric-label { font-size: 10px; color: #888; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 18px; font-weight: 800; color: #333; }
    .stButton button { width: 100%; border-radius: 10px; height: auto; padding: 12px 15px; font-size: 16px; margin-bottom: 4px; line-height: 1.3; }
    .result-box { padding: 15px; border-radius: 8px; margin-bottom: 8px; color: #000000 !important; font-weight: 600; border: 1px solid rgba(0,0,0,0.1); font-size: 16px; }
    .google-box { display: block; background-color: #f1f3f5; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; margin: 10px 0; text-align: center; text-decoration: none; color: #495057; font-size: 14px; }
    .scenario-box { background: #e7f5ff; padding: 15px; border-left: 5px solid #1c7ed6; border-radius: 5px; margin-bottom: 15px; font-size: 15px; }
    .footer { font-size: 11px; color: #666; text-align: center; margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; line-height: 1.4; }
    .rule-box { padding: 8px; border-radius: 5px; border: 1px solid #ffe066; background-color: #fff9db; font-size: 13px; margin-top: 5px;}
    .stProgress > div > div > div > div { background-color: #1c7ed6; }
    .question-header { font-size: 14px; color: #333; background-color: #f1f3f5; padding: 10px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #1c7ed6; }
    .placeholder-img { width: 100%; height: auto; min-height: 180px; background: #f8f9fa; display: flex; align-items: center; justify-content: center; flex-direction: column; border: 2px dashed #ddd; border-radius: 8px; color: #aaa; padding: 10px; }
    /* STILE PER IL DEBUG */
    .debug-info { font-size: 12px; color: #495057; background: #e9ecef; padding: 10px; border-radius: 6px; margin-bottom: 15px; border: 1px dashed #adb5bd; }
    @media (max-width: 768px) { .metric-value { font-size: 16px; } }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE STATO ---
if 'init' not in st.session_state:
    st.session_state.quiz_mode = "Quiz Base"
    st.session_state.exam_mode = False
    st.session_state.review_mode = False
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

# AUTO-SYNC
if HAS_LOCAL_STORAGE and local_storage:
    time.sleep(0.1)
    browser_data = local_storage.getItem("nautica_history")
    if browser_data and len(browser_data) > 0 and st.session_state.history != browser_data:
        new_history = {}
        migrated = False
        for k, v in browser_data.items():
            if v == 'KO': new_history[k] = -1; migrated = True
            elif v == 'OK': new_history[k] = 1; migrated = True
            else: new_history[k] = v
        
        st.session_state.history = new_history
        if migrated: local_storage.setItem("nautica_history", new_history)
        st.rerun()

# --- 4. CARICAMENTO DATI ---
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

# --- 5. LOGICA DEL GIOCO ---
db = load_data(st.session_state.quiz_mode)
if db is None or len(db) == 0: st.stop()

def get_unique_key(id_dom):
    return f"{st.session_state.quiz_mode}_{id_dom}"

def calculate_weight(val):
    if val is None: return 1.0       # Nuova
    if val == -1: return 10.0        # Errore
    if val > 0: return 1.0 / (1.0 + val) 
    return 1.0

def get_weighted_question(dataset, num=1):
    df = dataset.copy()
    def assign_weight(id_dom):
        unique_key = get_unique_key(id_dom)
        val = st.session_state.history.get(unique_key)
        return calculate_weight(val)
    
    df['peso'] = df['ID Progressivo'].apply(assign_weight)
    safe_num = min(len(df), num)
    return df.sample(n=safe_num, weights='peso')

def reset_game(exam=False, review=False):
    st.session_state.exam_mode = exam
    st.session_state.review_mode = review
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.answered = False
    st.session_state.exam_finished = False
    st.session_state.start_time = time.time() if exam else None
    st.session_state.exam_questions = [] 
    
    if review:
        prefix = f"{st.session_state.quiz_mode}_"
        target_ids = []
        for key, val in st.session_state.history.items():
            if val == -1 and key.startswith(prefix):
                target_ids.append(key.replace(prefix, ""))
        
        filtered_db = db[db['ID Progressivo'].isin(target_ids)]
        if len(filtered_db) == 0:
            st.warning(f"Nessun errore registrato in {st.session_state.quiz_mode}!")
            st.session_state.review_mode = False
            return
        st.session_state.exam_questions = filtered_db.sample(len(filtered_db)).to_dict('records')
        load_question()

    elif exam:
        is_short_exam = "Carteggio" in st.session_state.quiz_mode or "Vela" in st.session_state.quiz_mode
        num = 5 if is_short_exam else 20
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
        
        if is_correct:
            if current_val is None or current_val == -1: st.session_state.history[unique_key] = 1
            else: st.session_state.history[unique_key] = current_val + 1
        else:
            st.session_state.history[unique_key] = -1
        
        if HAS_LOCAL_STORAGE and local_storage:
            try: local_storage.setItem("nautica_history", st.session_state.history)
            except: pass
            
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("⚓ Patente Nautica App Pro")
    
    st.markdown("### 1. Modalità")
    st.button("🎓 SIMULAZIONE ESAME", type="primary", on_click=reset_game, kwargs={'exam': True})
    st.button("♾️ ALLENAMENTO", on_click=reset_game, kwargs={'exam': False})
    
    st.divider()
    
    mode = st.radio("Materia:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"], label_visibility="collapsed")
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode
        st.session_state.current_row = None
        st.session_state.exam_questions = []
        st.session_state.exam_mode = False
        st.session_state.review_mode = False
        st.rerun()
    
    current_prefix = f"{st.session_state.quiz_mode}_"
    err_count = 0
    for k, v in st.session_state.history.items():
        if v == -1 and k.startswith(current_prefix): err_count += 1

    if err_count > 0:
        st.error(f"⚠️ **{err_count} ERRORI GRAVI**")
        st.button("🔄 RIPASSA ERRORI", on_click=reset_game, kwargs={'review': True})
    
    st.divider()
    
    if st.session_state.exam_mode and st.session_state.start_time and not st.session_state.exam_finished:
        mm, ss = divmod(int(time.time() - st.session_state.start_time), 60)
        st.markdown(f"<h1 style='text-align:center; color:{'red' if mm>=20 else 'black'}'>{mm:02d}:{ss:02d}</h1>", unsafe_allow_html=True)
        st.divider()

    # --- SEZIONE INFO ---
    with st.expander("ℹ️ GUIDA E ISTRUZIONI", expanded=False):
        st.markdown("""
        **1. MODALITÀ DI STUDIO**
        * 🎓 **Simulazione:** Simula l'esame reale (20 domande per Base, 5 per Vela/Carteggio).
        * ♾️ **Allenamento:** Feedback immediato dopo ogni risposta.

        **2. MEMORIA INTELLIGENTE (SRS)**
        * 🔴 **Errori:** Peso 10 (Escono spesso).
        * 🟢 **Apprendimento:** Peso decrescente (Escono meno).
        * 🆕 **Nuove:** Peso normale.

        **3. RIPASSO ERRORI**
        Usa il tasto rosso per correggere solo gli errori attivi.
        """)

    # --- SEZIONE DEBUG RIPRISTINATA COMPLETAMENTE ---
    with st.expander("🧠 STATO MEMORIA (Debug)", expanded=False):
        st.session_state.debug_mode = st.checkbox("🛠️ Attiva Debug Mode")
        
        # Calcolo Statistiche
        total_mem = len([k for k in st.session_state.history if k.startswith(current_prefix)])
        mastered = len([k for k,v in st.session_state.history.items() if k.startswith(current_prefix) and v > 0])
        errors_debug = len([k for k,v in st.session_state.history.items() if k.startswith(current_prefix) and v == -1])
        
        st.markdown(f"**Statistiche per {st.session_state.quiz_mode}:**")
        st.markdown(f"- 📂 Totale in memoria: **{total_mem}**")
        st.markdown(f"- 🔴 Errori attivi: **{errors_debug}**")
        st.markdown(f"- 🟢 In apprendimento: **{mastered}**")
        
        if st.checkbox("Mostra elenco ID"):
             # Mostra solo ID puliti della materia corrente
             debug_list = {k.replace(current_prefix, ""): v for k,v in st.session_state.history.items() if k.startswith(current_prefix)}
             st.write(debug_list)
        
    st.markdown("<br>", unsafe_allow_html=True)
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    id_d = st.session_state.current_row.get('ID Progressivo','') if st.session_state.current_row is not None else ''
    st.markdown(f"<div class='footer'><b>by Vincenzo Autolitano</b><br>v4.3 Full Feature • {today}<br><a href='mailto:vincenzo.autolitano@gmail.com?subject=Errore ID {id_d}'>⚠️ SEGNALA ERRORE</a></div>", unsafe_allow_html=True)

# --- 7. INTERFACCIA ---
current_icon = icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}.get(st.session_state.quiz_mode, '⚓')
if st.session_state.review_mode: sub_title = "Ripasso Errori"
elif st.session_state.exam_mode: sub_title = "Simulazione Esame"
else: sub_title = "Allenamento"
st.markdown(f"## {current_icon} **{st.session_state.quiz_mode}** - *{sub_title}*")

if not st.session_state.exam_finished:
    tot = st.session_state.score_ok + st.session_state.score_ko
    perc = int(st.session_state.score_ok / tot * 100) if tot > 0 else 0
    st.markdown(f'<div class="metric-container"><div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div><div class="metric-box"><div class="metric-label">Errate</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div><div class="metric-box"><div class="metric-label">%</div><div class="metric-value">{perc}%</div></div><div class="metric-box"><div class="metric-label">Totali</div><div class="metric-value">{tot}</div></div></div>', unsafe_allow_html=True)
    if st.session_state.exam_mode or st.session_state.review_mode:
        st.progress((st.session_state.exam_index + 1) / len(st.session_state.exam_questions))

if st.session_state.exam_finished:
    if st.session_state.review_mode:
        st.markdown(f"<h1 style='text-align:center; color:blue'>RIPASSO COMPLETATO! 💪</h1>", unsafe_allow_html=True)
        st.info("Gli errori corretti ora appariranno con meno frequenza.")
    else:
        passed = st.session_state.score_ok >= 4 if "Vela" in st.session_state.quiz_mode or "Carteggio" in st.session_state.quiz_mode else st.session_state.score_ko <= 4
        st.markdown(f"<h1 style='text-align:center; color:{'green' if passed else 'red'}'>{'PROMOSSO! 🎉' if passed else 'NON IDONEO 🚫'}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align:center'>{st.session_state.score_ok} Esatte - {st.session_state.score_ko} Errate</h3>", unsafe_allow_html=True)
    st.button("🔄 NUOVA SIMULAZIONE", type="primary", on_click=reset_game, kwargs={'exam': True})

elif st.session_state.current_row is not None:
    row = st.session_state.current_row
    
    # --- VISUALIZZAZIONE DEBUG PESI (RIPRISTINATA) ---
    if st.session_state.debug_mode:
        id_dom = str(row.get('ID Progressivo'))
        ukey = get_unique_key(id_dom)
        val = st.session_state.history.get(ukey)
        w = calculate_weight(val)
        status_text = "🆕 MAI VISTA"
        if val == -1: status_text = "🔴 ERRORE ATTIVO"
        elif val is not None and val > 0: status_text = f"🟢 CORRETTA {val} VOLTE"
        
        st.markdown(f"""
        <div class="debug-info">
            🔧 <b>DEBUG:</b> ID {id_dom} | Stato: <b>{status_text}</b> | Peso Estrazione: <b>{w:.2f}</b>
        </div>
        """, unsafe_allow_html=True)

    if "Carteggio" in st.session_state.quiz_mode:
        st.markdown(f"### Esercizio {row.get('ID Progressivo','')}")
        st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
        if not st.session_state.answered:
            st.info("Risolvi sulla carta e poi clicca sotto.")
            if st.button("👁️ MOSTRA SOLUZIONI", type="primary"): st.session_state.answered = True; st.rerun()
        else:
            sol_data = {"Parametro": ["Distanza", "Velocità", "Carburante", "Partenza", "Arrivo"], "Soluzione": [row.get(f'Soluzione {i+1}') for i in range(5)]}
            st.table(pd.DataFrame(sol_data))
            c1, c2 = st.columns(2); 
            if c1.button("✅ CORRETTO"): answer(True); next_question(); st.rerun()
            if c2.button("❌ ERRATO"): answer(False); next_question(); st.rerun()
            
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            pth = get_image_path(row.get('NomeImmagine'))
            if pth: st.image(Image.open(pth), use_container_width=True)
            else: st.markdown("<div class='placeholder-img'>⚓<br>NESSUNA IMMAGINE</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='question-header'><b>ID {row.get('ID Progressivo')} • {row.get('Argomento')}</b><br><i>{row.get('Voce','')}</i></div>", unsafe_allow_html=True)
            st.markdown(f"### {row.get('Domanda')}")
            for i, opt in enumerate(st.session_state.shuffled_options):
                if st.session_state.answered:
                    bg = "#d1e7dd" if opt['ok'] else "#f8d7da" 
                    st.markdown(f"<div class='result-box' style='background:{bg};'>{'✅' if opt['ok'] else '❌'} {opt['txt']}</div>", unsafe_allow_html=True)
                else:
                    if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}"): answer(opt['ok']); st.rerun()
            if st.session_state.answered:
                q_url = urllib.parse.quote(f"Patente nautica spiegazione {row.get('Domanda','')}")
                st.markdown(f'<a href="https://www.google.com/search?q={q_url}" target="_blank" class="google-box">💡 <b>Approfondimento:</b> Cerca su Google</a>', unsafe_allow_html=True)
                if st.button("PROSSIMA DOMANDA ➡", type="primary"): next_question(); st.rerun()

if st.session_state.current_row is None: reset_game(False); st.rerun()