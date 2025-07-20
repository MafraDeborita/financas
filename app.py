import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
from datetime import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURAR CREDENCIAIS E CONECTAR AO GOOGLE SHEETS ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(credentials)

# === ABRIR PLANILHA ===
spreadsheet = client.open("financas")  # Substitua pelo nome real
sheet = spreadsheet.sheet1



st.set_page_config(page_title="Controle Financeiro", layout="centered")

# === Carregar meses disponíveis e permitir seleção ===
dados_path = "dados"
os.makedirs(dados_path, exist_ok=True)

arquivos_disponiveis = sorted(
    [f for f in os.listdir(dados_path) if f.endswith(".xlsx")],
    reverse=True
)

if arquivos_disponiveis:
    nome_meses = [arquivo.replace(".xlsx", "") for arquivo in arquivos_disponiveis]
    mes_selecionado = st.selectbox("📅 Selecione o mês para visualizar os dados:", nome_meses)
    arquivo_escolhido = os.path.join(dados_path, f"{mes_selecionado}.xlsx")
else:
    st.info("Nenhum mês salvo ainda. Adicione dados para começar.")
    mes_selecionado = datetime.today().strftime('%Y-%m')
    arquivo_escolhido = os.path.join(dados_path, f"{mes_selecionado}.xlsx")

# === Carregar dados do mês selecionado ===
try:
    recebimentos_carregados = pd.read_excel(arquivo_escolhido, sheet_name="Recebimentos")
    gastos_carregados = pd.read_excel(arquivo_escolhido, sheet_name="Gastos")

    if "Status" not in gastos_carregados.columns:
        gastos_carregados["Status"] = "Pendente"

except:
    recebimentos_carregados = pd.DataFrame(columns=["Data", "Descrição", "Valor"])
    gastos_carregados = pd.DataFrame(columns=["Data", "Descrição", "Valor", "Status"])

# === Atualizar session_state quando o mês for alterado ===
if st.session_state.get("mes_atual") != mes_selecionado:
    st.session_state.recebimentos = recebimentos_carregados.copy()
    st.session_state.gastos = gastos_carregados.copy()
    st.session_state.mes_atual = mes_selecionado

st.title("Controle Simples de Finanças Pessoais")

# Valor inicial
valor_inicial = st.number_input("💰 Valor atual na poupança (R$)", min_value=0.0, step=10.0)

# === RECEBIMENTOS ===
st.markdown("---")
st.header("📥 Rendimentos Mensais (Contas a Receber)")

with st.form("form_recebimentos"):
    descricao_r = st.text_input("Descrição do rendimento")
    valor_r = st.number_input("Valor recebido (R$)", step=10.0, format="%.2f")
    data_r = st.date_input("Data do recebimento")
    submitted_r = st.form_submit_button("Adicionar rendimento")

if submitted_r:
    nova_linha = {"Data": data_r, "Descrição": descricao_r, "Valor": valor_r}
    st.session_state.recebimentos = pd.concat(
        [st.session_state.recebimentos, pd.DataFrame([nova_linha])], ignore_index=True
    )

# === Mostrar tabela de recebimentos ===
st.subheader("📋 Lista de Rendimentos")
for i, row in st.session_state.recebimentos.iterrows():
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    data_formatada = pd.to_datetime(row["Data"]).strftime("%d/%m/%Y")
    col1.write(f"{row['Descrição']} ({data_formatada})")
    col2.write(f"R$ {row['Valor']:.2f}")
    if col4.button("❌", key=f"del_r_{i}"):
        st.session_state.recebimentos = st.session_state.recebimentos.drop(i).reset_index(drop=True)
        st.rerun()

# === GASTOS ===
st.markdown("---")
st.header("📤 Gastos Mensais (Contas a Pagar)")

with st.form("form_gastos"):
    descricao_g = st.text_input("Descrição do gasto")
    valor_g = st.number_input("Valor gasto (R$)", step=10.0, format="%.2f")
    data_g = st.date_input("Data do gasto")
    submitted_g = st.form_submit_button("Adicionar gasto")

if submitted_g:
    nova_linha = {"Data": data_g, "Descrição": descricao_g, "Valor": valor_g, "Status": "Pendente"}
    st.session_state.gastos = pd.concat(
        [st.session_state.gastos, pd.DataFrame([nova_linha])], ignore_index=True
    )

# === Mostrar tabela de gastos pendentes ===
st.subheader("📋 Gastos Pendentes")
gastos_pendentes = st.session_state.gastos[st.session_state.gastos["Status"] == "Pendente"]

