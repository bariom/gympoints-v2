
import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh
from PIL import Image
import os
import base64
from io import BytesIO

def image_to_base64(path):
    with open(path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    MIN_HEIGHT = 210
    IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1400px;}
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(
            "<h2 style='text-align: center; margin-bottom: 10px; color: #003366; font-weight: 900; font-size:2.7rem;'>"
            f"{nome_comp[0]}</h2>",
            unsafe_allow_html=True
        )

    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(
        "<h3 style='text-align: center; margin-top: 0; color:#206; font-size:2.1rem;'>"
        "<span style='font-size:1.55em;'>&#128260;</span> Rotazione <b>{}</b></h3>".format(rotazione_corrente),
        unsafe_allow_html=True
    )

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    col1, col2, col3 = st.columns([1, 1, 1])
    col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        # AGGIUNTA SINCRONIZZAZIONE INDEX
        if index >= len(atleti) and len(atleti) > 0:
            index = len(atleti) - 1
            st.session_state["progresso_live"][key_prog] = index

        if not atleti:
            contenuto = "<span style='font-size: 1.23rem; font-weight:600; color:#bed6f2;'>Nessun atleta assegnato.</span>"
        elif index >= len(atleti):
            contenuto = "<span style='font-size: 1.12rem; color: #ace5b6;'>✅ Tutti gli atleti hanno completato la rotazione.</span>"
        else:
            tutti_attrezzi_completati = False
            atleta_id, nome = atleti[index]
            score_row = c.execute("""
                SELECT d, e, penalty, score FROM scores 
                WHERE athlete_id = ? AND apparatus = ?
            """, (atleta_id, attrezzo)).fetchone()
            if score_row:
                d, e, penalty, totale = score_row
                timer_key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
                shown_at = st.session_state["score_timers"].get(timer_key)
                if shown_at is None:
                    st.session_state["score_timers"][timer_key] = now
                if now - st.session_state["score_timers"][timer_key] < 20:
                    dettaglio = (
                        f"<div style='font-size:1.8rem; margin-bottom:5px;'>"
                        f"D: {d:.1f} &nbsp;&nbsp; E: {e:.1f} &nbsp;&nbsp; "
                        f"<span style='color:#25e56b; font-weight:900; font-size:2.3rem;'>TOT: {totale:.3f}</span>"
                        f"</div>"
                    )
                    contenuto = (
                        f"<div style='font-size:2.02rem; font-weight:800; color:#fff; margin-bottom:6px;'>{nome}</div>"
                        f"{dettaglio}"
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

        nome_file_icona = attrezzo + ".png"
        percorso_icona = os.path.join(IMG_DIR, nome_file_icona)

        if os.path.exists(percorso_icona):
            img_b64 = image_to_base64(percorso_icona)
            img_html = f"<img src='{img_b64}' width='90' style='margin-bottom:12px;'/>"
        else:
            img_html = f"<div style='font-size: 1.5rem; font-weight: 700; margin-bottom: 8px;'>{attrezzo}</div>"

        col.markdown(
            f"""
            <div style='
                background: #002d5d;
                color: white;
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
                padding: 15px 10px 15px 10px;'>
                {img_html}
                <div style='width:100%;'>{contenuto}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if tutti_attrezzi_completati:
        st.markdown(
            "<div style='background:#eaffea; color:#0a5d0a; text-align:center; font-size:1.18rem; border-radius: 9px; padding:10px; margin-top:18px;'>"
            "Tutti gli atleti hanno completato la rotazione."
            "</div>",
            unsafe_allow_html=True
        )

    conn.close()
