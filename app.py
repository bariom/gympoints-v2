import streamlit as st
from admin import show_admin
from live import show_live
from ranking import show_ranking

st.set_page_config(page_title="GymPoints Live", layout="wide")

# Compatibile con tutte le versioni
params = st.experimental_get_query_params()
admin_mode = params.get("admin", [None])[0] == "1234"  # Cambia la chiave se vuoi

pages = ["Live Gara", "Classifica Generale"]
if admin_mode:
    pages.insert(1, "Amministrazione")

st.sidebar.title("Menu")
page = st.sidebar.radio("Vai a:", pages)

if page == "Live Gara":
    show_live()
elif page == "Amministrazione":
    if not admin_mode:
        st.warning("Accesso non autorizzato.")
    else:
        show_admin()
elif page == "Classifica Generale":
    show_ranking()
