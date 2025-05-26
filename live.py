import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1400px;}
        .attrezzo-header {
            background: #003366;
            color: #fff;
            text-align: center;
            padding: 10px 0 10px 0;
            font-size: 2.2rem;
            font-weight: 900;
            letter-spacing: 2px;
            border-radius: 9px;
            margin-bottom: 8px;
        }
        .atleta-name {
            text-align: center;
            font-size: 2.1rem;
            font-weight: 800;
            color: #111;
            letter-spacing: 1.5px;
            margin: 22px 0 12px 0;
            text-transform: uppercase;
        }
        .score-show {
            text-align: center;
            font-size: 3.4rem;
            font-weight: 900;
            color: #16bb50;
            text-shadow: 0 2px 8px #d8ffe8;
            margin-bottom: 15px;
        }
        .score-pending {
            text-align: center;
            font-size: 1.7rem;
            color: #fa9900;
            font-weight: 800;
            margin-bottom: 15px;
        }
        .done-rot {
            text-align: center;
            background: #eaffea;
            color: #0a5d0a;
            font-size: 1.32rem;
            border-radius: 9px;
            padding: 9px 0 7px 0;
            margin-top: 22px;
        }
        .classifica-title {
            text-align: center;
            color: #003366;
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: 1px;
            margin-bottom: 10px;
            margin-top: 18px;
        }
        .classifica-row {font-size: 1.25rem; font-weight: 700;}
        .podio1 {color: #d6af36;}
        .podio2 {color: #b4b4b4;}
        .podio3 {color: #c97a41;}
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 10px; color: #003366; font-weight: 900; font-size:2.7rem;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(f"<h3 style='text-align: center; margin-top: 0; color:#206; font-size:2.1rem;'><span style='font-size:1.55em;'>&#128260;</span> Rotazione <b>{rotazione_corrente}</b></h3>", unsafe_allow_html=True)

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    logica_classifica = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    usa_logica_olimpica = logica_classifica and logica_classifica[0] == "olimpica"

    if show_ranking_active:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        col_map = [col1, col2, col3, col1, col2, col3]
        col_classifica = col4
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        col_map = [col1, col2, col3, col1, col2, col3]
        col_classifica = col3

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = col_map[i]
        col.markdown(f"<div class='attrezzo-header'>{attrezzo}</div>", unsafe_allow_html=True)

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        if not atleti:
            col.markdown("<div class='score-pending' style='color:#226;'>Nessun atleta assegnato.</div>", unsafe_allow_html=True)
            continue

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.markdown("<div class='done-rot'>✅ Tutti gli atleti hanno completato la rotazione.</div>", unsafe_allow_html=True)
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]
        col.markdown(f"<div class='atleta-name'>{nome}</div>", unsafe_allow_html=True)

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
                col.markdown(f"<div class='score-show'>{punteggio:.3f}</div>", unsafe_allow_html=True)
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.markdown("<div class='score-pending'>⏳ In attesa del punteggio...</div>", unsafe_allow_html=True)

    if tutti_attrezzi_completati:
        st.markdown("<div class='done-rot'>Tutti gli attrezzi hanno completato la rotazione.<br>Attendere l'avanzamento manuale.</div>", unsafe_allow_html=True)

    # Mostra classifica provvisoria
    if show_ranking_active:
        col_classifica.markdown("<div class='classifica-title'>Classifica provvisoria</div>", unsafe_allow_html=True)
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

            # Colori podio
            podio = ""
            if posizione_effettiva == 1:
                podio = "podio1"
            elif posizione_effettiva == 2:
                podio = "podio2"
            elif posizione_effettiva == 3:
                podio = "podio3"

            col_classifica.markdown(
                f"<div class='classifica-row {podio}'>{posizione_effettiva}. <b>{nome}</b> — <span style='font-size:1.3em'>{totale:.3f}</span><br><span style='font-size:0.95em;font-weight:400'>{club}</span></div>",
                unsafe_allow_html=True
            )

            punteggio_precedente = totale
            posizione += 1

    conn.close()
