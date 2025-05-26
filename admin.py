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

    tab1, tab2, tab3, tab4 = st.tabs(["Atleti", "Giudici", "Rotazioni", "Impostazioni"])

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

        # --- AGGIUNTA NUOVO GIUDICE ---
        with st.form("add_judge"):
            name = st.text_input("Nome Giudice")
            surname = st.text_input("Cognome Giudice")
            apparatus = st.selectbox("Attrezzo",
                                     ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"])
            add_judge = st.form_submit_button("Aggiungi giudice")
            if add_judge:
                code = genera_codice_giudice(name, surname)
                c.execute("INSERT INTO judges (name, surname, apparatus, code) VALUES (?, ?, ?, ?)",
                          (name, surname, apparatus, code))
                conn.commit()
                st.success(f"Giudice aggiunto. Codice accesso: {code}")
                st.rerun()
                return

        # --- TABELLA GIUDICI ---
        df_giudici = pd.read_sql_query(
            "SELECT name, surname, apparatus, code FROM judges ORDER BY surname, name, apparatus", conn
        )
        st.dataframe(df_giudici, use_container_width=True)

        # --- MODIFICA o ELIMINA assegnazione giudice-attrezzo ---
        st.markdown("### Modifica o elimina assegnazione giudice-attrezzo")

        # Recupera tutte le assegnazioni
        assegnazioni = c.execute(
            "SELECT id, name, surname, apparatus, code FROM judges ORDER BY surname, name, apparatus"
        ).fetchall()

        if assegnazioni:
            select_key = f"edit_judge_assign_{len(assegnazioni)}"
            labels = [
                f"{row[1]} {row[2]} – {row[3]} [codice: {row[4]}]" for row in assegnazioni
            ]
            id_map = {label: row[0] for label, row in zip(labels, assegnazioni)}

            selected_label = st.selectbox(
                "Seleziona un’assegnazione da modificare o eliminare",
                labels,
                key=select_key
            )
            if selected_label:
                judge_id = id_map[selected_label]
                # Prendi i dettagli correnti
                current_row = next(row for row in assegnazioni if row[0] == judge_id)
                nome_corr, cognome_corr, apparatus_corr = current_row[1], current_row[2], current_row[3]

                form_key = f"form_edit_judge_assign_{judge_id}"
                with st.form(form_key):
                    new_name = st.text_input("Nome", value=nome_corr)
                    new_surname = st.text_input("Cognome", value=cognome_corr)
                    new_apparatus = st.selectbox(
                        "Attrezzo",
                        ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"],
                        index=["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"].index(
                            apparatus_corr)
                    )
                    delete = st.checkbox("Elimina questa assegnazione")
                    submitted = st.form_submit_button("Applica modifiche")
                    if submitted:
                        if delete:
                            c.execute("DELETE FROM judges WHERE id = ?", (judge_id,))
                            conn.commit()
                            st.success("Assegnazione eliminata con successo.")
                            st.rerun()
                            return
                        else:
                            code = genera_codice_giudice(new_name, new_surname)
                            c.execute(
                                "UPDATE judges SET name = ?, surname = ?, apparatus = ?, code = ? WHERE id = ?",
                                (new_name, new_surname, new_apparatus, code, judge_id)
                            )
                            conn.commit()
                            st.success("Assegnazione aggiornata con successo.")
                            st.rerun()
                            return
        else:
            st.info("Nessuna assegnazione giudice-attrezzo da modificare.")

        # --- QR CODE GIUDICI (visualizzazione manuale) ---
        st.markdown("### QR Code di accesso giudici")
        url_base = st.text_input("URL base dell'applicazione",
                                 value=st.session_state.get("url_base", "https://gympoints.streamlit.app"))
        st.session_state["url_base"] = url_base

        giudici = c.execute("SELECT name, surname, code FROM judges").fetchall()
        giudici_dict = {f"{name} {surname} [{code}]": (name, surname, code) for name, surname, code in giudici}
        select_qr_key = f"select_qr_{len(giudici)}"
        selezione = st.selectbox("Seleziona un giudice per visualizzare il QR:", list(giudici_dict.keys()),
                                 key=select_qr_key)

        if selezione:
            name, surname, code = giudici_dict[selezione]
            giudice_key = f"{surname.strip().lower()}{code}"
            full_url = f"{url_base}/?giudice={giudice_key}"
            qr_img = qrcode.make(full_url)
            buf = io.BytesIO()
            qr_img.save(buf)
            buf.seek(0)
            st.markdown(f"#### {name} {surname} - Codice: {code}")
            st.image(buf, caption=full_url, width=250)

    with tab3:
        st.subheader("Gestione Rotazioni")
        attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

        athletes = c.execute("SELECT id, name || ' ' || surname || ' (' || club || ')' FROM athletes").fetchall()

        st.markdown("### Aggiungi nuova rotazione")
        with st.form("add_rotation"):
            athlete_id = st.selectbox("Atleta", athletes, format_func=lambda x: x[1], key="add_select")
            apparatus = st.selectbox("Attrezzo", attrezzi, key="add_apparatus")
            rotation_order = st.number_input("Ordine di rotazione", min_value=1, step=1, key="add_order")
            if st.form_submit_button("Aggiungi rotazione"):
                c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                          (apparatus, athlete_id[0], rotation_order))
                conn.commit()
                st.success("Rotazione aggiunta correttamente")



        st.markdown("### Elenco rotazioni")
        rot_table = c.execute("""
            SELECT 
                r.id AS ID,
                r.apparatus AS Attrezzo,
                a.name || ' ' || a.surname AS Atleta,
                r.rotation_order AS Ordine
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            ORDER BY r.rotation_order, r.apparatus, r.id
        """).fetchall()
        st.dataframe(rot_table, use_container_width=True)

        st.markdown("### Modifica o elimina rotazione esistente")
        rotation_rows = c.execute(
            "SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus FROM rotations r JOIN athletes a ON a.id = r.athlete_id ORDER BY r.rotation_order, r.apparatus").fetchall()
        rotation_map = {row[1]: row[0] for row in rotation_rows}

        if rotation_map:
            selected_label = st.selectbox("Seleziona una rotazione da modificare o eliminare",
                                          list(rotation_map.keys()), key="edit_select")
            if selected_label in rotation_map:
                selected_rotation_id = rotation_map[selected_label]
                with st.form("edit_rotation"):
                    new_athlete_id = st.selectbox("Nuovo Atleta", athletes, format_func=lambda x: x[1],
                                                  key="edit_athlete")
                    new_apparatus = st.selectbox("Nuovo Attrezzo", attrezzi, key="edit_apparatus")
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

        st.markdown("### Elimina intera rotazione")

        # Recupera tutti i numeri di rotazione esistenti
        rotation_orders = [row[0] for row in c.execute(
            "SELECT DISTINCT rotation_order FROM rotations ORDER BY rotation_order").fetchall()]
        if rotation_orders:
            selected_rot = st.selectbox(
                "Seleziona la rotazione da eliminare (elimina TUTTI i record di questa rotazione):", rotation_orders,
                key="delete_rotazione")
            if st.button("Elimina rotazione selezionata"):
                c.execute("DELETE FROM rotations WHERE rotation_order = ?", (selected_rot,))
                conn.commit()
                st.success(f"Rotazione {selected_rot} eliminata completamente.")
                st.rerun()
                return
        else:
            st.info("Nessuna rotazione esistente da eliminare.")

        st.markdown("### Generazione automatica rotazioni 2–6")

        if st.button("🔁 Reset rotazioni"):
            c.execute("DELETE FROM rotations")
            conn.commit()
            st.success("Tutte le rotazioni sono state eliminate.")

        # ---- Simulazione logica olimpica ----
        if st.button("👁️ Visualizza anteprima rotazioni 2–6"):
            # Recupera gruppi di atleti per ogni attrezzo in rotazione 1
            gruppi = []
            nomi_gruppi = []
            for att in attrezzi:
                atleti_per_attrezzo = c.execute("""
                    SELECT a.name || ' ' || a.surname
                    FROM rotations r
                    JOIN athletes a ON a.id = r.athlete_id
                    WHERE r.rotation_order = 1 AND r.apparatus = ?
                    ORDER BY r.id
                """, (att,)).fetchall()
                nomi_gruppi.append([x[0] for x in atleti_per_attrezzo])

            # Ruota i gruppi tra attrezzi, E ruota la lista interna degli atleti a sinistra a ogni rotazione
            for rot in range(2, 7):
                # Ruota atleti dentro ogni gruppo (olimpica tra atleti)
                nomi_gruppo_ruotati = []
                for gruppo in nomi_gruppi:
                    if gruppo:
                        gruppo_rotato = gruppo[1:] + gruppo[:1]  # shift a sinistra
                    else:
                        gruppo_rotato = []
                    nomi_gruppo_ruotati.append(gruppo_rotato)
                # Ruota i gruppi tra attrezzi (olimpica tra attrezzi)
                nomi_gruppi = nomi_gruppo_ruotati[-1:] + nomi_gruppo_ruotati[:-1]  # ruota gruppi a destra

                st.markdown(f"#### Rotazione {rot}")
                for att, gruppo in zip(attrezzi, nomi_gruppi):
                    st.markdown(f"**{att}**:")
                    if gruppo:
                        for idx, name in enumerate(gruppo, start=1):
                            st.write(f"{idx}. {name}")
                    else:
                        st.write("_(vuoto)_")

        # ---- Salva rotazioni olimpiche ----
        if st.button("✅ Genera e salva rotazioni 2–6"):
            # Recupera gruppi di atleti per ogni attrezzo in rotazione 1 (id!)
            ids_gruppi = []
            for att in attrezzi:
                athlete_ids = c.execute("""
                    SELECT athlete_id
                    FROM rotations
                    WHERE rotation_order = 1 AND apparatus = ?
                    ORDER BY id
                """, (att,)).fetchall()
                ids_gruppi.append([x[0] for x in athlete_ids])

            for rot in range(2, 7):
                # Ruota atleti dentro ogni gruppo (olimpica tra atleti)
                ids_gruppo_ruotati = []
                for gruppo in ids_gruppi:
                    if gruppo:
                        gruppo_rotato = gruppo[1:] + gruppo[:1]  # shift a sinistra
                    else:
                        gruppo_rotato = []
                    ids_gruppo_ruotati.append(gruppo_rotato)
                # Ruota i gruppi tra attrezzi (olimpica tra attrezzi)
                ids_gruppi = ids_gruppo_ruotati[-1:] + ids_gruppo_ruotati[:-1]  # ruota gruppi a destra

                for att, gruppo in zip(attrezzi, ids_gruppi):
                    for athlete_id in gruppo:
                        c.execute("""
                            INSERT INTO rotations (apparatus, athlete_id, rotation_order)
                            VALUES (?, ?, ?)
                        """, (att, athlete_id, rot))
            conn.commit()
            st.success("Rotazioni 2–6 generate e salvate correttamente.")


    # with tab4:
    #     st.subheader("Inserimento Punteggi")
    #
    #     # Recupera la rotazione corrente
    #     rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    #
    #     # Ottieni le rotazioni disponibili per la rotazione corrente
    #     rotations = c.execute("""
    #         SELECT r.id, a.name || ' ' || a.surname || ' - ' || r.apparatus
    #         FROM rotations r
    #         JOIN athletes a ON a.id = r.athlete_id
    #         WHERE r.rotation_order = ?
    #         AND (
    #             SELECT COUNT(*) FROM scores s
    #             WHERE s.athlete_id = r.athlete_id AND s.apparatus = r.apparatus
    #         ) < 2
    #         ORDER BY r.apparatus
    #     """, (rotazione_corrente,)).fetchall()
    #
    #     if not rotations:
    #         st.info("Nessuna rotazione disponibile per la rotazione corrente.")
    #     else:
    #         selected_rotation = st.selectbox(
    #             "Seleziona atleta e attrezzo",
    #             options=rotations,
    #             format_func=lambda x: x[1],
    #             key="select_rotation"
    #         )
    #
    #         if selected_rotation:
    #             rotation_id = selected_rotation[0]
    #             app_row = c.execute(
    #                 "SELECT apparatus, athlete_id FROM rotations WHERE id = ?", (rotation_id,)
    #             ).fetchone()
    #             apparatus, athlete_id = app_row
    #
    #             judges = c.execute("""
    #                 SELECT id, name || ' ' || surname || ' (' || apparatus || ')'
    #                 FROM judges
    #                 WHERE apparatus = ?
    #             """, (apparatus,)).fetchall()
    #
    #             with st.form(f"add_score_form_{rotation_id}"):
    #                 st.markdown(f"**Attrezzo:** {apparatus}")
    #
    #                 if not judges:
    #                     st.warning(f"Nessun giudice assegnato a {apparatus}")
    #                 else:
    #                     judge = st.selectbox("Giudice", judges, format_func=lambda x: x[1], key=f"judge_{rotation_id}")
    #                     score = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05, key=f"score_{rotation_id}")
    #
    #                     if st.form_submit_button("Registra punteggio"):
    #                         existing = c.execute("""
    #                             SELECT 1 FROM scores
    #                             WHERE apparatus = ? AND athlete_id = ? AND judge_id = ?
    #                         """, (apparatus, athlete_id, judge[0])).fetchone()
    #
    #                         if existing:
    #                             st.error("Questo giudice ha già inserito un punteggio per questo atleta su questo attrezzo.")
    #                         else:
    #                             c.execute("""
    #                                 INSERT INTO scores (apparatus, athlete_id, judge_id, score)
    #                                 VALUES (?, ?, ?, ?)
    #                             """, (apparatus, athlete_id, judge[0], score))
    #                             conn.commit()
    #                             st.success("Punteggio registrato correttamente")
    #
    #     st.markdown("### Tutti i punteggi")
    #
    #     df = pd.read_sql_query("""
    #         SELECT
    #             a.name || ' ' || a.surname AS Atleta,
    #             j.name || ' ' || j.surname AS Giudice,
    #             s.apparatus AS Attrezzo,
    #             s.score AS Punteggio
    #         FROM scores s
    #         JOIN athletes a ON a.id = s.athlete_id
    #         JOIN judges j ON j.id = s.judge_id
    #         ORDER BY s.apparatus, Atleta
    #     """, conn)
    #
    #     st.dataframe(df, use_container_width=True)


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

        # Mostra classifica finale
        show_final_ranking = c.execute("SELECT value FROM state WHERE key = 'show_final_ranking'").fetchone()
        show_final_default = show_final_ranking[0] == "1" if show_final_ranking else False
        show_final_toggle = st.toggle("Mostra classifica finale", value=show_final_default)

        if st.button("Salva impostazioni"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("nome_competizione", nome_competizione))
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)",
                      ("show_ranking_live", "1" if show_ranking_toggle else "0"))
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)",
                      ("show_final_ranking", "1" if show_final_toggle else "0"))
            conn.commit()
            st.success("Impostazioni aggiornate.")

    conn.close()
