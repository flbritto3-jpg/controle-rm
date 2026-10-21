import pandas as pd
from supabase import create_client

URL = "https://kyhffrkcoenisknzumxt.supabase.co"
KEY = "sb_publishable_JQL2ZBje_HdL6fIg55fbeQ_gvfd-rNP"
supabase = create_client(URL, KEY)

def limpar_texto(valor):
    if pd.isna(valor): return None
    texto = str(valor).strip()
    if texto.lower() in ["nan", "none", ""]: return None
    return texto

def formatar_hora(val):
    if pd.isna(val): return None
    try:
        # Transforma em texto e pega só a hora
        hora_str = str(val).split()[-1] 
        return f"2026-10-13T{hora_str}"
    except:
        return None

def main():
    print("📂 Lendo Excel...")
    df = pd.read_excel("dados.xlsx", sheet_name="Controle de Exames")
    
    # O SEGREDO ESTÁ AQUI: Limpa os nomes das colunas removendo espaços extras e deixando em maiúsculo
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Filtra apenas as linhas válidas
    df = df.dropna(subset=["Nº ATENDIMENTO"]).copy()
    df = df[df["TIPO DE EXAME"].notna() & (df["TIPO DE EXAME"].astype(str).str.strip() != "")]
    print(f"   → {len(df)} exames válidos encontrados")

    print("🧹 Limpando banco antigo...")
    supabase.table("exames").delete().neq("id", 0).execute()

    print("🚀 Enviando para o Supabase...")
    enviados = 0
    
    for _, row in df.iterrows():
        registro = {
            "data_exame": "2026-10-13", # Data fixa provisória (mude aqui quando o Excel tiver a data real)
            "numero_atendimento": limpar_texto(row.get("Nº ATENDIMENTO")),
            "paciente": limpar_texto(row.get("NOME DO PACIENTE")),
            "tipo_exame": limpar_texto(row.get("TIPO DE EXAME")),
            "contraste": str(row.get("CONTRASTE", "")).strip().upper() == "SIM",
            "medico": limpar_texto(row.get("MEDICO")),
            "tecnologo": limpar_texto(row.get("TECNÓLOGO RADIOLOGIA")),
            "enfermagem": limpar_texto(row.get("ENFERMAGEM")),
            "hora_ficha": formatar_hora(row.get("HORA DA FICHA RETIRADA")),
            "inicio_exame": formatar_hora(row.get("INÍCIO DO EXAME")),
            "termino_exame": formatar_hora(row.get("TÉRMINO DO EXAME")),
            "solicitante": limpar_texto(row.get("SOLICITANTE")),
            "sedacao": limpar_texto(row.get("SEDAÇÃO ACOMPANHAMENTO")),
            "justificativa": limpar_texto(row.get("JUSTIFICATIVA DA DEMORA")),
            "observacoes": limpar_texto(row.get("OBSERVAÇÕES")),
           "especialidade": limpar_texto(row.get("ESPECIALIDADE", row.get("Especialidade"))),
            "sedacao_confirmada": str(row.get("SEDAÇÃO ACOMPANHAMENTO", row.get("Sedação Acompanhamento", ""))).strip().upper() == "SIM",
        }
        try:
            supabase.table("exames").insert(registro).execute()
            enviados += 1
        except Exception as e:
            print(f"   ✗ Erro: {e}")

    print(f"\n✅ Concluído! {enviados} exames enviados.")

if __name__ == "__main__":
    main()