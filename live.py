import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    MIN_HEIGHT = 180  # Altezza minima per ogni box attrezzo (regolabile!)

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1400px;}
        .attrezzo-header {
            background: #002d5d;
            color: #fff;
            text-align: center;
            padding: 16px 0 10px 0;
            font-size: 2.1rem;
            font-weight: 900;
            letter-spacing: 2px;
            border-radius: 15px;
            margin-bottom: 6px;
            margin-top: 8px;
            min-height: 68px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .attrezzo-content {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 120px;
        }
        .atleta-name {
            text-align: center;
            font-size: 2.05rem;
            font-weight: 800;
            color: #111;
            letter-spacing: 1.2px;
            margin: 15px 0 10px 0;
            text-transform: uppercase;
        }
        .score-show {
            text-align: center;
            font-size: 3.2rem;
            font-weight: 900;
            color: #16bb50;
            text-shadow: 0 2px 8px #d8ffe8;
            margin-bottom: 10px;
        }
        .score-pending {
            text-align: center;
            font-size: 1.35rem;
            color: #fa9900;
            font-weight: 800;
            margin-bottom: 12px;
        }
        .done-rot {
            text-align: center;
            background: #eaffea;
            color: #0a5d0a;
            font-size: 1.20rem;
            border-radius: 9px;
            padding: 8px 0 6px 0;
            margin-top: 18px;
        }
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 10px; color: #003366; font-weight: 900; font-size:2.7rem;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(f"<h3 style='text-align: center; margin-top: 0; color:#206; font-size:2.1rem;'><span style='font-size:1.55em;'>&#128260;</span> Rotazione <b>{rotazione_corrente}</b></h3>", unsafe_allow_html=True)

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    logica_classifica = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    usa_logica_olimpica = logica_classifica and logica_classifica[0] == "olimpica"

    if show_ranking_active:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        col_map = [col1, col2, col3, col1, col2, col3]
        col_classifica = col4
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        col_map = [col1, col2, col3, col1, col2, col3]
        col_classifica = col3

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        # Box titolo attrezzo
        col.markdown(f"<div class='attrezzo-header' style='min-height:58px'>{attrezzo}</div>", unsafe_allow_html=True)

        # Box contenuto attrezzo con min-height fissa per allineamento verticale
        col.markdown(f"<div class='attrezzo-content' style='min-height:{MIN_HEIGHT}px'>", unsafe_allow_html=True)

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        if not atleti:
            col.markdown("<div class='score-pending' style='color:#226;'>Nessun atleta assegnato.</div>", unsafe_allow_html=True)
            col.markdown("</div>", unsafe_allow_html=True)
            continue

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.markdown("<div class='done-rot'>✅ Tutti gli atleti hanno completato la rotazione.</div>", unsafe_allow_html=True)
            col.markdown("</div>", unsafe_allow_html=True)
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]
        col.markdown(f"<div class='atleta-name'>{nome}</div>", unsafe_allow_html=True)

        score_row = c.execute("""
            SELECT score FROM scores 
            WHERE athlete_id = ? AND apparatus = ?
        """, (atleta_id, attrezzo)).fetchone()

        if score_row:
            punteggio = round(score_row[0], 3)
            timer_key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
            shown_at = st.session_state["score_timers"].get(timer_key)

            if shown_at is None:
                st.session_state["score_timers"][timer_key] = now
            if now - st.session_state["score_timers"][timer_key] < 20:
                col.markdown(f"<div class='score-show'>{punteggio:.3f}</div>", unsafe_allow_html=True)
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.markdown("<div class='score-pending'>⏳ In attesa del punteggio...</div>", unsafe_allow_html=True)

        col.markdown("</div>", unsafe_allow_html=True)

    if tutti_attrezzi_completati:
        st.markdown("<div class='done-rot'>Tutti gli attrezzi hanno completato la rotazione.<br>Attendere l'avanzamento manuale.</div>", unsafe_allow_html=True)

    # (Classifica provvisoria se necessario, puoi inserire qui sotto)

    conn.close()
