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

def formatar_hora(val, data_base):
    if pd.isna(val): return None
    try:
        hora_str = str(val).split()[-1] 
        return f"{data_base}T{hora_str}"
    except:
        return None

def main():
    print("📂 Lendo Excel de Setembro...")
    # Lê a planilha
    df = pd.read_excel("dados setembro.xlsx", sheet_name="Controle de Exames")
    
    # Padroniza os nomes das colunas
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Como a planilha tem os dias nas linhas vazias, precisamos rastrear a data
    # Vamos varrer linha por linha
    enviados = 0
    data_atual = None

    print("🚀 Enviando para o Supabase...")
    
    for _, row in df.iterrows():
        # Verifica se a linha é um "cabeçalho de dia" (ex: "01 Terça")
        valor_col_b = str(row.get("NOME DO PACIENTE", "")).strip()
        if "TERÇA" in valor_col_b.upper() or "QUARTA" in valor_col_b.upper() or "QUINTA" in valor_col_b.upper() or "SEGUNDA" in valor_col_b.upper() or "SEXTA" in valor_col_b.upper():
            # Extrai o dia (ex: "01")
            dia = valor_col_b.split()[0].zfill(2)
            data_atual = f"2026-09-{dia}" # Ano e mês fixos para Setembro
            continue # Pula a linha do cabeçalho

        # Se não tiver tipo de exame, ignora
        tipo_exame = limpar_texto(row.get("TIPO DE EXAME"))
        if not tipo_exame:
            continue

        # Se não achou um dia antes, usa 01/09 como padrão
        if not data_atual:
            data_atual = "2026-09-01"

        registro = {
            "numero_atendimento": limpar_texto(row.get("Nº ATENDIMENTO")),
            "paciente": limpar_texto(row.get("NOME DO PACIENTE")),
            "tipo_exame": tipo_exame,
            "contraste": str(row.get("CONTRASTE", "")).strip().upper() == "SIM",
            "especialidade": limpar_texto(row.get("ESPECIALIDADE")),
            "medico": limpar_texto(row.get("MEDICO")),
            "tecnologo": limpar_texto(row.get("TECNÓLOGO RADIOLOGIA")),
            "enfermagem": limpar_texto(row.get("ENFERMAGEM")),
            "data_exame": data_atual,
            "hora_ficha": formatar_hora(row.get("HORA DA FICHA RETIRADA"), data_atual),
            "inicio_exame": formatar_hora(row.get("INÍCIO DO EXAME"), data_atual),
            "termino_exame": formatar_hora(row.get("TÉRMINO DO EXAME"), data_atual),
            "solicitante": limpar_texto(row.get("SOLICITANTE")),
            "sedacao_confirmada": str(row.get("SEDAÇÃO ACOMPANHAMENTO", "")).strip().upper() == "SIM",
            "justificativa": limpar_texto(row.get("JUSTIFICATIVA DA DEMORA")),
            "observacoes": limpar_texto(row.get("OBSERVAÇÕES")),
        }
        
        try:
            supabase.table("exames").insert(registro).execute()
            enviados += 1
        except Exception as e:
            print(f"   ✗ Erro: {e}")

    print(f"\n✅ Concluído! {enviados} exames de Setembro enviados.")

if __name__ == "__main__":
    main()