for i, row in gastos_pendentes.iterrows():
    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
    data_formatada = pd.to_datetime(row["Data"]).strftime("%d/%m/%Y")
    col1.write(f"{row['Descrição']} ({data_formatada})")
    col2.write(f"R$ {row['Valor']:.2f}")
    if col3.button("✅ Pagar", key=f"pagar_{i}"):
        st.session_state.gastos.at[i, "Status"] = "Pago"
        st.rerun()
    if col4.button("❌", key=f"del_g_{i}"):
        st.session_state.gastos = st.session_state.gastos.drop(i).reset_index(drop=True)
        st.rerun()

# === Mostrar tabela de gastos pagos ===
st.subheader("📌 Gastos Pagos")
gastos_pagos = st.session_state.gastos[st.session_state.gastos["Status"] == "Pago"]

for i, row in gastos_pagos.iterrows():
    col1, col2 = st.columns([4, 2])
    data_formatada = pd.to_datetime(row["Data"]).strftime("%d/%m/%Y")
    col1.write(f"{row['Descrição']} ({data_formatada})")
    col2.write(f"R$ {row['Valor']:.2f}")

# === Cálculos ===
total_recebido = st.session_state.recebimentos["Valor"].sum()
total_gasto = st.session_state.gastos[st.session_state.gastos["Status"] == "Pendente"]["Valor"].sum()
saldo = valor_inicial + total_recebido - total_gasto

st.markdown("---")
st.subheader("💡 Resumo Financeiro")
col1, col2, col3 = st.columns(3)
col1.metric("Contas a Receber", f"R$ {total_recebido:.2f}")
col2.metric("Contas a Pagar", f"R$ {total_gasto:.2f}")
col3.metric("Saldo Restante", f"R$ {saldo:.2f}")

# === Gráfico de barras ===
st.markdown("---")
st.subheader("📊 Gráfico de Resumo Financeiro")

df_barras = pd.DataFrame({
    "Categoria": ["Contas a Receber", "Contas a Pagar", "Saldo Restante"],
    "Valor": [total_recebido, total_gasto, saldo]
})

cores_personalizadas = {
    "Contas a Receber": "#2ecc71",
    "Contas a Pagar": "#e74c3c",
    "Saldo Restante": "#3498db"
}

fig_barras = px.bar(
    df_barras,
    x="Categoria",
    y="Valor",
    color="Categoria",
    text=df_barras["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")),
    color_discrete_map=cores_personalizadas
)

fig_barras.update_layout(title="Resumo Geral", yaxis_title="Valor (R$)", xaxis_title="", showlegend=False)
fig_barras.update_yaxes(tickprefix="R$ ")
st.plotly_chart(fig_barras, use_container_width=True)

# === Gráfico de pizza ===
st.subheader("🥧 Gráfico de Distribuição Geral")

pie_df = pd.DataFrame({
    "Categoria": ["Contas a Pagar", "Contas a Receber", "Saldo Restante"],
    "Valor": [total_gasto, total_recebido, saldo]
})

fig_pie = px.pie(
    pie_df,
    names="Categoria",
    values="Valor",
    title="Distribuição Financeira",
    color="Categoria",
    color_discrete_map=cores_personalizadas
)

fig_pie.update_traces(textinfo="label+percent+value", hovertemplate="%{label}: R$ %{value:,.2f}")
st.plotly_chart(fig_pie, use_container_width=True)

# === Exportação ===
st.markdown("---")
st.subheader("📥 Exportar dados para Excel (.xlsx)")

def exportar_excel(df, nome_arquivo, nome_aba):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=nome_aba)
    output.seek(0)
    return output

st.download_button("⬇ Baixar Recebimentos (.xlsx)",
    data=exportar_excel(st.session_state.recebimentos, "recebimentos.xlsx", "Recebimentos"),
    file_name="recebimentos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.download_button("⬇ Baixar Gastos (.xlsx)",
    data=exportar_excel(st.session_state.gastos, "gastos.xlsx", "Gastos"),
    file_name="gastos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Exportar Tudo
output_tudo = io.BytesIO()
with pd.ExcelWriter(output_tudo, engine='xlsxwriter') as writer:
    st.session_state.recebimentos.to_excel(writer, index=False, sheet_name='Recebimentos')
    st.session_state.gastos.to_excel(writer, index=False, sheet_name='Gastos')
output_tudo.seek(0)
st.download_button("⬇ Baixar Tudo em um arquivo (.xlsx)",
    data=output_tudo,
    file_name="controle_financeiro_completo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# === Salvamento automático ===
try:
    with pd.ExcelWriter(arquivo_escolhido, engine="xlsxwriter") as writer:
        st.session_state.recebimentos.to_excel(writer, index=False, sheet_name="Recebimentos")
        st.session_state.gastos.to_excel(writer, index=False, sheet_name="Gastos")
except PermissionError:
    st.warning("⚠️ Feche o arquivo do Excel para que os dados possam ser salvos corretamente.")
