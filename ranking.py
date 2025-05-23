import streamlit as st
import sqlite3
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_ranking():
    # Auto-refresh ogni 10 secondi
    st_autorefresh(interval=10_000, key="auto_refresh")

    if "ranking_page" not in st.session_state:
        st.session_state["ranking_page"] = 0

    conn = get_connection()
    c = conn.cursor()

    # Controlla logica classifica
    logica_row = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    logica_classifica = logica_row[0] if logica_row else "olimpica"

    query = """
    SELECT 
        a.name || ' ' || a.surname AS Atleta,
        a.club AS Società,
        SUM(s.score) AS Totale
    FROM scores s
    JOIN athletes a ON a.id = s.athlete_id
    GROUP BY s.athlete_id
    ORDER BY Totale DESC
    """

    try:
        results = c.execute(query).fetchall()
    except Exception as e:
        st.error(f"Errore durante l'esecuzione della classifica: {e}")
        conn.close()
        return

    # Titolo competizione
    nome = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    conn.close()

    if not results:
        st.warning("Nessun punteggio disponibile per la classifica.")
        return

    if nome:
        st.markdown(f"<h2 style='text-align: center;'>{nome[0]}</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Classifica Generale - All Around</h3>", unsafe_allow_html=True)

    per_page = 15
    total_pages = (len(results) - 1) // per_page + 1
    current_page = st.session_state["ranking_page"]
    start = current_page * per_page
    end = start + per_page
    display_data = results[start:end]

    html = """<table style='width: 90%; margin: auto; border-collapse: collapse; font-size: 22px;'>
        <thead>
            <tr style='background-color: #003366; color: white; text-align: center;'>
                <th style='padding: 8px;'>Posizione</th>
                <th style='padding: 8px;'>Atleta</th>
                <th style='padding: 8px;'>Società</th>
                <th style='padding: 8px;'>Totale</th>
            </tr>
        </thead>
        <tbody>
    """

    posizione = 1
    posizione_effettiva = 1
    punteggio_precedente = None

    for i, row in enumerate(display_data, start=start + 1):
        nome, club, totale = row
        if punteggio_precedente is not None:
            if totale == punteggio_precedente:
                pass  # posizione effettiva resta invariata
            else:
                if use_olympic_logic:
                    posizione_effettiva = posizione
                else:
                    posizione_effettiva += 1
        else:
            posizione_effettiva = 1

        if posizione_effettiva == 1:
            bg = "#FFD700"
        elif posizione_effettiva == 2:
            bg = "#C0C0C0"
        elif posizione_effettiva == 3:
            bg = "#CD7F32"
        else:
            bg = "#f0f8ff" if i % 2 == 0 else "#ffffff"

        html += f"""
        <tr style='text-align: center; background-color: {bg};'>
            <td style='padding: 6px; font-weight: bold;'>{posizione_effettiva}</td>
            <td style='padding: 6px;'>{nome}</td>
            <td style='padding: 6px;'>{club}</td>
            <td style='padding: 6px; font-weight: bold; color: #006600;'>{totale:.3f}</td>
        </tr>
        """

        punteggio_precedente = totale
        posizione += 1

    html += "</tbody></table>"
    st.components.v1.html(html, height=700, scrolling=True)

    st.session_state["ranking_page"] = (current_page + 1) % total_pages