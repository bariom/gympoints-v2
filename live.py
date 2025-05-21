import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st.set_page_config(page_title="Live Gara", layout="wide")

    # Auto-refresh ogni 20 secondi
    st_autorefresh(interval=20000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    # Recupera la rotazione corrente (globale per tutti gli attrezzi)
    rotazione_corrente = st.session_state.get("rotazione_corrente", 1)
    st.title(f"Live Gara – Rotazione {rotazione_corrente}")

    # Lista degli attrezzi
    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    col1, col2, col3 = st.columns(3)
    col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        col.subheader(attrezzo)

        # Trova atleta della rotazione corrente per l'attrezzo
        row = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
        """, (attrezzo, rotazione_corrente)).fetchone()

        if row:
            atleta_id, nome = row
            col.markdown(f"### {nome}")

            # Verifica i punteggi presenti
            scores = c.execute("""
                SELECT score FROM scores 
                WHERE athlete_id = ? AND apparatus = ?
            """, (atleta_id, attrezzo)).fetchall()

            if len(scores) == 2:
                media = round(sum(s[0] for s in scores) / 2, 3)
                key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
                shown_at = st.session_state["score_timers"].get(key)

                if shown_at is None:
                    st.session_state["score_timers"][key] = now
                    col.success(f"Punteggio: {media:.3f}")
                elif now - shown_at < 20:
                    col.success(f"Punteggio: {media:.3f}")
                else:
                    col.info("Punteggio mostrato. Passare alla prossima rotazione manualmente.")
            else:
                col.warning("In attesa del punteggio di entrambi i giudici")
        else:
            col.info("Nessun atleta assegnato a questa rotazione")

    conn.close()
