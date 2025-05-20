import streamlit as st
from admin import show_admin
from live import show_live

st.set_page_config(page_title="GymPoints Live", layout="wide")

st.sidebar.title("Menu")
page = st.sidebar.radio("Vai a:", ["Live Gara", "Amministrazione"])

if page == "Live Gara":
    show_live()
elif page == "Amministrazione":
    show_admin()