import streamlit as st
from db import get_connection

def show_giudice():
    st.set_page_config(page_title="Accesso Giudice", layout="centered")
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

    # Cerca giudice
    giudice = c.execute("""
        SELECT id, name, surname, apparatus FROM judges
        WHERE LOWER(surname) = ? AND code = ?
    """, (cognome, codice)).fetchone()

    if not giudice:
        st.error("Giudice non trovato o codice errato.")
        conn.close()
        return

    giudice_id, nome, cognome, attrezzo = giudice
    st.success(f"Benvenuto {nome} {cognome.upper()} – Attrezzo: {attrezzo}")

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

    # Atleti della rotazione corrente per quell'attrezzo
    rotazioni = c.execute("""
        SELECT r.id, a.name || ' ' || a.surname
        FROM rotations r
        JOIN athletes a ON a.id = r.athlete_id
        WHERE r.apparatus = ? AND r.rotation_order = ?
        ORDER BY r.id
    """, (attrezzo, rotazione_corrente)).fetchall()

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
                """, (atleta_id, attrezzo, giudice_id)).fetchone()

                if existing:
                    st.warning("Hai già assegnato un punteggio a questo atleta.")
                else:
                    c.execute("""
                        INSERT INTO scores (apparatus, athlete_id, judge_id, score)
                        VALUES (?, ?, ?, ?)
                    """, (attrezzo, atleta_id, giudice_id, punteggio))
                    conn.commit()
                    st.success("Punteggio salvato correttamente.")

    conn.close()
