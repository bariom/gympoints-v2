import streamlit as st
from admin import show_admin
from live import show_live
from ranking import show_ranking

st.set_page_config(page_title="GymPoints Live", layout="wide")

st.sidebar.title("Menu")
page = st.sidebar.radio("Vai a:", ["Live Gara", "Amministrazione", "Classifica Generale"])

if page == "Live Gara":
    show_live()
elif page == "Amministrazione":
    show_admin()
elif page == "Classifica Generale":
    show_ranking()