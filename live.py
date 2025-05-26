import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    MIN_HEIGHT = 210  # Altezza minima per ogni box attrezzo

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1400px;}
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(
            "<h2 style='text-align: center; margin-bottom: 10px; color: #003366; font-weight: 900; font-size:2.7rem;'>"
            f"{nome_comp[0]}</h2>",
            unsafe_allow_html=True
        )

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(
        "<h3 style='text-align: center; margin-top: 0; color:#206; font-size:2.1rem;'>"
        "<span style='font-size:1.55em;'>&#128260;</span> Rotazione <b>{}</b></h3>".format(rotazione_corrente),
        unsafe_allow_html=True
    )

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

        # Prepara contenuto del box attrezzo
        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if not atleti:
            contenuto = "<span style='font-size: 1.23rem; font-weight:600; color:#bed6f2;'>Nessun atleta assegnato.</span>"
        elif index >= len(atleti):
            contenuto = "<span style='font-size: 1.12rem; color: #ace5b6;'>✅ Tutti gli atleti hanno completato la rotazione.</span>"
        else:
            tutti_attrezzi_completati = False
            atleta_id, nome = atleti[index]
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
                    contenuto = (
                        f"<div style='font-size:2.02rem; font-weight:800; color:#fff; margin-bottom:6px;'>{nome}</div>"
                        f"<div style='font-size:2.45rem; color:#25e56b; font-weight: 900;'>{punteggio:.3f}</div>"
                    )
                else:
                    st.session_state["progresso_live"][key_prog] = index + 1
                    contenuto = (
                        f"<div style='font-size:2.02rem; font-weight:800; color:#fff; margin-bottom:6px;'>{nome}</div>"
                        f"<div style='font-size:1.1rem; color:#bed6f2;'>Aspetta il prossimo atleta...</div>"
                    )
            else:
                contenuto = (
                    f"<div style='font-size:2.02rem; font-weight:800; color:#fff; margin-bottom:6px;'>{nome}</div>"
                    f"<div style='font-size:1.19rem; color:#fa9900; margin-top: 6px;'>⏳ In attesa del punteggio...</div>"
                )

        # BOX UNICO per titolo + contenuto
        col.markdown(
            f"""
            <div style='
                background: #002d5d;
                color: white;
                font-size: 2.1rem;
                font-weight: bold;
                text-align: center;
                border-radius: 15px;
                margin-bottom: 22px;
                margin-top: 10px;
                min-height: {MIN_HEIGHT}px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                align-items: center;
                padding: 15px 10px 15px 10px;
            '>
                <div style='font-size: 2rem; font-weight: 900; margin-bottom: 12px; letter-spacing: 1.5px;'>{attrezzo}</div>
                <div style='width:100%;'>
                    {contenuto}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if tutti_attrezzi_completati:
        st.markdown(
            "<div style='background:#eaffea; color:#0a5d0a; text-align:center; font-size:1.18rem; border-radius: 9px; padding:10px; margin-top:18px;'>"
            "Tutti gli attrezzi hanno completato la rotazione.<br>Attendere l'avanzamento manuale."
            "</div>",
            unsafe_allow_html=True
        )

    # (Classifica provvisoria se necessario, puoi inserire qui sotto)

    conn.close()
