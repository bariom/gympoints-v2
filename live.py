import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=5000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    # Recupera impostazioni
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    # Titolo competizione
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='text-align: center;'>Rotazione {rotazione_corrente}</h4>", unsafe_allow_html=True)

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    if show_ranking_active:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
        col_map = [col1, col2, col3, col1, col2, col3]
    else:
        col1, col2, col3 = st.columns(3)
        col_map = [col1, col2, col3, col1, col2, col3]

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]

        # intestazione attrezzo in stile blu
        col.markdown(
            f"<div style='background-color:#003366; color:white; text-align:center; padding:8px; border-radius:6px; font-weight:bold; font-size:18px;'>{attrezzo.upper()}</div>",
            unsafe_allow_html=True
        )

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
        col.markdown(f"<div style='font-size:26px; text-align: center; font-weight: 600;'>{nome}</div>", unsafe_allow_html=True)

        # Recupera punteggi
        scores = c.execute("""
            SELECT score FROM scores 
            WHERE athlete_id = ? AND apparatus = ?
        """, (atleta_id, attrezzo)).fetchall()

        if len(scores) == 2:
            media = round(sum(s[0] for s in scores) / 2, 3)
            timer_key = f"{attrezzo}_{atleta_id}_{rotazione_corrente}"
            shown_at = st.session_state["score_timers"].get(timer_key)

            if shown_at is None:
                st.session_state["score_timers"][timer_key] = now
                col.success(f"{media:.3f}")
            elif now - shown_at < 20:
                col.success(f"{media:.3f}")
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.warning("⏳ In attesa del punteggio di entrambi i giudici")

    if tutti_attrezzi_completati:
        st.info("Tutti gli attrezzi hanno completato la rotazione. Attendere l'avanzamento manuale.")

    # Se attivo, mostra classifica a lato
    if show_ranking_active:
        with col4:
            st.markdown("<h4 style='text-align: center;'>Classifica</h4>", unsafe_allow_html=True)

            classifica = c.execute("""
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
                LIMIT 10
            """).fetchall()

            for i, row in enumerate(classifica, start=1):
                st.markdown(f"<div style='font-size:18px;'>{i}. {row[0]} — <b>{row[1]:.3f}</b></div>", unsafe_allow_html=True)

    conn.close()
