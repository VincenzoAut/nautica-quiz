# ui.py - Modulo Gestione Interfaccia Grafica (Fix Tablet)
import streamlit as st
import base64
import os

# --- GESTIONE SFONDI ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_backgrounds(main_bg, sidebar_bg):
    # Applica sfondo Main
    if os.path.exists(main_bg):
        bin_str = get_base64_of_bin_file(main_bg)
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url(data:image/jpg;base64,{bin_str});
            background-size: cover; /* Usa 'cover' invece di 100vw/vh per non deformare */
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Applica sfondo Sidebar
    if os.path.exists(sidebar_bg):
        bin_str = get_base64_of_bin_file(sidebar_bg)
        st.markdown(f"""
        <style>
        [data-testid="stSidebar"] {{
            background-image: url(data:image/jpg;base64,{bin_str});
            background-size: cover;
            background-position: center;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            background-color: rgba(255, 255, 255, 0.7); /* Sfondo semi-trasparente per leggere meglio */
            backdrop-filter: blur(5px); /* Effetto sfocato moderno */
        }}
        </style>
        """, unsafe_allow_html=True)

# --- CARICAMENTO CSS COMPLETO ---
def load_css():
    st.markdown("""
    <style>
        /* Layout Generale */
        .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
        
        /* FORZA TESTO SCURO (Fix per Tablet Dark Mode) */
        .stRadio label, .stMarkdown p, .stText, h1, h2, h3, .streamlit-expanderHeader {
            color: #000000 !important;
            font-weight: 500;
        }
        
        /* Bottoni */
        div.stButton > button { width: 100%; border-radius: 8px; padding: 12px; font-size: 16px; margin-bottom: 5px; background-color: #ffffff !important; border: 1px solid #ced4da !important; color: #212529 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.2s ease; }
        div.stButton > button:hover { border-color: #0d6efd !important; color: #0d6efd !important; background-color: #f8f9fa !important; transform: translateY(-1px); }
        div.stButton > button[kind="primary"] { background-color: #ff4b4b !important; color: white !important; border: none !important; font-weight: bold !important; font-size: 18px !important; padding: 15px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
        div.stButton > button[kind="primary"]:hover { background-color: #ff3333 !important; box-shadow: 0 6px 8px rgba(0,0,0,0.3); }
        
        /* Box Vari */
        .question-box { background-color: #e3f2fd; padding: 20px; border-radius: 10px; border-left: 6px solid #1565c0; margin-bottom: 20px; color: #0d47a1; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .question-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(13, 71, 161, 0.2); padding-bottom: 8px; flex-wrap: wrap; }
        .question-id { font-size: 14px; font-weight: 900; color: #1565c0; text-transform: uppercase; letter-spacing: 0.5px; }
        .question-topic { font-size: 13px; color: #455a64; font-style: italic; text-align: right; font-weight: 600; }
        .question-text { font-size: 20px; font-weight: 700; line-height: 1.5; color: #0d47a1; }
        
        /* Metriche, Risultati, Rank */
        .metric-container { display: flex; justify-content: space-between; background-color: white; padding: 5px 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); margin-bottom: 15px; }
        .metric-box { text-align: center; width: 100%; }
        .metric-label { font-size: 10px; color: #888; text-transform: uppercase; font-weight: bold; }
        .metric-value { font-size: 18px; font-weight: 800; color: #333; }
        div[data-testid="column"] button { padding: 5px 0px; font-size: 20px; border: 1px solid #ddd; background-color: transparent !important; color: #d63384 !important; font-weight: bold; }
        div[data-testid="column"] button:hover { background-color: #fce4ec !important; border-color: #d63384 !important; }
        .result-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; color: #000; font-weight: 600; border: 1px solid rgba(0,0,0,0.1); font-size: 15px; }
        .rank-box { background: linear-gradient(135deg, #0061f2 0%, #00c6f7 100%); padding: 15px; border-radius: 8px; color: white; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
        .rank-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; font-weight: bold; }
        .rank-name { font-size: 22px; font-weight: 800; margin: 5px 0; }
        
        /* Esiti e Footer */
        .exam-pass { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #c3e6cb; margin-bottom: 20px; }
        .exam-fail { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #f5c6cb; margin-bottom: 20px; }
        .review-end { background-color: #e2e3e5; color: #383d41; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #d6d8db; margin-bottom: 20px; }
        .footer-sidebar { font-size: 11px; color: #000000 !important; text-align: center; margin-top: 30px; padding-top: 10px; border-top: 1px solid #999; line-height: 1.6; font-weight: 600; }
        .footer-sidebar a { color: #0061f2; text-decoration: none; font-weight: bold; }
        
        /* Login */
        .login-container { background-color: rgba(255, 255, 255, 0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); text-align: center; border: 1px solid rgba(255, 255, 255, 0.18); }
        .login-title { font-size: 32px; font-weight: 800; color: #0061f2; margin-bottom: 5px; }
        .login-subtitle { font-size: 14px; color: #555; margin-bottom: 25px; font-weight: 500; }
        .footer-login { position: fixed; bottom: 20px; right: 20px; text-align: right; color: white; font-size: 14px; font-weight: bold; background-color: rgba(0,0,0,0.5); padding: 10px 15px; border-radius: 10px; backdrop-filter: blur(5px); }
        
        /* Debug */
        .debug-info { font-size: 11px; color: #495057; background: #e9ecef; padding: 5px; border-radius: 4px; margin-bottom: 10px; border: 1px dashed #adb5bd; }
    </style>
    """, unsafe_allow_html=True)

# --- COMPONENTI HTML (WIDGETS VISIVI) ---
def draw_login_header(version_text):
    st.markdown(f"""
    <div class="login-container">
        <div class="login-title">⚓ Patente Nautica SRS</div>
        <div class="login-subtitle">{version_text}</div>
    </div>
    """, unsafe_allow_html=True)

def draw_login_footer():
    st.markdown("""
    <div class='footer-login'>
        <b>Footer & Credits</b><br>
        Developed by Vincenzo Autolitano
    </div>
    """, unsafe_allow_html=True)

def draw_question_card(id_prog, argomento, voce, testo):
    st.markdown(f"""
    <div class="question-box">
        <div class="question-header">
            <span class="question-id">DOMANDA {id_prog}</span>
            <span class="question-topic">{argomento} - <i>{voce}</i></span>
        </div>
        <div class="question-text">{testo}</div>
    </div>
    """, unsafe_allow_html=True)

def draw_rank_box(rank_name, current, target):
    st.markdown(f"""
    <div class="rank-box">
        <div class="rank-title">IL TUO GRADO</div>
        <div class="rank-name">{rank_name}</div>
        <div class="rank-next">{current} / {target} Consolidate</div>
    </div>
    """, unsafe_allow_html=True)

def draw_stat_metric(label, value, sub_text="", color="blue"):
    colors = {
        "blue": "#e3f2fd", "green": "#d1e7dd", "red": "#f8d7da", "yellow": "#fff3cd"
    }
    bg = colors.get(color, "#f8f9fa")
    text_col = "#0d47a1" if color == "blue" else ("#0f5132" if color == "green" else "#842029")
    
    st.markdown(f"""
    <div style="background-color: {bg}; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase;">{label}</div>
        <div style="font-size: 24px; font-weight: 800; color: {text_col}; margin: 5px 0;">{value}</div>
        <div style="font-size: 11px; font-style: italic; color: #555;">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)