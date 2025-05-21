import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    # Auto-refresh ogni 20 secondi
    st_autorefresh(interval=20000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    rotazione_corrente = st.session_state.get("rotazione_corrente", 1)
    st.title(f"Live Gara – Rotazione {rotazione_corrente}")

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    col1, col2, col3 = st.columns(3)
    col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}

    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        col.subheader(attrezzo)

        # Ottieni tutti gli atleti per attrezzo e rotazione corrente
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

        # Stato per attrezzo
        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.success("Tutti gli atleti hanno completato la rotazione.")
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]
        col.markdown(f"### {nome}")

        # Recupera punteggi
        scores = c.execute("""
            SELECT score FROM scores 
            WHERE athlete_id = ? AND apparatus = ?
        """, (atleta_id, attrezzo)).fetchall()

        if len(scores) == 2:
            media = round(sum(s[0] for s in scores) / 2, 3)
            timer_key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
            shown_at = st.session_state["score_timers"].get(timer_key)

            if shown_at is None:
                st.session_state["score_timers"][timer_key] = now
                col.success(f"Punteggio: {media:.3f}")
            elif now - shown_at < 20:
                col.success(f"Punteggio: {media:.3f}")
            else:
                # Passa al prossimo atleta
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.warning("In attesa del punteggio di entrambi i giudici")

    if tutti_attrezzi_completati:
        st.info("Tutti gli attrezzi hanno completato la rotazione. Passare manualmente alla prossima.")
