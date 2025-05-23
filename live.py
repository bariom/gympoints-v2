import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=5000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 5px;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(f"<h4 style='text-align: center; margin-top: 0;'>Rotazione {rotazione_corrente}</h4>", unsafe_allow_html=True)

    # Switch per mostrare classifica provvisoria
    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    # Switch logica classifica
    logica_classifica = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    usa_logica_olimpica = logica_classifica and logica_classifica[0] == "olimpica"

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
    col1, col2, col3 = st.columns([1, 1, 1]) if not show_ranking_active else st.columns([1, 1, 1, 1])
    col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        col.markdown(f"<div style='background-color: #003366; color: white; text-align: center; padding: 6px; font-size: 22px; font-weight: bold; border-radius: 4px;'>{attrezzo}</div>", unsafe_allow_html=True)

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        if not atleti:
            col.info("Nessun atleta assegnato.")
            continue

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.success("Tutti gli atleti hanno completato la rotazione.")
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]
        col.markdown(f"<div style='text-align: center; font-size: 20px; margin-top: 10px;'><b>{nome}</b></div>", unsafe_allow_html=True)

        score_row = c.execute("""
            SELECT score FROM scores 
            WHERE athlete_id = ? AND apparatus = ?
        """, (atleta_id, attrezzo)).fetchone()

        if score_row:
            punteggio = round(score_row[0], 3)
            timer_key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
            shown_at = st.session_state["score_timers"].get(timer_key)

            if shown_at is None:
                st.session_state["score_timers"][timer_key] = now
            if now - st.session_state["score_timers"][timer_key] < 20:
                col.markdown(f"<div style='text-align: center; font-size: 28px; font-weight: bold; color: #009966;'>{punteggio:.3f}</div>", unsafe_allow_html=True)
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.warning("⏳ In attesa del punteggio")

    if tutti_attrezzi_completati:
        st.info("Tutti gli attrezzi hanno completato la rotazione. Attendere l'avanzamento manuale.")

    # Mostra classifica provvisoria
    if show_ranking_active:
        col_classifica = col_map[-1]
        col_classifica.markdown("<h4 style='text-align: center;'>Classifica provvisoria</h4>", unsafe_allow_html=True)

        classifica = c.execute("""
            SELECT 
                a.name || ' ' || a.surname AS nome,
                a.club AS club,
                SUM(s.score) AS totale
            FROM scores s
            JOIN athletes a ON a.id = s.athlete_id
            GROUP BY s.athlete_id
            ORDER BY totale DESC
        """).fetchall()

        posizione = 1
        posizione_effettiva = 1
        punteggio_precedente = None
        skip_count = 0

        for i, (nome, club, totale) in enumerate(classifica[:20], start=1):
            if punteggio_precedente is not None:
                if totale == punteggio_precedente:
                    skip_count += 1
                else:
                    if usa_logica_olimpica:
                        posizione_effettiva = posizione
                        skip_count = 1
                    else:
                        posizione_effettiva += 1
            else:
                skip_count = 1

            col_classifica.markdown(
                f"<div style='font-size:16px;'>{posizione_effettiva}. <b>{nome} — {totale:.3f}</b><br/><i>{club}</i></div>",
                unsafe_allow_html=True
            )

            punteggio_precedente = totale
            posizione += 1

    conn.close()