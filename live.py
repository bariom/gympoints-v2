import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1400px;}
        .attrezzo-box {
            background: #f6fbff;
            border: 3px solid #0074c7;
            border-radius: 22px;
            min-height: 175px;
            margin-bottom: 32px;
            margin-top: 16px;
            box-shadow: 0 4px 18px #b2d8ff44;
            padding: 14px 4px 18px 4px;
            text-align: center;
        }
        .attrezzo-label {
            background: #0074c7;
            color: #fff;
            font-size: 1.4rem;
            font-weight: 800;
            border-radius: 14px;
            display: inline-block;
            padding: 7px 26px 7px 26px;
            margin-bottom: 10px;
        }
        .atleta-name {
            font-size: 1.32rem;
            font-weight: 700;
            color: #222;
            margin: 13px 0 7px 0;
        }
        .score-ok {
            color: #009966;
            font-size: 2.9rem;
            font-weight: bold;
            margin: 7px 0 12px 0;
            letter-spacing: 2px;
            text-shadow: 0 2px 8px #d8ffe8;
        }
        .score-pending {
            color: #ff9900;
            font-size: 1.4rem;
            font-weight: 800;
            margin: 7px 0 4px 0;
        }
        .empty-assign {
            background: #eaf2fa;
            color: #111;
            border-radius: 9px;
            font-size: 1.13rem;
            margin: 20px auto 7px auto;
            padding: 8px 15px 8px 15px;
            display: inline-block;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 8px; color: #003366; letter-spacing: 1px; font-weight: 900;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(f"<h3 style='text-align: center; margin-top: 0; color:#206;'><span style='font-size:1.35em;'>&#128260;</span> Rotazione <b>{rotazione_corrente}</b></h3>", unsafe_allow_html=True)

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    # 2 colonne x 3 righe
    grid = [attrezzi[:2], attrezzi[2:4], attrezzi[4:]]
    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    for riga in grid:
        cols = st.columns(2, gap="large")
        for i, attrezzo in enumerate(riga):
            with cols[i]:
                st.markdown('<div class="attrezzo-box">', unsafe_allow_html=True)
                st.markdown(f'<div class="attrezzo-label">{attrezzo}</div>', unsafe_allow_html=True)
                atleti = c.execute("""
                    SELECT a.id, a.name || ' ' || a.surname AS nome
                    FROM rotations r
                    JOIN athletes a ON a.id = r.athlete_id
                    WHERE r.apparatus = ? AND r.rotation_order = ?
                    ORDER BY r.id
                """, (attrezzo, rotazione_corrente)).fetchall()

                if not atleti:
                    st.markdown('<div class="empty-assign">Nessun atleta assegnato.</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    continue

                key_prog = f"{attrezzo}_index_{rotazione_corrente}"
                index = st.session_state["progresso_live"].get(key_prog, 0)

                if index >= len(atleti):
                    st.markdown('<div class="score-pending" style="color:#229933;">Tutti completato!</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    continue

                atleta_id, nome = atleti[index]
                st.markdown(f'<div class="atleta-name">{nome}</div>', unsafe_allow_html=True)

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
                        st.markdown(f'<div class="score-ok">{punteggio:.3f}</div>', unsafe_allow_html=True)
                    else:
                        st.session_state["progresso_live"][key_prog] = index + 1
                else:
                    st.markdown('<div class="score-pending">⏳ In attesa del punteggio...</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    conn.close()
