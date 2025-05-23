import streamlit as st
import sqlite3
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_ranking():
    st_autorefresh(interval=10_000, key="auto_refresh")

    if "ranking_page" not in st.session_state:
        st.session_state["ranking_page"] = 0

    conn = get_connection()
    c = conn.cursor()

    # Recupera logica classifica
    logic_row = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    logic = logic_row[0] if logic_row else "olimpica"
    use_olympic_logic = logic == "olimpica"

    # Recupera nome competizione
    nome = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    nome_competizione = nome[0] if nome else None

    # Query classifica
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

    conn.close()

    if not results:
        st.warning("Nessun punteggio disponibile per la classifica.")
        return

    per_page = 15
    total_pages = (len(results) - 1) // per_page + 1
    current_page = st.session_state["ranking_page"]
    start = current_page * per_page
    end = start + per_page
    display_data = results[start:end]

    if nome_competizione:
        st.markdown(f"<h2 style='text-align: center;'>{nome_competizione}</h2>", unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: center;'>Classifica Generale - All Around</h3>", unsafe_allow_html=True)

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

    last_score = None
    position = 0

    for i, row in enumerate(display_data, start=1):
        nome, club, totale = row
        bg = "#f0f8ff" if i % 2 == 0 else "#ffffff"

        if use_olympic_logic:
            if totale != last_score:
                position = i
        else:
            position += 1

        last_score = totale

        if position == 1:
            bg = "#FFD700"
        elif position == 2:
            bg = "#C0C0C0"
        elif position == 3:
            bg = "#CD7F32"

        html += f"""
        <tr style='text-align: center; background-color: {bg};'>
            <td style='padding: 6px; font-weight: bold;'>{position}</td>
            <td style='padding: 6px;'>{nome}</td>
            <td style='padding: 6px;'>{club}</td>
            <td style='padding: 6px; font-weight: bold; color: #006600;'>{totale:.3f}</td>
        </tr>
        """

    html += "</tbody></table>"
    st.components.v1.html(html, height=700, scrolling=True)

    # Prossima pagina
    st.session_state["ranking_page"] = (current_page + 1) % total_pages
