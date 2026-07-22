from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Avaliação de Mérito Tecnológico", layout="wide")
st.title("Assistente de Avaliação de Mérito Tecnológico")
st.caption("Iteração I-001 — fundação local, sem IA generativa")

try:
    health = httpx.get(f"{API_BASE_URL}/health", timeout=5).json()
    st.success(f"API disponível — processamento externo: {health['external_processing_enabled']}")
except (httpx.HTTPError, KeyError, ValueError):
    st.error("API indisponível. Verifique o Docker Compose.")
    st.stop()

profiles = httpx.get(f"{API_BASE_URL}/profiles", timeout=5).json()
profile_by_name = {item["name"]: item["id"] for item in profiles}

st.subheader("Nova avaliação")
with st.form("create-evaluation"):
    title = st.text_input("Título da avaliação")
    selected_name = st.selectbox("Perfil", list(profile_by_name))
    submitted = st.form_submit_button("Criar avaliação")

if submitted:
    response = httpx.post(
        f"{API_BASE_URL}/evaluations",
        json={"title": title, "profile_id": profile_by_name[selected_name]},
        timeout=10,
    )
    if response.is_success:
        st.success("Avaliação criada.")
    else:
        st.error(response.text)

st.subheader("Avaliações")
response = httpx.get(f"{API_BASE_URL}/evaluations", timeout=5)
if response.is_success:
    evaluations = response.json()
    if evaluations:
        st.dataframe(evaluations, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma avaliação criada.")
