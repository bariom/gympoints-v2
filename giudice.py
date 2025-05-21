import streamlit as st
from db import get_connection

def show_giudice():
    st.title("Pannello Giudice")

    params = st.query_params
    codice_param = params.get("giudice", "").strip()

    if not codice_param or len(codice_param) < 5:
        st.error("Accesso non valido. Assicurati che il link contenga il parametro corretto.")
        return

    cognome = codice_param[:-4].lower()
    codice = codice_param[-4:]

    conn = get_connection()
    c = conn.cursor()

    # Cerca giudice (uno qualsiasi con quel cognome e codice)
    giudice = c.execute("""
        SELECT id, name, surname, apparatus FROM judges
        WHERE LOWER(surname) = ? AND code = ?
        LIMIT 1
    """, (cognome, codice)).fetchone()

    if not giudice:
        st.error("Giudice non trovato o codice errato.")
        conn.close()
        return

    giudice_id, nome, cognome, attrezzo_orig = giudice

    # Trova tutti gli attrezzi assegnati al giudice
    attrezzi_giudice = c.execute("""
        SELECT DISTINCT apparatus FROM judges
        WHERE surname = LOWER(?) AND code = ?
    """, (cognome, codice)).fetchall()

    attrezzi_lista = [row[0] for row in attrezzi_giudice]
    selected_attrezzo = st.selectbox(
        "Seleziona attrezzo",
        attrezzi_lista,
        index=attrezzi_lista.index(attrezzo_orig) if attrezzo_orig in attrezzi_lista else 0
    )

    if selected_attrezzo:
        st.success(f"Benvenuto {nome} {cognome.upper()} – Attrezzo selezionato: {selected_attrezzo}")
    else:
        st.error("Errore: nessun attrezzo assegnato.")

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

    # Atleti per rotazione e attrezzo selezionato
    rotazioni = c.execute("""
        SELECT r.id, a.name || ' ' || a.surname
        FROM rotations r
        JOIN athletes a ON a.id = r.athlete_id
        WHERE r.apparatus = ? AND r.rotation_order = ?
        ORDER BY r.id
    """, (selected_attrezzo, rotazione_corrente)).fetchall()

    if not rotazioni:
        st.info("Nessun atleta in gara su questo attrezzo per la rotazione corrente.")
        conn.close()
        return

    with st.form("form_punteggio"):
        selected_rotation = st.selectbox("Seleziona atleta", rotazioni, format_func=lambda x: x[1])
        punteggio = st.number_input("Punteggio", min_value=0.0, max_value=20.0, step=0.05)

        if st.form_submit_button("Invia punteggio"):
            rot_id = selected_rotation[0]
            # Ottieni atleta
            row = c.execute("SELECT athlete_id FROM rotations WHERE id = ?", (rot_id,)).fetchone()
            if not row:
                st.error("Errore interno.")
            else:
                atleta_id = row[0]

                # Verifica se ha già votato
                existing = c.execute("""
                    SELECT 1 FROM scores
                    WHERE athlete_id = ? AND apparatus = ? AND judge_id = ?
                """, (atleta_id, selected_attrezzo, giudice_id)).fetchone()

                if existing:
                    st.warning("Hai già assegnato un punteggio a questo atleta.")
                else:
                    c.execute("""
                        INSERT INTO scores (apparatus, athlete_id, judge_id, score)
                        VALUES (?, ?, ?, ?)
                    """, (selected_attrezzo, atleta_id, giudice_id, punteggio))
                    conn.commit()
                    st.success("Punteggio salvato correttamente.")

    conn.close()
