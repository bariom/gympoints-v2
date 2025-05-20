import streamlit as st
import sqlite3
from db import get_connection

def show_admin():
    st.title("Amministrazione Gara")

    conn = get_connection()
    c = conn.cursor()

    tab1, tab2, tab3, tab4 = st.tabs(["Atleti", "Giudici", "Rotazioni", "Punteggi"])

    with tab1:
        st.subheader("Gestione Atleti")
        with st.form("add_athlete"):
            name = st.text_input("Nome")
            surname = st.text_input("Cognome")
            club = st.text_input("Società")
            category = st.text_input("Categoria")
            if st.form_submit_button("Aggiungi atleta"):
                c.execute("INSERT INTO athletes (name, surname, club, category) VALUES (?, ?, ?, ?)",
                          (name, surname, club, category))
                conn.commit()
        st.dataframe(c.execute("SELECT * FROM athletes").fetchall(), use_container_width=True)

    with tab2:
        st.subheader("Gestione Giudici")
        with st.form("add_judge"):
            name = st.text_input("Nome Giudice")
            surname = st.text_input("Cognome Giudice")
            apparatus = st.selectbox("Attrezzo", ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"])
            if st.form_submit_button("Aggiungi giudice"):
                c.execute("INSERT INTO judges (name, surname, apparatus) VALUES (?, ?, ?)",
                          (name, surname, apparatus))
                conn.commit()
        st.dataframe(c.execute("SELECT * FROM judges").fetchall(), use_container_width=True)

    with tab3:
        st.subheader("Gestione Rotazioni")
        athletes = c.execute("SELECT id, name || ' ' || surname FROM athletes").fetchall()
        with st.form("add_rotation"):
            athlete_id = st.selectbox("Atleta", athletes, format_func=lambda x: x[1])
            apparatus = st.selectbox("Attrezzo", ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"])
            rotation_order = st.number_input("Ordine di rotazione", min_value=1, step=1)
            if st.form_submit_button("Aggiungi rotazione"):
                c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                          (apparatus, athlete_id[0], rotation_order))
                conn.commit()

        rot_table = c.execute("""
            SELECT 
                r.id AS ID,
                r.apparatus AS Attrezzo,
                a.name || ' ' || a.surname AS Atleta,
                r.rotation_order AS Ordine
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            ORDER BY r.apparatus, r.rotation_order
        """).fetchall()
        st.dataframe(rot_table, use_container_width=True)

    with tab4:
        st.subheader("Inserimento Punteggi")
        rotations = c.execute("SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus FROM rotations r JOIN athletes a ON a.id = r.athlete_id ORDER BY r.rotation_order").fetchall()
        judges = c.execute("SELECT id, name || ' ' || surname FROM judges").fetchall()
        with st.form("add_score"):
            rotation = st.selectbox("Rotazione", rotations, format_func=lambda x: x[1])
            judge = st.selectbox("Giudice", judges, format_func=lambda x: x[1])
            score = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05)
            if st.form_submit_button("Registra punteggio"):
                app = c.execute("SELECT apparatus, athlete_id FROM rotations WHERE id = ?", (rotation[0],)).fetchone()
                c.execute("INSERT INTO scores (apparatus, athlete_id, judge_id, score) VALUES (?, ?, ?, ?)",
                          (app[0], app[1], judge[0], score))
                conn.commit()
        st.dataframe(c.execute("SELECT * FROM scores").fetchall(), use_container_width=True)

    conn.close()
