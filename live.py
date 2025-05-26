import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=2000, key="refresh_live")

    st.markdown("""
        <style>
        .main .block-container {padding-top: 0.5rem; max-width: 1280px;}
        .card-attrezzo {
            background: linear-gradient(120deg, #eaf4fc 0%, #f7fafd 100%);
            border-radius: 22px;
            box-shadow: 0 3px 12px #b2d8ff55;
            padding: 16px 12px 20px 12px;
            margin-bottom: 18px;
            min-height: 210px;
            border: 2px solid #0068c966;
        }
        .card-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #003366;
            letter-spacing: 1px;
            background: #f0f5fa;
            border-radius: 10px;
            margin-bottom: 10px;
            padding: 4px 0;
        }
        .score-pending {
            color: #ff9900; font-size: 1.7rem; font-weight: bold; margin: 14px 0;
        }
        .score-ok {
            color: #00a878; font-size: 2.5rem; font-weight: bold; margin: 14px 0; text-shadow: 1px 2px 5px #d8ffe8;
        }
        .score-fade {
            opacity: 0.6; filter: blur(1px);
        }
        .atleta-name {
            font-size: 1.2rem; font-weight: 600; margin-top: 8px; letter-spacing: 1px;
        }
        .all-done-box {
            background: #eaffea;
            color: #106610;
            font-size: 1.3rem;
            border-left: 7px solid #33bb55;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 22px;
            margin-top: 18px;
            text-align: center;
        }
        .ranking-title {
            color: #114477;
            font-size: 1.25rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 6px;
            margin-top: 12px;
            letter-spacing: 1px;
        }
        .ranking-row {
            font-size: 1.13rem;
            padding: 2px 0 2px 0;
            margin-bottom: 2px;
        }
        .ranking-gold {color: #d6af36; font-weight: 700;}
        .ranking-silver {color: #b4b4b4; font-weight: 700;}
        .ranking-bronze {color: #c97a41; font-weight: 700;}
        .ranking-me {background: #fff7d0;}
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()
    c = conn.cursor()

    # Nome competizione
    nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
    if nome_comp:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 6px; color: #003366; letter-spacing: 1px; font-weight: 900;'>{nome_comp[0]}</h2>", unsafe_allow_html=True)

    # Rotazione corrente
    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])
    st.markdown(f"<h4 style='text-align: center; margin-top: 0; color:#338;'>&#128260; Rotazione <b>{rotazione_corrente}</b></h4>", unsafe_allow_html=True)

    # Switch per mostrare classifica provvisoria
    show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
    show_ranking_active = show_ranking_live and show_ranking_live[0] == "1"

    # Switch logica classifica
    logica_classifica = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
    usa_logica_olimpica = logica_classifica and logica_classifica[0] == "olimpica"

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]

    # Colonne responsive
    col_count = 3
    cols = st.columns(col_count)

    now = time.time()
    if "progresso_live" not in st.session_state:
        st.session_state["progresso_live"] = {}
    if "score_timers" not in st.session_state:
        st.session_state["score_timers"] = {}

    tutti_attrezzi_completati = True

    for i, attrezzo in enumerate(attrezzi):
        col = cols[i % col_count]
        with col:
            st.markdown('<div class="card-attrezzo">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">{attrezzo}</div>', unsafe_allow_html=True)

            atleti = c.execute("""
                SELECT a.id, a.name || ' ' || a.surname AS nome
                FROM rotations r
                JOIN athletes a ON a.id = r.athlete_id
                WHERE r.apparatus = ? AND r.rotation_order = ?
                ORDER BY r.id
            """, (attrezzo, rotazione_corrente)).fetchall()

            if not atleti:
                st.info("Nessun atleta assegnato.")
                st.markdown('</div>', unsafe_allow_html=True)
                continue

            key_prog = f"{attrezzo}_index_{rotazione_corrente}"
            index = st.session_state["progresso_live"].get(key_prog, 0)

            if index >= len(atleti):
                st.markdown('<div class="score-pending all-done-box">✅ Tutti completato!</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                continue

            tutti_attrezzi_completati = False
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
                    # Effetto "fade" per il punteggio (visibile per 20 secondi)
                    st.markdown(f'<div class="score-ok">{punteggio:.3f}</div>', unsafe_allow_html=True)
                else:
                    st.session_state["progresso_live"][key_prog] = index + 1
            else:
                st.markdown('<div class="score-pending">⏳ In attesa del punteggio...</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)  # fine card-attrezzo

    if tutti_attrezzi_completati:
        st.markdown('<div class="all-done-box">Tutti gli attrezzi hanno completato la rotazione.<br/>Attendere l\'avanzamento manuale.</div>', unsafe_allow_html=True)

    # Mostra classifica provvisoria
    if show_ranking_active:
        st.markdown('<div class="ranking-title">Classifica provvisoria</div>', unsafe_allow_html=True)

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

        # Podio con colori diversi
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

            # Badge podio
            if posizione_effettiva == 1:
                rank_style = 'ranking-row ranking-gold'
                badge = '🥇'
            elif posizione_effettiva == 2:
                rank_style = 'ranking-row ranking-silver'
                badge = '🥈'
            elif posizione_effettiva == 3:
                rank_style = 'ranking-row ranking-bronze'
                badge = '🥉'
            else:
                rank_style = 'ranking-row'
                badge = f"<span style='font-size:1.1em;color:#337;'>#{posizione_effettiva}</span>"

            st.markdown(
                f"<div class='{rank_style}'>{badge} <b>{nome}</b> — <span style='color:#009966;font-weight:600;'>{totale:.3f}</span>"
                f"<br/><span style='font-size:0.98em;color:#6a6a6a;'>{club}</span></div>",
                unsafe_allow_html=True
            )

            punteggio_precedente = totale
            posizione += 1

    conn.close()
