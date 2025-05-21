import streamlit as st
import sqlite3
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_ranking():


    # Auto-refresh ogni 10 secondi
    count = st_autorefresh(interval=10_000, key="auto_refresh")

    # Gestione paginazione
    if "ranking_page" not in st.session_state:
        st.session_state["ranking_page"] = 0

    conn = get_connection()
    c = conn.cursor()

    query = """
    SELECT 
        a.name || ' ' || a.surname AS Atleta,
        a.club AS Società,
        SUM(avg_score) AS Totale
    FROM (
        SELECT 
            s.apparatus,
            s.athlete_id,
            AVG(s.score) AS avg_score
        FROM scores s
        GROUP BY s.apparatus, s.athlete_id
        HAVING COUNT(*) = 2
    ) AS sub
    JOIN athletes a ON a.id = sub.athlete_id
    GROUP BY sub.athlete_id
    ORDER BY Totale DESC
    """

    results = c.execute(query).fetchall()
    conn.close()

    if not results:
        st.warning("Nessun punteggio disponibile per la classifica.")
        return

    per_page = 20
    total_pages = (len(results) - 1) // per_page + 1

    # Aggiorna pagina ogni 10 secondi
    current_page = st.session_state["ranking_page"]
    start = current_page * per_page
    end = start + per_page
    display_data = results[start:end]

    st.markdown(
        f"<h2 style='text-align: center;'>Classifica Generale - All Around</h2>",
        unsafe_allow_html=True
    )

    # Tabella HTML centrata e leggibile
    html = """
    <table style='width: 90%; margin: auto; border-collapse: collapse; font-size: 22px;'>
        <thead>
            <tr style='background-color: #003366; color: white;'>
                <th style='padding: 8px;'>Posizione</th>
                <th style='padding: 8px;'>Atleta</th>
                <th style='padding: 8px;'>Società</th>
                <th style='padding: 8px;'>Totale</th>
            </tr>
        </thead>
        <tbody>
    """

    for i, row in enumerate(display_data, start=start + 1):
        html += f"""
        <tr style='text-align: center; background-color: {"#f0f8ff" if i % 2 == 0 else "#ffffff"};'>
            <td style='padding: 6px; font-weight: bold;'>{i}</td>
            <td style='padding: 6px;'>{row[0]}</td>
            <td style='padding: 6px;'>{row[1]}</td>
            <td style='padding: 6px; font-weight: bold; color: #006600;'>{row[2]:.3f}</td>
        </tr>
        """

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)

    # Cambia pagina per il prossimo refresh
    st.session_state["ranking_page"] = (current_page + 1) % total_pages
