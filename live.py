
import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st.set_page_config(layout="wide")
    st_autorefresh(interval=5000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    st.markdown(f"<h2 style='text-align: center; margin-bottom: 5px;'>Rotazione {rotazione_corrente}</h2>", unsafe_allow_html=True)

    col_attrezzi, col_classifica = st.columns([2, 1])

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    col1, col2, col3 = col_attrezzi.columns(3)
    col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        col.markdown(f"<div style='background-color: #003366; color: white; text-align: center; padding: 6px; font-size: 22px; font-weight: bold; border-radius: 4px;'>{attrezzo}</div>", unsafe_allow_html=True)

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        if not atleti:
            col.info("Nessun atleta assegnato.")
            continue

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.success("Tutti gli atleti hanno completato la rotazione.")
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]
        col.markdown(f"<div style='text-align: center; font-size: 20px; margin-top: 10px;'><b>{nome}</b></div>", unsafe_allow_html=True)

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
                col.markdown(f"<div style='text-align: center; font-size: 28px; font-weight: bold; color: #009966;'>{punteggio:.3f}</div>", unsafe_allow_html=True)
            elif now - shown_at < 20:
                col.markdown(f"<div style='text-align: center; font-size: 28px; font-weight: bold; color: #009966;'>{punteggio:.3f}</div>", unsafe_allow_html=True)
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.warning("⏳ In attesa del punteggio")

    if tutti_attrezzi_completati:
        st.info("Tutti gli attrezzi hanno completato la rotazione. Attendere l'avanzamento manuale.")

    if show_ranking_active:
        with col_classifica:
            st.markdown("<h4 style='text-align: center;'>Classifica provvisoria</h4>", unsafe_allow_html=True)

            classifica = c.execute("""
                SELECT 
                    a.name || ' ' || a.surname AS Atleta,
                    a.club,
                    SUM(score) AS Totale
                FROM scores s
                JOIN athletes a ON a.id = s.athlete_id
                GROUP BY s.athlete_id
                ORDER BY Totale DESC
                LIMIT 30
            """).fetchall()

            left, mid, right = st.columns(3)
            for i, row in enumerate(classifica, start=1):
                block = f"<b>{i}. {row[0]}</b><br><i>{row[1]}</i> — <b>{row[2]:.3f}</b><br><br>"
                if i <= 10:
                    left.markdown(block, unsafe_allow_html=True)
                elif i <= 20:
                    mid.markdown(block, unsafe_allow_html=True)
                else:
                    right.markdown(block, unsafe_allow_html=True)

    conn.close()
