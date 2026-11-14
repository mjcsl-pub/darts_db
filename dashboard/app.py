"""Darts training dashboard. Run: streamlit run dashboard/app.py"""
import streamlit as st

import bob27
import catch40
import heatmap
import x01

st.set_page_config(page_title="Darts dashboard", layout="wide")

pages = [
    st.Page(lambda: x01.render(501), title="501", url_path="x01-501", default=True),
    st.Page(heatmap.render_board, title="501 dartboard", url_path="x01-dartboard"),
    st.Page(heatmap.render_scores, title="501 visit scores", url_path="x01-visit-scores"),
    st.Page(bob27.render, title="Bob's 27", url_path="bobs-27"),
    st.Page(catch40.render, title="Catch 40", url_path="catch-40"),
]
st.navigation(pages).run()
