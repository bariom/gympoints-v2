import streamlit as st
import sqlite3
from streamlit_autorefresh import st_autorefresh
from db import get_connection

def show_live():
    st.title("Visualizzazione Live Gara")

    # Refresh automatico ogni 20 secondi
    st_autorefresh(interval=20000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    cols = st.columns(3)

    for i, apparatus in enumerate(attrezzi):
        with cols[i % 3]:
            st.subheader(apparatus)
            rot = c.execute("""
                SELECT a.name, a.surname, r.id FROM rotations r
                JOIN athletes a ON a.id = r.athlete_id
                WHERE r.apparatus = ?
                ORDER BY r.rotation_order
                LIMIT 1
            """, (apparatus,)).fetchone()

            if rot:
                st.markdown(f"**{rot[0]} {rot[1]}**")
                scores = c.execute("SELECT score FROM scores WHERE athlete_id = (SELECT athlete_id FROM rotations WHERE id = ?) AND apparatus = ?", (rot[2], apparatus)).fetchall()
                if len(scores) == 2:
                    avg = sum(s[0] for s in scores) / 2
                    st.success(f"Punteggio: {avg:.2f}")
                else:
                    st.warning("In attesa di punteggi...")
            else:
                st.info("Nessun atleta in rotazione")

    conn.close()