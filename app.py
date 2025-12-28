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

# --- 2. CSS PER STILE E STATISTICHE ---
st.markdown("""
<style>
    /* Stile Dashboard in alto */
    .metric-container {
        display: flex;
        justify-content: space-between;
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .metric-box { text-align: center; width: 100%; }
    .metric-label { font-size: 12px; color: #888; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 24px; font-weight: 800; color: #333; }
    
    /* Stile Bottoni */
    .stButton button { width: 100%; border-radius: 8px; height: auto; padding: 12px; }
    
    /* Box Immagine - Ridimensionato */
    .placeholder-img {
        width: 300px; height: 250px; background: #f8f9fa; 
        display: flex; align-items: center; justify-content: center;
        border: 2px dashed #ddd; border-radius: 8px; color: #aaa;
    }
    
    /* Box Carteggio */
    .scenario-box { background: #e7f5ff; padding: 20px; border-left: 5px solid #1c7ed6; border-radius: 5px; margin-bottom: 20px; }
    
    /* Footer Sidebar */
    .footer { 
        font-size: 13px; 
        color: #666; 
        text-align: center; 
        margin-top: 50px; 
        padding-top: 20px;
        border-top: 1px solid #ddd;
        line-height: 1.6;
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
    
    # Supporto CSV/XLSX
    if not os.path.exists(f): 
        f_csv = f.replace(".xlsx", ".csv")
        if os.path.exists(f_csv): f = f_csv
        else: return None
        
    try:
        df = pd.read_csv(f) if f.endswith('.csv') else pd.read_excel(f)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Merge Raccordo (Solo se non carteggio)
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
# Se il caricamento fallisce (es. cambio file rapido), non crashare ma stop
if db is None: 
    st.error(f"Errore caricamento database per {st.session_state.quiz_mode}. Controlla i file.")
    st.stop()

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
        # Safety sample
        st.session_state.exam_questions = db.sample(min(len(db), num)).to_dict('records')
        load_question()
    else:
        next_question()

def next_question():
    st.session_state.answered = False
    if st.session_state.exam_mode:
        st.session_state.exam_index += 1
        load_question()
    else:
        # Safety sample
        if len(db) > 0:
            st.session_state.current_row = db.sample(1).iloc[0]
            prepare_options()

def load_question():
    if st.session_state.exam_index < len(st.session_state.exam_questions):
        st.session_state.current_row = st.session_state.exam_questions[st.session_state.exam_index]
        prepare_options()
    else:
        st.session_state.exam_finished = True

def prepare_options():
    row = st.session_state.current_row
    if "Carteggio" not in st.session_state.quiz_mode:
        corretta = str(row['Risposta Esatta']).strip().upper()
        opts = [
            {'txt': row.get('Risposta A'), 'ok': corretta=='A'},
            {'txt': row.get('Risposta B'), 'ok': corretta=='B'},
            {'txt': row.get('Risposta C'), 'ok': corretta=='C'}
        ]
        opts = [o for o in opts if pd.notna(o['txt'])]
        random.shuffle(opts)
        st.session_state.shuffled_options = opts

def answer(is_correct):
    if not st.session_state.answered:
        st.session_state.answered = True
        if is_correct: st.session_state.score_ok += 1
        else: st.session_state.score_ko += 1

# --- 6. INTERFACCIA UTENTE (SIDEBAR) ---
with st.sidebar:
    st.title("⚓ NauticaApp")
    
    # --- BOTTONI PRINCIPALI ---
    st.markdown("### 1. Modalità")
    if st.button("🎓 SIMULAZIONE ESAME", type="primary"): 
        reset_game(True)
        st.rerun()
        
    if st.button("♾️ ALLENAMENTO"): 
        reset_game(False)
        st.rerun()
    
    st.divider()

    # --- SCELTA MATERIA (FIXED) ---
    st.markdown("### 2. Materia")
    mode = st.radio("Seleziona:", ["Quiz Base", "Quiz Vela", "Elementi di Carteggio"], label_visibility="collapsed")
    
    # SE CAMBIA LA MATERIA:
    if mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = mode
        # 1. Resetta la riga corrente a None (così non usa il vecchio DB)
        st.session_state.current_row = None
        # 2. Riavvia l'app per caricare il nuovo DB
        st.rerun()
    
    # TIMER
    if st.session_state.exam_mode and st.session_state.start_time and not st.session_state.exam_finished:
        st.divider()
        sec_passati = int(time.time() - st.session_state.start_time)
        mm, ss = divmod(sec_passati, 60)
        colore = "red" if mm >= 20 else "black"
        st.markdown(f"<h1 style='text-align:center; color:{colore}'>{mm:02d}:{ss:02d}</h1>", unsafe_allow_html=True)
        st.caption("Tempo (aggiornato a ogni click)")

    # --- FOOTER CREDITS ---
    today_date = datetime.datetime.now().strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="footer">
        <b>NauticaApp Pro</b><br>
        by Vincenzo Autolitano<br>
        v1.3 - Agg. {today_date}
    </div>
    """, unsafe_allow_html=True)

