import streamlit as st
from admin import show_admin
from live import show_live
from ranking import show_ranking

st.set_page_config(page_title="GymPoints Live", layout="wide")

# ✅ Usa la nuova API
params = st.query_params
admin_mode = params.get("admin") == "1234"

pages = ["Live Gara", "Classifica Generale"]
if admin_mode:
    pages.insert(1, "Amministrazione")

st.sidebar.title("Menu")
page = st.sidebar.radio("Vai a:", pages)

if page == "Live Gara":
    show_live()
elif page == "Amministrazione":
    show_admin()
elif page == "Classifica Generale":
    show_ranking()
