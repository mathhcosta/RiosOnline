# -*- coding: UTF-8 -*-

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import plotly.graph_objects as go
import os
import requests
from folium.plugins import LocateControl
from streamlit_js_eval import get_geolocation


# ================= CONFIG =================
st.set_page_config(
    page_title="Sala de Situação – Rios Online",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #e9f3ff;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<h2 style='text-align:center'>Sala de Situação – Rios Online</h2>",
    unsafe_allow_html=True
)
st.markdown(
    """
    <div style='text-align:center; margin-bottom:6px;'>
        <span style='font-size:13px; color:#555; letter-spacing:1px;'>
            Instituições colaboradoras
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

col0, col1, col2, col3, col4 = st.columns([2,3,3,3,2])

with col2:
    st.image("logos/logo.png", width=260)

st.markdown("---")



# ================= FUNÇÃO LEITURA =================
def carregar_dados_estacao(pasta, codigo):
    arquivo = os.path.join(pasta, f"{codigo}.xlsx")

    if not os.path.exists(arquivo):
        st.error(f"Arquivo não encontrado: {arquivo}")
        st.stop()

    return pd.read_excel(arquivo)

# ================= COLUNAS =================
COL_ANO = 0
COL_HMAX = 7
COL_COIN = 8
COL_HMIN = 9
COL_COFI = 10
COL_VAR = 11
COL_DIA_MES = 12
COL_MIN = 13
COL_MAX = 14
COL_MEDIA = 15
COL_ATUAL = 16
COL_MES = 18
COL_FREQ_MAX = 20
COL_FREQ_MIN = 19

# ================= GRÁFICOS =================
def grafico_hidrograma(df):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.iloc[:, COL_DIA_MES],
        y=df.iloc[:, COL_MAX],
        line=dict(width=0),
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=df.iloc[:, COL_DIA_MES],
        y=df.iloc[:, COL_MIN],
        fill="tonexty",
        fillcolor="rgba(0,100,255,0.15)",
        line=dict(width=0),
        name="Faixa Histórica"
    ))

    fig.add_trace(go.Scatter(
        x=df.iloc[:, COL_DIA_MES],
        y=df.iloc[:, COL_MEDIA],
        name="Média Histórica",
        line=dict(color="green")
    ))

    fig.add_trace(go.Scatter(
        x=df.iloc[:, COL_DIA_MES],
        y=df.iloc[:, COL_ATUAL],
        name="Cota Atual",
        line=dict(color="red", width=2)
    ))

    fig.update_layout(
        xaxis=dict(
            dtick="M1",
            tickformat="%b",
            automargin=True
        ),
        height=300
    )

    return fig

def obter_pais_por_gps(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "RiosOnlineApp"}

        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        return data["address"].get("country", "").lower()

    except:
        return None


def grafico_variabilidade(df):
    df_var = pd.DataFrame({
        "Ano": pd.to_numeric(df.iloc[:, COL_ANO], errors="coerce"),
        "Variabilidade": pd.to_numeric(
            df.iloc[:, COL_VAR].astype(str).str.replace(",", "."),
            errors="coerce"
        )
    }).dropna()

    df_10 = df_var.sort_values("Ano", ascending=False).head(10).sort_values("Ano")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_10["Ano"],
        y=df_10["Variabilidade"],
        mode="lines+markers"
    ))

    fig.update_layout(height=300)
    return fig


def obter_cota_atual(df):
    df_atual = df[df.iloc[:, COL_ATUAL].notna()]

    if df_atual.empty:
        return None, None

    linha = df_atual.iloc[-1]
    return linha.iloc[COL_ATUAL], linha.iloc[COL_DIA_MES]


def grafico_frequencia(df, coluna, titulo):
    df_freq = pd.DataFrame({
        "Mes": df.iloc[:, COL_MES],
        "Freq": df.iloc[:, coluna]
    })

    df_freq["Freq"] = pd.to_numeric(
        df_freq["Freq"].astype(str).str.replace(",", "."),
        errors="coerce"
    )

    df_freq = (
        df_freq.dropna()
        .groupby("Mes", as_index=False)["Freq"]
        .sum()
    )

    df_freq = df_freq[df_freq["Freq"] > 0]

    fig = go.Figure()

    if not df_freq.empty:
        fig.add_trace(go.Pie(
            labels=df_freq["Mes"],
            values=df_freq["Freq"],
            hole=0.35,
            textinfo="percent"
        ))

    fig.update_layout(
        title=titulo,
        height=350,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig


def tabela_eventos(df, col_data, col_cota, asc=True):
    tab = pd.DataFrame({
        "Ano": df.iloc[:, COL_ANO],
        "Data": df.iloc[:, col_data],
        "Cota": df.iloc[:, col_cota]
    }).dropna()

    return (
        tab.sort_values("Cota", ascending=asc)
        .head(5)
        .reset_index(drop=True)
    )


# ================= ESTAÇÕES =================
def carregar_estacoes(pasta_estacoes):
    arquivo = os.path.join(pasta_estacoes, "estacoes.xlsx")

    if not os.path.exists(arquivo):
        st.error(f"Arquivo de estações não encontrado: {arquivo}")
        st.stop()

    df = pd.read_excel(arquivo)

    estacoes = []
    for _, row in df.iterrows():
        lat = float(str(row["lat"]).replace(",", "."))
        lon = float(str(row["lon"]).replace(",", "."))

        estacoes.append({
            "codigo": str(row["codigo"]),
            "nome": row["nome"],
            "coords": [lat, lon],
            "tipo": row.get("tipo", ""),
            "pais": [
                p.strip().lower()
                for p in str(row.get("pais", "")).split(",")
            ]

        })


    return estacoes


# ================= INPUT =================
pasta_dados = "C:/RiosOnline/dados_excel"
pasta_estacoes = "C:/RiosOnline/estacoes"

if "codigo_estacao" not in st.session_state:
    st.session_state["codigo_estacao"] = None

estacoes = carregar_estacoes(pasta_estacoes)

# ================= MAPAS =================

col_mapa1, col_mapa2 = st.columns(2)

# ================= GPS AUTOMÁTICO =================
if "gps_carregado" not in st.session_state:
    st.session_state["gps_carregado"] = False
    st.session_state["pais_gps"] = None
    st.session_state["lat_user"] = None
    st.session_state["lon_user"] = None

# Captura automática ao abrir
if not st.session_state["gps_carregado"]:
    loc = get_geolocation()

    if loc:
        lat = loc["coords"]["latitude"]
        lon = loc["coords"]["longitude"]

        st.session_state["lat_user"] = lat
        st.session_state["lon_user"] = lon
        st.session_state["pais_gps"] = obter_pais_por_gps(lat, lon)
        st.session_state["gps_carregado"] = True

# ================= LISTA DE PAÍSES =================
lista_paises = sorted(
    set(p for e in estacoes for p in e["pais"] if p)
)

# Define país padrão automaticamente
pais_gps = st.session_state["pais_gps"]

if pais_gps and pais_gps in lista_paises:
    indice_padrao = lista_paises.index(pais_gps)
else:
    indice_padrao = 0

# ================= SELECTBOX =================
pais_selecionado = st.selectbox(
    "🌎 Filtrar estações por país",
    lista_paises,
    index=indice_padrao
)

# ================= MAPA ESTAÇÕES =================
with col_mapa1:
    st.markdown("### Estações fluviais")

    # Centro padrão
    lat_centro = -3.5
    lon_centro = -60
    zoom_mapa = 5

    # Se GPS capturado
    if st.session_state["lat_user"]:
        lat_centro = st.session_state["lat_user"]
        lon_centro = st.session_state["lon_user"]
        zoom_mapa = 8

    mapa = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=zoom_mapa,
        tiles="OpenStreetMap",
        control_scale=True
    )

    LocateControl(auto_start=False).add_to(mapa)

    for e in estacoes:
        if pais_selecionado.lower() not in e["pais"]:
            continue

        folium.Marker(
            location=e["coords"],
            tooltip=e["nome"],
            icon=folium.Icon(color="blue", icon="map-pin", prefix="fa")
        ).add_to(mapa)

    retorno = st_folium(mapa, height=400, use_container_width=True)

# ================= MAPA WINDY =================
with col_mapa2:
    st.markdown("### 🌬️ Condições atmosféricas (Windy)")

    components.html(
        """
        <iframe width="100%" height="500"
        src="https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=°C&metricWind=km/h&zoom=5&overlay=wind&product=ecmwf&level=surface&lat=-7.014&lon=-59.985&detailLat=-3.075&detailLon=-59.985&detail=true&message=true"
        frameborder="0"></iframe>
        """,
        height=400
    )


# ================= SELEÇÃO ESTAÇÃO =================
if retorno and retorno.get("last_object_clicked_tooltip"):
    nome = retorno["last_object_clicked_tooltip"]
    for e in estacoes:
        if e["nome"] == nome:
            st.session_state["codigo_estacao"] = e["codigo"]

codigo = st.session_state.get("codigo_estacao")

if codigo is None:
    st.info("Clique em uma estação no mapa para visualizar a Sala de Situação.")
    st.stop()

df = carregar_dados_estacao(pasta_dados, codigo)

# ================= SALA DE SITUAÇÃO =================
c1, c2 = st.columns(2)
with c1:

    if st.session_state.get("codigo_estacao"):

        # Buscar estação selecionada
        estacao = next(
            (e for e in estacoes
             if e["codigo"] == st.session_state["codigo_estacao"]),
            None
        )

        if estacao:

            # Obter última cota
            cota_atual, data_cota = obter_cota_atual(df)

            # Formatar data
            data_txt = ""
            if data_cota is not None and pd.notna(data_cota):
                data_txt = f" em {pd.to_datetime(data_cota).strftime('%d/%m/%Y')}"

            # Caso exista valor válido
            if cota_atual is not None and pd.notna(cota_atual):

                st.markdown(
                    f"""
                    <div style="
                        background-color:#e6f2ff;
                        padding:12px 16px;
                        border-radius:10px;
                        margin-bottom:12px;
                        font-size:18px;
                        font-weight:600;
                    ">
                        📍 <b>{estacao['nome']}</b> — {estacao['codigo']}  
                        <br>
                        🌊 Cota do último registro: <b>{int(cota_atual)} cm</b>{data_txt}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:
                st.warning("Não há dados recentes disponíveis para esta estação.")

        else:
            st.error("Estação não encontrada.")

    else:
        st.info("Selecione uma estação no mapa para visualizar a Sala de Situação.")


c1, c2 = st.columns(2)
with c1:
    st.markdown(" Hidrograma de evolução anual")
    st.plotly_chart(grafico_hidrograma(df), use_container_width=True)

with c2:
    st.markdown(" Variabilidade decadal Hmax-Hmin")
    st.plotly_chart(grafico_variabilidade(df), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown(" Últimos 5 eventos de cheia")
    st.dataframe(tabela_eventos(df, COL_HMAX, COL_COIN, asc=False), use_container_width=True)

with c4:
    st.markdown(" Últimos 5 eventos de seca")
    st.dataframe(tabela_eventos(df, COL_HMIN, COL_COFI, asc=True), use_container_width=True)

c5, c6 = st.columns(2)
with c5:
    st.plotly_chart(grafico_frequencia(df, COL_FREQ_MAX, "Frequência de Máximas"), use_container_width=True)

with c6:
    st.plotly_chart(grafico_frequencia(df, COL_FREQ_MIN, "Frequência de Mínimas"), use_container_width=True)
