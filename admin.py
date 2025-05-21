import streamlit as st
import sqlite3
import pandas as pd
from io import StringIO
from db import get_connection

def show_admin():
    st.title("Amministrazione Gara")

    conn = get_connection()
    c = conn.cursor()

    tab1, tab2, tab3, tab4 = st.tabs(["Atleti", "Giudici", "Rotazioni", "Punteggi"])

    with tab1:
        st.subheader("Gestione Atleti")

        if st.button("Esporta elenco atleti in CSV"):
            df = pd.read_sql_query("SELECT name, surname, club, category FROM athletes", conn)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "atleti.csv", "text/csv")

        uploaded_file = st.file_uploader("Importa elenco atleti da CSV", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                exists = c.execute("""
                    SELECT 1 FROM athletes 
                    WHERE name = ? AND surname = ? AND club = ? AND category = ?
                """, (row['name'], row['surname'], row['club'], row['category'])).fetchone()
                if not exists:
                    c.execute("INSERT INTO athletes (name, surname, club, category) VALUES (?, ?, ?, ?)",
                              (row['name'], row['surname'], row['club'], row['category']))
            conn.commit()
            st.success("Atleti importati correttamente")

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
        athletes = c.execute("SELECT id, name || ' ' || surname || ' (' || club || ')' FROM athletes").fetchall()


        st.markdown("### Aggiungi nuova rotazione")
        with st.form("add_rotation"):
            athlete_id = st.selectbox("Atleta", athletes, format_func=lambda x: x[1], key="add_select")
            apparatus = st.selectbox("Attrezzo", ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"], key="add_apparatus")
            rotation_order = st.number_input("Ordine di rotazione", min_value=1, step=1, key="add_order")
            if st.form_submit_button("Aggiungi rotazione"):
                c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                          (apparatus, athlete_id[0], rotation_order))
                conn.commit()
                st.success("Rotazione aggiunta correttamente")

        st.markdown("### Modifica o elimina rotazione esistente")
        rotation_rows = c.execute("SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus FROM rotations r JOIN athletes a ON a.id = r.athlete_id ORDER BY r.apparatus, r.rotation_order").fetchall()
        rotation_map = {row[1]: row[0] for row in rotation_rows}

        if rotation_map:
            selected_label = st.selectbox("Seleziona una rotazione da modificare o eliminare", list(rotation_map.keys()), key="edit_select")
            if selected_label in rotation_map:
                selected_rotation_id = rotation_map[selected_label]

                with st.form("edit_rotation"):
                    new_athlete_id = st.selectbox("Nuovo Atleta", athletes, format_func=lambda x: x[1], key="edit_athlete")
                    new_apparatus = st.selectbox("Nuovo Attrezzo", ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"], key="edit_apparatus")
                    new_order = st.number_input("Nuovo Ordine di Rotazione", min_value=1, step=1, key="edit_order")
                    delete = st.checkbox("Elimina questa rotazione")
                    if st.form_submit_button("Applica modifiche"):
                        if delete:
                            c.execute("DELETE FROM rotations WHERE id = ?", (selected_rotation_id,))
                            st.success("Rotazione eliminata")
                        else:
                            c.execute("UPDATE rotations SET athlete_id = ?, apparatus = ?, rotation_order = ? WHERE id = ?",
                                      (new_athlete_id[0], new_apparatus, new_order, selected_rotation_id))
                            st.success("Rotazione aggiornata correttamente")
                        conn.commit()
        else:
            st.info("Nessuna rotazione disponibile da modificare.")

        st.markdown("### Elenco rotazioni")
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



    st.markdown("### Generazione automatica rotazioni 2–6")

    # Definizione ordine attrezzi
    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    attrezzo_to_next = {attrezzi[i]: attrezzi[(i + 1) % len(attrezzi)] for i in range(len(attrezzi))}

    if st.button("🔁 Reset rotazioni"):
        c.execute("DELETE FROM rotations")
        conn.commit()
        st.success("Tutte le rotazioni sono state eliminate.")

    if st.button("👁️ Visualizza anteprima rotazioni 2–6"):
        data_r1 = c.execute("""
            SELECT r.apparatus, r.athlete_id, r.rotation_order, a.name || ' ' || a.surname
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.rotation_order = 1
            ORDER BY r.id
        """).fetchall()

        gruppi = {att: [] for att in attrezzi}
        for app, athlete_id, rot, full_name in data_r1:
            gruppi[app].append((athlete_id, full_name))

        for rot in range(2, 7):
            st.markdown(f"#### Rotazione {rot}")
            nuovo_gruppi = {att: [] for att in attrezzi}
            for att in attrezzi:
                from_group = list(gruppi[attrezzo_to_next[att]])
                from_group.reverse()
                nuovo_gruppi[att] = from_group
                st.markdown(f"**{att}**:")
                for idx, (aid, name) in enumerate(from_group, start=1):
                    st.write(f"{idx}. {name}")
            gruppi = nuovo_gruppi

    if st.button("✅ Genera e salva rotazioni 2–6"):
        data_r1 = c.execute("""
            SELECT r.apparatus, r.athlete_id, r.rotation_order
            FROM rotations r
            WHERE r.rotation_order = 1
            ORDER BY r.id
        """).fetchall()

        gruppi = {att: [] for att in attrezzi}
        for app, athlete_id, order in data_r1:
            gruppi[app].append(athlete_id)

        for rot in range(2, 7):
            nuovo_gruppi = {att: [] for att in attrezzi}
            for att in attrezzi:
                from_att = list(gruppi[attrezzo_to_next[att]])
                from_att.reverse()
                nuovo_gruppi[att] = from_att
                for idx, athlete_id in enumerate(from_att):
                    c.execute("""
                        INSERT INTO rotations (apparatus, athlete_id, rotation_order)
                        VALUES (?, ?, ?)
                    """, (att, athlete_id, rot))
            gruppi = nuovo_gruppi

        conn.commit()
        st.success("Rotazioni 2–6 generate e salvate correttamente.")


    with tab4:
        st.subheader("Inserimento Punteggi")

        # Recupera la rotazione corrente
        rotazione_corrente = st.session_state.get("rotazione_corrente", 1)

        # Ottieni le rotazioni disponibili per la rotazione corrente
        rotations = c.execute("""
            SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.rotation_order = ?
            ORDER BY r.apparatus
        """, (rotazione_corrente,)).fetchall()

        if not rotations:
            st.info("Nessuna rotazione disponibile per la rotazione corrente.")
        else:
            with st.form("add_score"):
                rotation = st.selectbox("Rotazione", rotations, format_func=lambda x: x[1], key="select_rotation")

                if rotation:
                    app = c.execute("SELECT apparatus, athlete_id FROM rotations WHERE id = ?",
                                    (rotation[0],)).fetchone()
                    apparatus, athlete_id = app

                    judges = c.execute("""
                        SELECT id, name || ' ' || surname || ' (' || apparatus || ')'
                        FROM judges
                        WHERE apparatus = ?
                    """, (apparatus,)).fetchall()

                    judge = st.selectbox("Giudice", judges, format_func=lambda x: x[1], key="judge_dynamic")

                    score = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05)

                    if st.form_submit_button("Registra punteggio"):
                        existing = c.execute("""
                            SELECT 1 FROM scores
                            WHERE apparatus = ? AND athlete_id = ? AND judge_id = ?
                        """, (apparatus, athlete_id, judge[0])).fetchone()

                        if existing:
                            st.error(
                                "Questo giudice ha già inserito un punteggio per questo atleta su questo attrezzo.")
                        else:
                            c.execute("""
                                INSERT INTO scores (apparatus, athlete_id, judge_id, score)
                                VALUES (?, ?, ?, ?)
                            """, (apparatus, athlete_id, judge[0], score))
                            conn.commit()
                            st.success("Punteggio registrato correttamente")

                if not judges:
                    st.warning(f"Nessun giudice assegnato a {apparatus}")
                else:
                    judge = st.selectbox("Giudice", judges, format_func=lambda x: x[1])
                    score = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05)
                    if st.form_submit_button("Registra punteggio"):
                        # Verifica se esiste già un punteggio inserito dallo stesso giudice
                        existing = c.execute("""
                            SELECT 1 FROM scores
                            WHERE apparatus = ? AND athlete_id = ? AND judge_id = ?
                        """, (apparatus, athlete_id, judge[0])).fetchone()

                        if existing:
                            st.error(
                                "Questo giudice ha già inserito un punteggio per questo atleta su questo attrezzo.")
                        else:
                            c.execute("""
                                INSERT INTO scores (apparatus, athlete_id, judge_id, score)
                                VALUES (?, ?, ?, ?)
                            """, (apparatus, athlete_id, judge[0], score))
                            conn.commit()
                            st.success("Punteggio registrato correttamente")

        st.dataframe(c.execute("SELECT * FROM scores").fetchall(), use_container_width=True)

    tab5 = st.tabs(["Stato Gara"])[0]
    with tab5:
        st.subheader("Gestione Stato Rotazione")
        current_rotation = st.number_input("Rotazione corrente", min_value=1, step=1, value=st.session_state.get("rotazione_corrente", 1))
        if st.button("Aggiorna rotazione"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("rotazione_corrente", str(current_rotation)))
            conn.commit()
            st.session_state["progresso_live"] = {}
            st.session_state["score_timers"] = {}
            st.success(f"Rotazione impostata a {current_rotation}")

    conn.close()