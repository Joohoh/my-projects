from pypdf import PdfReader
from pathlib import Path

# O PDF foi gerado sequencialmente de Janeiro a Dezembro (páginas 0 a 11)
MESES_PAGINAS = {
    "janeiro": 0,
    "fevereiro": 1,
    "marco": 2,
    "março": 2,
    "abril": 3,
    "maio": 4,
    "junho": 5,
    "julho": 6,
    "agosto": 7,
    "setembro": 8,
    "outubro": 9,
    "novembro": 10,
    "dezembro": 11
}

def consultar_mes_no_pdf(mes_buscado: str, caminho_pdf: str = "guia_clima_brasil.pdf") -> str | None:
    """
    Lê uma página específica do PDF baseado no mês solicitado
    e retorna o texto extraído para enviar ao usuário.
    """
    mes = mes_buscado.lower().strip()
    if mes not in MESES_PAGINAS:
        return None
    
    caminho = Path(caminho_pdf)
    if not caminho.exists():
        return None
        
    try:
        reader = PdfReader(caminho)
        num_pag = MESES_PAGINAS[mes]
        page = reader.pages[num_pag]
        text = page.extract_text()
        
        # Vamos dar uma limpada no texto para tirar as informações de formatação
        # do fpdf2 (cabeçalhos e rodapés) e deixar a mensagem agradável pro Telegram
        linhas = text.split("\n")
        texto_limpo = []
        
        for linha in linhas:
            l = linha.strip()
            # Ignorar cabeçalho e rodapé do PDF original
            if "GUIA DO CLIMA NO BRASIL" in l or "ChuviscoClimaBot" in l:
                continue
            if not l:
                continue
                
            # Identificação do título do mês e estação  (ex: Janeiro - Verão)
            if " - " in l and any(m in l.lower() for m in MESES_PAGINAS.keys()):
                l = f"📅 *{l.upper()}*\n" + "━"*25
            
            # Identificação de regiões para adicionar emojis
            elif l.startswith("Norte") or l.startswith("Nordeste") or \
                 l.startswith("Centro-Oeste") or l.startswith("Sudeste") or \
                 l.startswith("Sul"):
                l = f"\n🌍 *{l}*"
                
            # Formatação de campos técnicos
            elif "Temp. min:" in l or "Temp. max:" in l:
                l = "\n" + l.replace("Temp. min:", "🌡️ *Mín:*").replace("Temp. max:", " *Máx:*").replace("Umidade:", "💧 *Umidade:*")
            elif "Precipitacao:" in l:
                l = f"🌧️ *Chuva:* {l.replace('Precipitacao: ', '')}\n"
                
            # Se a linha limpa anterior não terminar com uma pontuação finalizadora, junta com a atual ajeitando o espaço que o PDF retirou
            if texto_limpo and not texto_limpo[-1].endswith((".", ":", "*", "━", "\n")):
                texto_limpo[-1] += " " + l
            else:
                texto_limpo.append(l)
            
        return "\n".join(texto_limpo)
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return None
