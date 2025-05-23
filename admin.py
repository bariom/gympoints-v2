import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from io import StringIO
from db import get_connection
import qrcode
from PIL import Image
import io

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

    def genera_codice_giudice(nome: str, cognome: str) -> str:
        combinazione = f"{nome.lower()}_{cognome.lower()}"
        hash_val = hashlib.sha256(combinazione.encode()).hexdigest()
        code = int(hash_val[:4], 16) % 10000
        return str(code).zfill(4)

    with tab2:
        st.subheader("Gestione Giudici")

        with st.form("add_judge"):
            name = st.text_input("Nome Giudice")
            surname = st.text_input("Cognome Giudice")
            apparatus = st.selectbox("Attrezzo",
                                     ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"])
            if st.form_submit_button("Aggiungi giudice"):
                code = genera_codice_giudice(name, surname)
                c.execute("INSERT INTO judges (name, surname, apparatus, code) VALUES (?, ?, ?, ?)",
                          (name, surname, apparatus, code))
                conn.commit()
                st.success(f"Giudice aggiunto. Codice accesso: {code}")

        st.dataframe(
            c.execute("SELECT name, surname, apparatus, code FROM judges").fetchall(),
            use_container_width=True
        )

        st.markdown("### QR Code di accesso giudici")
        url_base = st.text_input("URL base dell'applicazione", value=st.session_state.get("url_base", "https://gympoints.streamlit.app"))
        st.session_state["url_base"] = url_base

        giudici = c.execute("SELECT name, surname, code FROM judges").fetchall()
        giudici_dict = {f"{name} {surname} [{code}]": (name, surname, code) for name, surname, code in giudici}
        selezione = st.selectbox("Seleziona un giudice per visualizzare il QR:", list(giudici_dict.keys()))

        if selezione:
            name, surname, code = giudici_dict[selezione]
            giudice_key = f"{surname.lower()}{code}"
            full_url = f"{url_base}/?giudice={giudice_key}"
            qr_img = qrcode.make(full_url)
            buf = io.BytesIO()
            qr_img.save(buf)
            buf.seek(0)
            st.markdown(f"#### {name} {surname} - Codice: {code}")
            st.image(buf, caption=full_url, width=250)

    with tab3:
        st.subheader("Gestione Rotazioni")
        athletes = c.execute("SELECT id, name || ' ' || surname || ' (' || club || ')' FROM athletes").fetchall()

        st.markdown("### Aggiungi nuova rotazione")
        with st.form("add_rotation"):
            athlete_id = st.selectbox("Atleta", athletes, format_func=lambda x: x[1], key="add_select")
            apparatus = st.selectbox("Attrezzo",
                                     ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"],
                                     key="add_apparatus")
            rotation_order = st.number_input("Ordine di rotazione", min_value=1, step=1, key="add_order")
            if st.form_submit_button("Aggiungi rotazione"):
                c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                          (apparatus, athlete_id[0], rotation_order))
                conn.commit()
                st.success("Rotazione aggiunta correttamente")

        st.markdown("### Modifica o elimina rotazione esistente")
        rotation_rows = c.execute(
            "SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus FROM rotations r JOIN athletes a ON a.id = r.athlete_id ORDER BY r.apparatus, r.rotation_order").fetchall()
        rotation_map = {row[1]: row[0] for row in rotation_rows}

        if rotation_map:
            selected_label = st.selectbox("Seleziona una rotazione da modificare o eliminare",
                                          list(rotation_map.keys()), key="edit_select")
            if selected_label in rotation_map:
                selected_rotation_id = rotation_map[selected_label]
                with st.form("edit_rotation"):
                    new_athlete_id = st.selectbox("Nuovo Atleta", athletes, format_func=lambda x: x[1],
                                                  key="edit_athlete")
                    new_apparatus = st.selectbox("Nuovo Attrezzo",
                                                 ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele",
                                                  "Sbarra"], key="edit_apparatus")
                    new_order = st.number_input("Nuovo Ordine di Rotazione", min_value=1, step=1, key="edit_order")
                    delete = st.checkbox("Elimina questa rotazione")
                    if st.form_submit_button("Applica modifiche"):
                        if delete:
                            c.execute("DELETE FROM rotations WHERE id = ?", (selected_rotation_id,))
                            st.success("Rotazione eliminata")
                        else:
                            c.execute(
                                "UPDATE rotations SET athlete_id = ?, apparatus = ?, rotation_order = ? WHERE id = ?",
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
                ORDER BY r.apparatus, r.rotation_order
            """).fetchall()

            gruppi = {att: [] for att in attrezzi}
            nomi = {att: [] for att in attrezzi}
            for app, athlete_id, rot, full_name in data_r1:
                gruppi[app].append(athlete_id)
                nomi[app].append(full_name)

            for rot in range(2, 7):
                st.markdown(f"#### Rotazione {rot}")
                nuovo_gruppi = {}
                nuovo_nomi = {}
                for att in attrezzi:
                    # ROTAZIONE CIRCOLARE: il primo va in fondo, gli altri scalano
                    new_group = gruppi[att][1:] + gruppi[att][:1]
                    new_nomi = nomi[att][1:] + nomi[att][:1]
                    nuovo_gruppi[att] = new_group
                    nuovo_nomi[att] = new_nomi
                    st.markdown(f"**{att}**:")
                    for idx, name in enumerate(new_nomi, start=1):
                        st.write(f"{idx}. {name}")
                gruppi = nuovo_gruppi
                nomi = nuovo_nomi

        if st.button("✅ Genera e salva rotazioni 2–6"):
            data_r1 = c.execute("""
                SELECT r.apparatus, r.athlete_id, r.rotation_order
                FROM rotations r
                WHERE r.rotation_order = 1
                ORDER BY r.apparatus, r.rotation_order
            """).fetchall()

            gruppi = {att: [] for att in attrezzi}
            for app, athlete_id, order in data_r1:
                gruppi[app].append(athlete_id)

            for rot in range(2, 7):
                nuovo_gruppi = {}
                for att in attrezzi:
                    # ROTAZIONE CIRCOLARE: il primo va in fondo, gli altri scalano
                    new_group = gruppi[att][1:] + gruppi[att][:1]
                    nuovo_gruppi[att] = new_group
                    for idx, athlete_id in enumerate(new_group):
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
        rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

        # Ottieni le rotazioni disponibili per la rotazione corrente
        rotations = c.execute("""
            SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.rotation_order = ?
            AND (
                SELECT COUNT(*) FROM scores s
                WHERE s.athlete_id = r.athlete_id AND s.apparatus = r.apparatus
            ) < 2
            ORDER BY r.apparatus
        """, (rotazione_corrente,)).fetchall()

        if not rotations:
            st.info("Nessuna rotazione disponibile per la rotazione corrente.")
        else:
            selected_rotation = st.selectbox(
                "Seleziona atleta e attrezzo",
                options=rotations,
                format_func=lambda x: x[1],
                key="select_rotation"
            )

            if selected_rotation:
                rotation_id = selected_rotation[0]
                app_row = c.execute(
                    "SELECT apparatus, athlete_id FROM rotations WHERE id = ?", (rotation_id,)
                ).fetchone()
                apparatus, athlete_id = app_row

                judges = c.execute("""
                    SELECT id, name || ' ' || surname || ' (' || apparatus || ')'
                    FROM judges
                    WHERE apparatus = ?
                """, (apparatus,)).fetchall()

                with st.form(f"add_score_form_{rotation_id}"):
                    st.markdown(f"**Attrezzo:** {apparatus}")

                    if not judges:
                        st.warning(f"Nessun giudice assegnato a {apparatus}")
                    else:
                        judge = st.selectbox("Giudice", judges, format_func=lambda x: x[1], key=f"judge_{rotation_id}")
                        score = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05, key=f"score_{rotation_id}")

                        if st.form_submit_button("Registra punteggio"):
                            existing = c.execute("""
                                SELECT 1 FROM scores
                                WHERE apparatus = ? AND athlete_id = ? AND judge_id = ?
                            """, (apparatus, athlete_id, judge[0])).fetchone()

                            if existing:
                                st.error("Questo giudice ha già inserito un punteggio per questo atleta su questo attrezzo.")
                            else:
                                c.execute("""
                                    INSERT INTO scores (apparatus, athlete_id, judge_id, score)
                                    VALUES (?, ?, ?, ?)
                                """, (apparatus, athlete_id, judge[0], score))
                                conn.commit()
                                st.success("Punteggio registrato correttamente")

        st.markdown("### Tutti i punteggi")

        df = pd.read_sql_query("""
            SELECT 
                a.name || ' ' || a.surname AS Atleta,
                j.name || ' ' || j.surname AS Giudice,
                s.apparatus AS Attrezzo,
                s.score AS Punteggio
            FROM scores s
            JOIN athletes a ON a.id = s.athlete_id
            JOIN judges j ON j.id = s.judge_id
            ORDER BY s.apparatus, Atleta
        """, conn)

        st.dataframe(df, use_container_width=True)


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

        st.markdown("---")
        st.subheader("Logica di Classifica")

        # Recupera valore attuale
        current_logic = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
        current_logic = current_logic[0] if current_logic else "incrementale"

        logic_option = st.radio(
            "Scegli la logica di assegnazione delle posizioni:",
            ["incrementale", "olimpica"],
            index=0 if current_logic == "incrementale" else 1,
            horizontal=True,
            key="logica_classifica"
        )

        if st.button("Salva logica classifica"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("logica_classifica", logic_option))
            conn.commit()
            st.success(f"Logica classifica impostata su: {logic_option}")

    tab6 = st.tabs(["Impostazioni"])[0]
    with tab6:
        st.subheader("Impostazioni Generali")

        # Nome competizione
        current_name = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
        default_name = current_name[0] if current_name else ""
        nome_competizione = st.text_input("Nome competizione", value=default_name)

        # Mostra classifica nel live
        show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
        show_ranking_default = show_ranking_live[0] == "1" if show_ranking_live else False
        show_ranking_toggle = st.toggle("Mostra classifica nel Live", value=show_ranking_default)

        if st.button("Salva impostazioni"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("nome_competizione", nome_competizione))
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)",
                      ("show_ranking_live", "1" if show_ranking_toggle else "0"))
            conn.commit()
            st.success("Impostazioni aggiornate.")

    conn.close()
