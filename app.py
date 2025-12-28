import streamlit as st
import pandas as pd
import os
import random
from PIL import Image
import urllib.parse
import time
import datetime

# --- 1. CONFIGURAZIONE E PERCORSI ---
st.set_page_config(page_title="Simulatore Patente", page_icon="⚓", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_QUIZ_BASE = os.path.join(BASE_DIR, "Quiz_Patente_Base_Finale_OK.xlsx")
FILE_QUIZ_VELA = os.path.join(BASE_DIR, "Quiz_Patente_Vela_Finale_OK.xlsx")
FILE_CARTEGGIO = os.path.join(BASE_DIR, "Quiz_Carteggio_Finale_OK.xlsx")
FILE_RACCORDO = os.path.join(BASE_DIR, "Raccordoimmagini.xlsx")
CARTELLA_IMMAGINI = os.path.join(BASE_DIR, "Immagini_Quiz")

# --- 2. CSS PERSONALIZZATO (RESPONSIVE) ---
st.markdown("""
<style>
    /* Contenitore Metriche */
    .metric-container {
        display: flex; justify-content: space-between; background-color: white; padding: 15px;
        border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e0e0e0;
    }
    .metric-box { text-align: center; width: 100%; }
    .metric-label { font-size: 11px; color: #888; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 22px; font-weight: 800; color: #333; }
    
    /* Bottoni più comodi per il touch */
    .stButton button { width: 100%; border-radius: 12px; height: auto; padding: 15px; font-size: 16px; margin-bottom: 5px; }
    
    /* Box Google */
    .google-box {
        display: block; background-color: #f1f3f5; border: 1px solid #dee2e6; border-radius: 8px;
        padding: 15px; margin: 15px 0; text-align: center; text-decoration: none; color: #495057; font-size: 14px;
    }
    .google-box:hover { border-color: #1c7ed6; color: #1c7ed6; background-color: #e7f5ff; }
    
    /* Box Carteggio */
    .scenario-box { background: #e7f5ff; padding: 20px; border-left: 5px solid #1c7ed6; border-radius: 5px; margin-bottom: 20px; font-size: 16px; }
    
    /* Footer */
    .footer { font-size: 12px; color: #666; text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; line-height: 1.5; }
    .rule-box { padding: 10px; border-radius: 5px; border: 1px solid #ffe066; background-color: #fff9db; font-size: 14px; margin-top: 10px;}
    
    /* Striscia Progresso */
    .stProgress > div > div > div > div { background-color: #1c7ed6; }
    
    /* Adattamento Immagini Placeholder */
    .placeholder-img {
        width: 100%; height: auto; min-height: 200px; background: #f8f9fa; 
        display: flex; align-items: center; justify-content: center; flex-direction: column;
        border: 2px dashed #ddd; border-radius: 8px; color: #aaa; padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE STATO ---
if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.quiz_mode = "Quiz Base"
    st.session_state.exam_mode = False
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.exam_questions = []
    st.session_state.current_row = None
    st.session_state.answered = False
    st.session_state.shuffled_options = []
    st.session_state.start_time = None
    st.session_state.exam_finished = False

# --- 4. FUNZIONI DATI E IMMAGINI ---
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
    if not os.path.exists(f): 
        f_csv = f.replace(".xlsx", ".csv")
        if os.path.exists(f_csv): f = f_csv
        else: return None
    try:
        df = pd.read_csv(f) if f.endswith('.csv') else pd.read_excel(f)
        df.columns = [str(c).strip() for c in df.columns]
        if "Carteggio" not in mode:
            fr = FILE_RACCORDO
            if not os.path.exists(fr): fr = fr.replace(".xlsx", ".csv")
            if os.path.exists(fr):
                dfr = pd.read_csv(fr) if fr.endswith('.csv') else pd.read_excel(fr)
                dfr.columns = [c.strip() for c in dfr.columns]
                if 'Progressivo' in dfr.columns and 'Immagine' in dfr.columns:
                    df = pd.merge(df, dfr[['Progressivo', 'Immagine']], left_on='ID Progressivo', right_on='Progressivo', how='left')
                    df.rename(columns={'Immagine_y': 'NomeImmagine'}, inplace=True)
        return df
    except: return None

# --- 5. LOGICA GIOCO ---
db = load_data(st.session_state.quiz_mode)
if db is None: st.error("Database non trovato."); st.stop()

def reset_game(exam=False):
    st.session_state.exam_mode = exam
    st.session_state.score_ok = 0
    st.session_state.score_ko = 0
    st.session_state.exam_index = 0
    st.session_state.answered = False
    st.session_state.exam_finished = False
    st.session_state.start_time = time.time() if exam else None
    if exam:
        num = 5 if ("Carteggio" in st.session_state.quiz_mode or "Vela" in st.session_state.quiz_mode) else 20
        st.session_state.exam_questions = db.sample(min(len(db), num)).to_dict('records')
        load_question()
    else: next_question()

def next_question():
    st.session_state.answered = False
    if st.session_state.exam_mode:
        st.session_state.exam_index += 1
        load_question()
    elif len(db) > 0:
        st.session_state.current_row = db.sample(1).iloc[0]
        prepare_options()

def load_question():
    if st.session_state.exam_index < len(st.session_state.exam_questions):
        st.session_state.current_row = st.session_state.exam_questions[st.session_state.exam_index]
        prepare_options()
    else: st.session_state.exam_finished = True

def prepare_options():
    row = st.session_state.current_row
    if row is not None and "Carteggio" not in st.session_state.quiz_mode:
        corretta = str(row['Risposta Esatta']).strip().upper()
        opts = [{'txt': row.get('Risposta A'), 'ok': corretta=='A'},
                {'txt': row.get('Risposta B'), 'ok': corretta=='B'},
                {'txt': row.get('Risposta C'), 'ok': corretta=='C'}]
        opts = [o for o in opts if pd.notna(o['txt'])]
        random.shuffle(opts)
        st.session_state.shuffled_options = opts

def answer(is_correct):
    if not st.session_state.answered:
        st.session_state.answered = True
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("⚓ NauticaApp Pro")
    
    st.markdown("### 1. Modalità")
    if st.button("🎓 SIMULAZIONE ESAME", type="primary"): reset_game(True); st.rerun()
    if st.button("♾️ ALLENAMENTO"): reset_game(False); st.rerun()
    
    st.divider()
    st.markdown("### 2. Materia")
    mode = st.radio("Seleziona:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"], label_visibility="collapsed")
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode
        st.session_state.current_row = None
        st.rerun()
    
    if "Carteggio" in st.session_state.quiz_mode:
        st.markdown('<div class="rule-box">📐 <b>REGOLE:</b> 5 esercizi.<br>Minimo <b>4 esatti</b> per idoneità.</div>', unsafe_allow_html=True)
    elif "Vela" in st.session_state.quiz_mode:
        st.markdown('<div class="rule-box">⛵ <b>REGOLE:</b> 5 domande.<br>Minimo <b>4 esatte</b> per idoneità.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="rule-box">🛥️ <b>REGOLE:</b> 20 domande.<br>Massimo <b>4 errori</b> ammessi.</div>', unsafe_allow_html=True)

    if st.session_state.exam_mode and st.session_state.start_time and not st.session_state.exam_finished:
        st.divider()
        mm, ss = divmod(int(time.time() - st.session_state.start_time), 60)
        st.markdown(f"<h1 style='text-align:center; color:{'red' if mm>=20 else 'black'}'>{mm:02d}:{ss:02d}</h1>", unsafe_allow_html=True)
        st.caption("Tempo d'esame")

    st.markdown("<br><br>", unsafe_allow_html=True)

    with st.expander("ℹ️ INFO E ISTRUZIONI", expanded=False):
        st.markdown(f"""
        **Benvenuti su NauticaApp Pro!**
        Supporto allo studio della patente nautica.
        
        🚀 **Cosa puoi fare:**
        - **Simulazione Esame:** Tempi e domande reali.
        - **Allenamento:** Senza limiti.
        
        📱 **Installazione Smartphone/Tablet:**
        - **Android:** Chrome -> 3 puntini -> "Aggiungi a home".
        - **iOS:** Safari -> Condividi -> "Aggiungi a home".
        """)

    today = datetime.datetime.now().strftime("%d/%m/%Y")
    id_domanda = st.session_state.current_row.get('ID Progressivo','') if st.session_state.current_row is not None else ''
    
    st.markdown(f"""
    <div class="footer">
        <b>by Vincenzo Autolitano</b><br>
        v1.8 Responsive - Agg. {today}<br><br>
        <a href="mailto:vincenzo.autolitano@gmail.com?subject=Segnalazione Errore NauticaApp&body=Errore nella domanda ID: {id_domanda}" style="color:#d63384; text-decoration:none;">⚠️ <b>SEGNALA ERRORE</b></a>
    </div>
    """, unsafe_allow_html=True)

# --- 7. UI PRINCIPALE ---
icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}
current_icon = icon_map.get(st.session_state.quiz_mode, '⚓')
st.markdown(f"## {current_icon} **{st.session_state.quiz_mode}** - *{'Esame' if st.session_state.exam_mode else 'Allenamento'}*")

if not st.session_state.exam_finished:
    tot = st.session_state.score_ok + st.session_state.score_ko
    perc = int(st.session_state.score_ok / tot * 100) if tot > 0 else 0
    st.markdown(f'<div class="metric-container"><div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div><div class="metric-box"><div class="metric-label">Errate</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div><div class="metric-box"><div class="metric-label">%</div><div class="metric-value">{perc}%</div></div><div class="metric-box"><div class="metric-label">Totali</div><div class="metric-value">{tot}</div></div></div>', unsafe_allow_html=True)
    
    if st.session_state.exam_mode:
        q_idx = st.session_state.exam_index + 1
        q_max = len(st.session_state.exam_questions)
        st.progress(q_idx / q_max)
        st.caption(f"Avanzamento: Domanda {q_idx} di {q_max}")

if st.session_state.exam_finished:
    passed = st.session_state.score_ok >= 4 if "Vela" in st.session_state.quiz_mode or "Carteggio" in st.session_state.quiz_mode else st.session_state.score_ko <= 4
    st.markdown(f"<h1 style='text-align:center; color:{'green' if passed else 'red'}'>{'PROMOSSO! 🎉' if passed else 'NON IDONEO 🚫'}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align:center'>{st.session_state.score_ok} Esatte - {st.session_state.score_ko} Errate</h3>", unsafe_allow_html=True)
    if st.button("🔄 NUOVA SIMULAZIONE", type="primary"): reset_game(True); st.rerun()

elif st.session_state.current_row is not None:
    row = st.session_state.current_row
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
            if pth: 
                # --- MODIFICA V1.8: USE_CONTAINER_WIDTH=TRUE ---
                # Questo rende l'immagine responsive: 100% della colonna
                st.image(Image.open(pth), use_container_width=True)
            else: 
                st.markdown("<div class='placeholder-img'>⚓<br>NESSUNA IMMAGINE</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"##### {row.get('Argomento','Argomento')}")
            st.markdown(f"### {row.get('Domanda')}")
            for i, opt in enumerate(st.session_state.shuffled_options):
                if st.session_state.answered:
                    icon = "✅" if opt['ok'] else "❌"
                    bg = "#d1e7dd" if opt['ok'] else "#f8d7da"
                    st.markdown(f"<div style='padding:10px; border-radius:5px; margin-bottom:5px; background:{bg}'>{icon} {opt['txt']}</div>", unsafe_allow_html=True)
                else:
                    if st.button(f"{chr(65+i)}. {opt['txt']}", key=f"btn_{i}"): answer(opt['ok']); st.rerun()
            
            if st.session_state.answered:
                q_url = urllib.parse.quote(f"Patente nautica spiegazione {row.get('Domanda','')}")
                st.markdown(f'<a href="https://www.google.com/search?q={q_url}" target="_blank" class="google-box">💡 <b>Approfondimento:</b> Cerca su Google</a>', unsafe_allow_html=True)
                if st.button("PROSSIMA DOMANDA ➡", type="primary"): next_question(); st.rerun()

if st.session_state.current_row is None: reset_game(False); st.rerun()