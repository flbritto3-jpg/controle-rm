import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px

# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
#     "supabase",
#     "plotly",
#     "openpyxl",
# ]
# ///

st.set_page_config(page_title="Controle RM", layout="wide")

URL = st.secrets["URL_SUPABASE"]
KEY = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL, KEY)

@st.cache_data(ttl=10)
def carregar():
    resp = supabase.table("exames").select("*").order("id").execute()
    df = pd.DataFrame(resp.data)
    if df.empty: return df

    for col in ["hora_ficha", "inicio_exame", "termino_exame"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    
    if "data_exame" in df.columns:
        df["data_exame"] = pd.to_datetime(df["data_exame"], errors="coerce").dt.date

    df["Tempo Total (min)"] = (df["termino_exame"] - df["hora_ficha"]).dt.total_seconds() / 60
    df["Tempo de Exame (min)"] = (df["termino_exame"] - df["inicio_exame"]).dt.total_seconds() / 60

    def turno(h):
        if pd.isna(h): return None
        if 6 <= h.hour < 12: return "Manhã"
        if 12 <= h.hour < 19: return "Tarde"
        return "Noite"
    df["Turno"] = df["inicio_exame"].apply(turno)
    return df

df = carregar()

# Criando duas colunas para a logo ficar ao lado do título
col_logo, col_titulo = st.columns([1, 8])

with col_logo:
    try:
        # Carrega a imagem 'logo.png' que está na pasta
        st.image("logo.png", width=100) 
    except:
        st.write("🧠") # Se não achar a imagem, mostra o emoji

with col_titulo:
    st.title("Controle Diário — Ressonância Magnética")

if df.empty:
    st.warning("Banco vazio. Rode `python importar_excel.py`.")
    st.stop()

# ============ FILTROS ============
with st.sidebar:
    st.header("🔍 Filtros")
    
    if "data_exame" in df.columns and not df["data_exame"].isna().all():
        df["mes_ano"] = pd.to_datetime(df["data_exame"]).dt.strftime('%Y-%m')
        meses = sorted(df["mes_ano"].dropna().unique(), reverse=True)
        mes_escolhido = st.selectbox("Mês de Referência", ["Todos"] + list(meses))
    else:
        mes_escolhido = "Todos"

    tipo = st.multiselect("Tipo de Exame", sorted(df["tipo_exame"].dropna().unique()))
    medico = st.multiselect("Médico", sorted(df["medico"].dropna().unique()))
    contraste = st.radio("Contraste", ["Todos", "Sim", "Não"])
    
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

f = df.copy()
if mes_escolhido != "Todos" and "data_exame" in f.columns:
    f = f[f["mes_ano"] == mes_escolhido]
    
if tipo: f = f[f["tipo_exame"].isin(tipo)]
if medico: f = f[f["medico"].isin(medico)]
if contraste == "Sim": f = f[f["contraste"] == True]
if contraste == "Não": f = f[f["contraste"] == False]

# ============ ABAS ============
aba1, aba2, aba3 = st.tabs(["📊 Indicadores", "📋 Exames", "➕ Novo Exame"])

# ---------- ABA 1: INDICADORES ----------
with aba1:
    st.subheader(f"Resumo: {mes_escolhido if mes_escolhido != 'Todos' else 'Geral'}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", len(f))
    c2.metric("Com Contraste", int(f["contraste"].sum()))
    c3.metric("Sem Contraste", int((~f["contraste"]).sum()))
    c4.metric("Médicos", f["medico"].nunique())
    c5.metric("Solicitantes", f["solicitante"].nunique())

    st.divider()

    tempos = f["Tempo de Exame (min)"].dropna()
    tempos = tempos[tempos > 0]
    if len(tempos) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("⏱ Tempo Médio", f"{tempos.mean():.1f} min")
        c2.metric("⚡ Mais Rápido", f"{tempos.min():.1f} min")
        c3.metric("🐢 Mais Lento", f"{tempos.max():.1f} min")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Exames por Tipo")
        vc = f["tipo_exame"].value_counts().reset_index()
        vc.columns = ["tipo_exame", "Qtd"]
        st.plotly_chart(px.bar(vc, x="Qtd", y="tipo_exame", orientation="h"), use_container_width=True)
    with c2:
        st.subheader("Exames por Turno")
        vc = f["Turno"].value_counts().reset_index()
        vc.columns = ["Turno", "Qtd"]
        if len(vc) > 0:
            st.plotly_chart(px.pie(vc, values="Qtd", names="Turno"), use_container_width=True)
        else:
            st.info("Sem dados.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Médicos / Laudo")
        vc = f["medico"].value_counts().reset_index()
        vc.columns = ["medico", "Qtd"]
        if len(vc) > 0:
            st.plotly_chart(px.bar(vc, x="medico", y="Qtd", text="Qtd"), use_container_width=True)
    with c2:
        st.subheader("Top Solicitantes")
        vc = f["solicitante"].value_counts().head(10).reset_index()
        vc.columns = ["solicitante", "Qtd"]
        if len(vc) > 0:
            st.plotly_chart(px.bar(vc, x="Qtd", y="solicitante", orientation="h", text="Qtd"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Exames por Especialidade")
        if "especialidade" in f.columns:
            vc = f["especialidade"].dropna().value_counts().reset_index()
            vc.columns = ["especialidade", "Qtd"]
            if len(vc) > 0:
                fig = px.pie(vc, values="Qtd", names="especialidade", hole=0.4)
                fig.update_traces(textposition='inside', textinfo='value+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de especialidade.")
    with c2:
        st.subheader("Exames com Sedação")
        if "sedacao_confirmada" in f.columns:
            vc = f["sedacao_confirmada"].value_counts().reset_index()
            vc.columns = ["Sedação", "Qtd"]
            vc["Sedação"] = vc["Sedação"].map({True: "Sim", False: "Não"})
            fig2 = px.pie(vc, values="Qtd", names="Sedação", hole=0.4)
            fig2.update_traces(textposition='inside', textinfo='value+label')
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("⏱ Tempo Médio por Tipo de Exame")
    df_tempo = f.dropna(subset=["Tempo de Exame (min)"])
    if len(df_tempo) > 0:
        tmedio = df_tempo.groupby("tipo_exame")["Tempo de Exame (min)"].mean().reset_index().sort_values("Tempo de Exame (min)", ascending=False)
        st.plotly_chart(px.bar(tmedio, x="tipo_exame", y="Tempo de Exame (min)"), use_container_width=True)

# ---------- ABA 2: EXAMES ----------
with aba2:
    st.subheader("📋 Exames Cadastrados")
    cols_show = ["id", "data_exame", "paciente", "tipo_exame", "contraste",
                 "especialidade", "sedacao_confirmada", "medico", "tecnologo", 
                 "inicio_exame", "termino_exame", "Tempo de Exame (min)", "solicitante"]
    cols_existentes = [c for c in cols_show if c in f.columns]
    st.dataframe(f[cols_existentes], use_container_width=True)

    st.divider()
    st.subheader("✏️ Editar exame pelo ID")
    id_edit = st.number_input("ID do exame", min_value=1, step=1, value=int(f["id"].iloc[0]) if len(f) > 0 else 1)
    row = df[df["id"] == id_edit]
    
    if not row.empty:
        row = row.iloc[0]
        # Formulário com a limpeza automática ativada
        with st.form("editar", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            pac = c1.text_input("Paciente", row["paciente"])
            tip = c2.text_input("Tipo de Exame", row["tipo_exame"])
            med = c3.text_input("Médico", row["medico"] or "")
            esp = c1.text_input("Especialidade", row.get("especialidade") or "")
            sol = c2.text_input("Solicitante", row["solicitante"] or "")
            obs = c3.text_input("Observações", row["observacoes"] or "")

            # Criando as colunas para os botões ficarem lado a lado (Ajuste visual)
            col_btn1, col_btn2, _ = st.columns([2, 2, 4]) 
            
            with col_btn1:
                btn_salvar = st.form_submit_button("💾 Salvar alterações")
                
            with col_btn2:
                btn_excluir = st.form_submit_button("🗑️ Excluir este exame")

            # Ação do botão Salvar
            if btn_salvar:
                supabase.table("exames").update({
                    "paciente": pac, "tipo_exame": tip, "medico": med, 
                    "especialidade": esp, "solicitante": sol, "observacoes": obs,
                }).eq("id", int(id_edit)).execute()
                st.success("✅ Alterado!")
                st.cache_data.clear()
                st.rerun()

            # Ação do botão Excluir (agora ele está no lugar certo e não repete)
            if btn_excluir:
                supabase.table("exames").delete().eq("id", int(id_edit)).execute()
                st.success("Excluído!")
                st.cache_data.clear()
                st.rerun()

# ---------- ABA 3: NOVO EXAME ----------
with aba3:
    st.subheader("➕ Adicionar Novo Exame")
    # Formulário de novo exame com a limpeza automática ativada
    with st.form("novo", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        num = c1.text_input("Nº Atendimento")
        pac = c2.text_input("Paciente *")
        tip = c3.text_input("Tipo de Exame *")
        cont = c1.selectbox("Contraste", ["Não", "Sim"])
        esp = c2.text_input("Especialidade")
        sed = c3.selectbox("Sedação?", ["Não", "Sim"])
        med = c1.text_input("Médico")
        tec = c2.text_input("Tecnólogo")
        enf = c3.text_input("Enfermagem")
        data_ex = c1.date_input("Data do Exame")
        hf = c2.time_input("Hora da Ficha")
        ini = c3.time_input("Início do Exame")
        fim = c1.time_input("Término do Exame")
        sol = c2.text_input("Solicitante")
        obs = c3.text_input("Observações")

        if st.form_submit_button("💾 Cadastrar", type="primary"):
            if not pac or not tip:
                st.error("Preencha Paciente e Tipo de Exame.")
            else:
                supabase.table("exames").insert({
                    "numero_atendimento": num,
                    "paciente": pac,
                    "tipo_exame": tip,
                    "contraste": cont == "Sim",
                    "especialidade": esp,
                    "sedacao_confirmada": sed == "Sim",
                    "medico": med, "tecnologo": tec, "enfermagem": enf,
                    "data_exame": str(data_ex),
                    "hora_ficha": f"{data_ex}T{hf}",
                    "inicio_exame": f"{data_ex}T{ini}",
                    "termino_exame": f"{data_ex}T{fim}",
                    "solicitante": sol,
                    "observacoes": obs,
                }).execute()
                st.success("✅ Exame cadastrado!")
                st.cache_data.clear()
                st.rerun()