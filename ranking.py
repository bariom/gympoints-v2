import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_ranking():
    st_autorefresh(interval=10_000, key="auto_refresh")

    if "ranking_page" not in st.session_state:
        st.session_state["ranking_page"] = 0

    conn = get_connection()
    c = conn.cursor()

    try:
        row = c.execute("SELECT value FROM state WHERE key = 'use_olympic_logic'").fetchone()
        use_olympic_logic = row and row[0] == "1"
    except:
        use_olympic_logic = True

    try:
        results = c.execute("""
            SELECT 
                a.name || ' ' || a.surname AS Atleta,
                a.club AS Società,
                SUM(s.score) AS Totale
            FROM scores s
            JOIN athletes a ON a.id = s.athlete_id
            GROUP BY s.athlete_id
            ORDER BY Totale DESC
        """).fetchall()
    except Exception as e:
        st.error(f"Errore durante l'esecuzione della classifica: {e}")
        conn.close()
        return

    nome = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
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

    if nome:
        st.markdown(f"<h2 style='text-align: center;'>{nome[0]}</h2>", unsafe_allow_html=True)

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

    pos = 1
    shown_rank = 1
    prev_score = None

    for i, row in enumerate(display_data):
        name, club, score = row
        score = round(score, 3)

        if use_olympic_logic:
            if score != prev_score:
                shown_rank = pos
        else:
            if score != prev_score:
                shown_rank = shown_rank + 1 if i > 0 else 1

        bg = "#FFD700" if shown_rank == 1 else "#C0C0C0" if shown_rank == 2 else "#CD7F32" if shown_rank == 3 else ("#f0f8ff" if i % 2 == 0 else "#ffffff")

        html += f"""
        <tr style='text-align: center; background-color: {bg};'>
            <td style='padding: 6px; font-weight: bold;'>{shown_rank}</td>
            <td style='padding: 6px;'>{name}</td>
            <td style='padding: 6px;'>{club}</td>
            <td style='padding: 6px; font-weight: bold; color: #006600;'>{score:.3f}</td>
        </tr>
        """

        prev_score = score
        pos += 1

    html += "</tbody></table>"
    st.components.v1.html(html, height=700, scrolling=True)

    st.session_state["ranking_page"] = (current_page + 1) % total_pages
