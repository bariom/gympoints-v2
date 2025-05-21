import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=5000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

    st.markdown(f"<h1 style='text-align: center; font-size: 36px; font-weight: 700; margin-bottom: 12px;'>Rotazione {rotazione_corrente}</h1>", unsafe_allow_html=True)

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
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

        col.markdown(f"""
        <div style="
            background-color: #003366;
            border-radius: 12px;
            padding: 6px 12px;
            margin-bottom: 6px;
            text-align: center;
            color: white;
            font-size: 18px;
            font-weight: bold;
        ">
            {attrezzo.upper()}
        </div>
        """, unsafe_allow_html=True)

        col.markdown("<div style='min-height: 180px;'>", unsafe_allow_html=True)

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        if not atleti:
            col.markdown("<div style='text-align:center; font-size:14px;'>Nessun atleta assegnato.</div>", unsafe_allow_html=True)
            col.markdown("</div>", unsafe_allow_html=True)
            continue

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"
        index = st.session_state["progresso_live"].get(key_prog, 0)

        if index >= len(atleti):
            col.markdown("<div style='text-align:center; font-size:14px; color:#00cc99;'>Tutti gli atleti hanno completato la rotazione.</div>", unsafe_allow_html=True)
            col.markdown("</div>", unsafe_allow_html=True)
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]

        col.markdown(f"""
        <div style='text-align:center; font-size:18px; font-weight:600; color:#111; margin-bottom:4px;'>
            {nome}
        </div>
        """, unsafe_allow_html=True)

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

            if shown_at is None or now - shown_at < 20:
                col.markdown(f"""
                <div style="
                    background-color: #f4f4f4;
                    border: 2px solid #00cc99;
                    border-radius: 8px;
                    padding: 10px;
                    text-align: center;
                    font-size: 28px;
                    font-weight: bold;
                    color: #009977;
                    margin-bottom: 6px;
                ">
                    {media:.3f}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
        else:
            col.markdown(f"""
            <div style='text-align:center; font-size:14px; color:#ff9933;'>
                ⏳ In attesa del punteggio di entrambi i giudici
            </div>
            """, unsafe_allow_html=True)

        col.markdown("</div>", unsafe_allow_html=True)

    if tutti_attrezzi_completati:
        st.markdown("""
        <div style='text-align:center; font-size:18px; color:#00cc99; margin-top: 20px;'>
            Tutti gli attrezzi hanno completato la rotazione.<br>
            Attendere l'avanzamento alla prossima rotazione.
        </div>
        """, unsafe_allow_html=True)

    conn.close()
