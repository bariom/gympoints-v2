import streamlit as st
import sqlite3
from db import get_connection

def show_ranking():
    st.title("Classifica Generale - All Around")

    conn = get_connection()
    c = conn.cursor()

    query = """
    SELECT 
        a.name || ' ' || a.surname AS Atleta,
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
    if results:
        st.dataframe(results, use_container_width=True)
    else:
        st.info("Nessun punteggio disponibile per la classifica.")

    conn.close()