# --- INTESTAZIONE PRINCIPALE ---
icon_map = {'Carteggio': '📐', 'Vela': '⛵', 'Base': '🛥️'}
current_icon = next((v for k, v in icon_map.items() if k in st.session_state.quiz_mode), '⚓')
mode_text = "Simulazione Esame" if st.session_state.exam_mode else "Allenamento Infinito"

st.markdown(f"## {current_icon} **{st.session_state.quiz_mode}** - *{mode_text}*")

# --- DASHBOARD STATISTICHE ---
if not st.session_state.exam_finished:
    tot = st.session_state.score_ok + st.session_state.score_ko
    perc = int(st.session_state.score_ok / tot * 100) if tot > 0 else 0
    
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-box"><div class="metric-label">Esatte</div><div class="metric-value" style="color:green">{st.session_state.score_ok}</div></div>
        <div class="metric-box"><div class="metric-label">Errate</div><div class="metric-value" style="color:red">{st.session_state.score_ko}</div></div>
        <div class="metric-box"><div class="metric-label">% Corrette</div><div class="metric-value">{perc}%</div></div>
        <div class="metric-box"><div class="metric-label">Totali</div><div class="metric-value">{tot}</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.exam_mode:
        prog = (st.session_state.exam_index + 1) / len(st.session_state.exam_questions)
        st.progress(prog)
        st.caption(f"Domanda {st.session_state.exam_index + 1} di {len(st.session_state.exam_questions)}")

# --- SCHERMATA FINALE ---
if st.session_state.exam_finished:
    passed = st.session_state.score_ok >= 4 if "Vela" in st.session_state.quiz_mode or "Carteggio" in st.session_state.quiz_mode else st.session_state.score_ko <= 4
    col_res = "green" if passed else "red"
    msg = "PROMOSSO! 🎉" if passed else "BOCCIATO 🚫"
    st.markdown(f"<h1 style='text-align:center; color:{col_res}; font-size:50px'>{msg}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align:center'>Risultato finale: {st.session_state.score_ok} Esatte - {st.session_state.score_ko} Errate</h3>", unsafe_allow_html=True)
    if st.button("Riprova", type="primary", use_container_width=True): reset_game(True); st.rerun()

# --- DOMANDA CORRENTE ---
elif st.session_state.current_row is not None:
    row = st.session_state.current_row
    
    # CARTEGGIO
    if "Carteggio" in st.session_state.quiz_mode:
        # Se siamo in carteggio ma il dato è corrotto (es. residuo di quiz base), rigeneriamo
        if 'Scenario' not in row and 'Domanda' not in row:
            st.warning("Allineamento dati in corso... Ricarica la pagina.")
            st.session_state.current_row = None
            st.rerun()
            
        st.markdown(f"### Esercizio {row.get('ID Progressivo','')}")
        st.markdown(f"<div class='scenario-box'>{row.get('Scenario', row.get('Domanda',''))}</div>", unsafe_allow_html=True)
        
        if not st.session_state.answered:
            st.info("Risolvi l'esercizio e poi controlla.")
            if st.button("👁️ MOSTRA SOLUZIONI", type="primary"): 
                st.session_state.answered = True
                st.rerun()
        else:
            sol_data = {
                "Parametro": ["Distanza", "Velocità", "Carburante", "Punto Partenza", "Punto Arrivo"],
                "Soluzione": [row.get(f'Soluzione {i+1}') for i in range(5)]
            }
            st.table(pd.DataFrame(sol_data))
            c1, c2 = st.columns(2)
            if c1.button("✅ HO FATTO GIUSTO"): answer(True); next_question(); st.rerun()
            if c2.button("❌ HO SBAGLIATO"): answer(False); next_question(); st.rerun()

    # QUIZ NORMALI
    else:
        # Se siamo in quiz base ma il dato è corrotto (es. residuo di carteggio)
        if 'Risposta A' not in row:
             st.session_state.current_row = None
             st.rerun()

        c1, c2 = st.columns([1, 2])
        with c1:
            pth = get_image_path(row.get('NomeImmagine'))
            if pth: 
                st.image(Image.open(pth), width=300) 
            else: 
                st.markdown("<div class='placeholder-img'>NESSUNA IMMAGINE</div>", unsafe_allow_html=True)
        
        with c2:
            st.markdown(f"##### {row.get('Argomento','Argomento')}")
            st.markdown(f"### {row.get('Domanda')}")
            st.write("")
            
            for i, opt in enumerate(st.session_state.shuffled_options):
                disabled = st.session_state.answered
                # Logica Colori Bottoni
                if disabled:
                    if opt['ok']: label = f"✅ {opt['txt']}"
                    elif not opt['ok'] and "btn_press" in st.session_state and st.session_state.btn_press == i: label = f"❌ {opt['txt']}"
                    else: label = opt['txt']
                else:
                    label = f"{chr(65+i)}. {opt['txt']}"

                if st.button(label, key=f"btn_{i}", disabled=disabled, use_container_width=True):
                    st.session_state.btn_press = i
                    answer(opt['ok'])
                    st.rerun()
            
            # Bottone Next
            if st.session_state.answered:
                if st.button("AVANTI ➡", type="primary", use_container_width=True):
                    next_question()
                    st.rerun()

# Avvio automatico (se reset o avvio)
if st.session_state.current_row is None:
    reset_game(False)
    st.rerun()