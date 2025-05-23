
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

    # Verifica logica da usare
    logic_row = c.execute("SELECT value FROM state WHERE key = 'ranking_logic'").fetchone()
    use_olympic_logic = logic_row and logic_row[0] == "olympic"

    query = '''
    SELECT 
        a.name || ' ' || a.surname AS Atleta,
        a.club AS Società,
        SUM(s.score) AS Totale
    FROM scores s
    JOIN athletes a ON a.id = s.athlete_id
    GROUP BY s.athlete_id
    ORDER BY Totale DESC
    '''

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

    # Titolo competizione
    nome = None
    conn = get_connection()
    c = conn.cursor()
    try:
        nome = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    finally:
        conn.close()

    if nome:
        st.markdown(f"<h2 style='text-align: center;'>{nome[0]}</h2>", unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: center;'>Classifica Generale - All Around</h3>", unsafe_allow_html=True)

    # Calcola posizioni con logica scelta
    positions = []
    prev_score = None
    real_position = 0
    last_assigned = 0

    for i, row in enumerate(display_data):
        score = row[2]
        real_position += 1
        if score != prev_score:
            position = real_position if use_olympic_logic else last_assigned + 1
        else:
            position = last_assigned
        positions.append(position)
        prev_score = score
        last_assigned = position

    # Costruzione tabella HTML
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

    for pos, row in zip(positions, display_data):
        bg = "#FFD700" if pos == 1 else "#C0C0C0" if pos == 2 else "#CD7F32" if pos == 3 else "#f0f8ff" if pos % 2 == 0 else "#ffffff"
        html += f"""
        <tr style='text-align: center; background-color: {bg};'>
            <td style='padding: 6px; font-weight: bold;'>{pos}</td>
            <td style='padding: 6px;'>{row[0]}</td>
            <td style='padding: 6px;'>{row[1]}</td>
            <td style='padding: 6px; font-weight: bold; color: #006600;'>{row[2]:.3f}</td>
        </tr>
        """

    html += "</tbody></table>"
    st.components.v1.html(html, height=700, scrolling=True)

    st.session_state["ranking_page"] = (current_page + 1) % total_pages
