import time
import streamlit as st
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_live():
    st_autorefresh(interval=5000, key="refresh_live")

    conn = get_connection()
    c = conn.cursor()

    rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

    st.markdown(f"<h1 style='text-align: center; font-size: 36px; font-weight: 700;'>Rotazione {rotazione_corrente}</h1>", unsafe_allow_html=True)

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

        atleti = c.execute("""
            SELECT a.id, a.name || ' ' || a.surname AS nome
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (attrezzo, rotazione_corrente)).fetchall()

        key_prog = f"{attrezzo}_index_{rotazione_corrente}"

        if not atleti:
            html = f"""
            <div style="text-align: center; background-color: #f8f9fc; border-radius: 10px; padding: 16px; min-height: 160px;">
                <div style="background-color: #003366; color: white; padding: 8px 12px; border-radius: 6px;
                            font-size: 18px; font-weight: bold; margin-bottom: 10px;">
                    {attrezzo.upper()}
                </div>
                <div style="font-size:14px; color:#999;">Nessun atleta assegnato.</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
            continue

        index = st.session_state["progresso_live"].get(key_prog, 0)
        if index >= len(atleti):
            html = f"""
            <div style="text-align: center; background-color: #f8f9fc; border-radius: 10px; padding: 16px; min-height: 160px;">
                <div style="background-color: #003366; color: white; padding: 8px 12px; border-radius: 6px;
                            font-size: 18px; font-weight: bold; margin-bottom: 10px;">
                    {attrezzo.upper()}
                </div>
                <div style="font-size:14px; color:#00cc99;">Tutti gli atleti hanno completato la rotazione.</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
            continue

        tutti_attrezzi_completati = False
        atleta_id, nome = atleti[index]

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
                shown_at = now

            if now - shown_at < 20:
                contenuto = f"""
                <div style="font-size: 20px; font-weight: 600; margin-bottom: 6px;">{nome}</div>
                <div style="font-size: 32px; font-weight: bold; color: #00aa66;">{media:.3f}</div>
                """
            else:
                st.session_state["progresso_live"][key_prog] = index + 1
                contenuto = f"<div style='font-size: 20px; font-weight: 600;'>{nome}</div>"
        else:
            contenuto = f"""
            <div style="font-size: 20px; font-weight: 600; margin-bottom: 6px;">{nome}</div>
            <div style="font-size:14px; color:#ff9933;">
                ⏳ In attesa del punteggio di entrambi i giudici
            </div>
            """

        html = f"""
        <div style="text-align: center; background-color: #f8f9fc; border-radius: 10px; padding: 16px; min-height: 160px;">
            <div style="background-color: #003366; color: white; padding: 8px 12px; border-radius: 6px;
                        font-size: 18px; font-weight: bold; margin-bottom: 10px;">
                {attrezzo.upper()}
            </div>
            {contenuto}
        </div>
        """
        col.markdown(html, unsafe_allow_html=True)

    if tutti_attrezzi_completati:
        st.markdown("""
        <div style="text-align:center; font-size:18px; color:#00cc99; margin-top: 20px;">
            Tutti gli attrezzi hanno completato la rotazione.<br>
            Attendere l'avanzamento alla prossima rotazione.
        </div>
        """, unsafe_allow_html=True)

    conn.close()
