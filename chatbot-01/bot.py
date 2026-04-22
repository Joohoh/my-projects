import logging
import os
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from clima import buscar_clima, buscar_previsao
from leitor_pdf import consultar_mes_no_pdf

# ══════════════════════════════════════════════
#  Carrega as chaves secretas do arquivo .env
# ══════════════════════════════════════════════
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ══════════════════════════════════════════════
SIGLAS_ESTADOS = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amapa": "AP", "amazonas": "AM", "bahia": "BA",
    "ceará": "CE", "ceara": "CE", "distrito federal": "DF", "espírito santo": "ES", "espirito santo": "ES",
    "goiás": "GO", "goias": "GO", "maranhão": "MA", "maranhao": "MA", "mato grosso": "MT",
    "mato grosso do sul": "MS", "minas gerais": "MG", "pará": "PA", "para": "PA", "paraíba": "PB", "paraiba": "PB",
    "paraná": "PR", "parana": "PR", "pernambuco": "PE", "piauí": "PI", "piaui": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS",
    "rondônia": "RO", "rondonia": "RO", "roraima": "RR", "santa catarina": "SC",
    "são paulo": "SP", "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO"
}
#  Configura os logs (mensagens de debug)
# ══════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


ESTADOS_E_PAIS_BLOQUEADOS = [
    "brasil", "brazil", "br"
]

def buscar_cidade_invalida(nome: str) -> bool:
    """Verifica se o usuário digitou um país ou estado indesejado"""
    n = nome.lower().strip()
    if n in ESTADOS_E_PAIS_BLOQUEADOS or n.startswith("estado de "):
        return True
    return False

# ══════════════════════════════════════════════
#  COMANDOS DO BOT
# ══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — Mensagem de boas-vindas"""
    await update.message.reply_text(
        "👋 Olá! Eu sou o Chuvisco, o *Bot do Clima Brasileiro*! ⛅\n\n"
        "📋 *Comandos disponíveis:*\n"
        "/tempo <cidade> — Clima atual de uma cidade\n"
        "/previsao <cidade> — Ver previsão de amanhã na cidade\n"
        "/mes <janeiro/fevereiro/...> — Ver o clima do mês no Brasil \n"
        "/estados — Ver a lista de siglas dos estados\n"
        "/info — Avisos e sobre o bot\n\n"
        "Exemplo: `/mes abril` , `/tempo goias` , `/previsao goias`",
        parse_mode="Markdown"
    )


async def tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tempo <cidade> — Retorna o clima atual"""

    # Verifica se o usuário passou o nome da cidade
    if not context.args:
        await update.message.reply_text(
            "❌ Você precisa informar o nome da cidade!\n"
            "Uso correto: `/tempo São Paulo`",
            parse_mode="Markdown"
        )
        return

    cidade = " ".join(context.args)

    if buscar_cidade_invalida(cidade):
        await update.message.reply_text(
            "❌ Por favor, digite o nome de uma **cidade específica**. Eu não busco pelo país todo ou estados inteiros.",
            parse_mode="Markdown"
        )
        return

    # Avisa que está buscando
    await update.message.reply_text(f"🔍 Buscando o clima de *{cidade}*...", parse_mode="Markdown")

    dados = buscar_clima(cidade)

    if dados:
        if dados.get("ambiguo"):
            estados_formatados = []
            for est in dados["estados"]:
                s_est = SIGLAS_ESTADOS.get(est.lower(), "UF")
                estados_formatados.append(f"{est} ({s_est})")
            estados_str = " | ".join(estados_formatados)
            estado_exemplo = dados['estados'][0]
            sigla = SIGLAS_ESTADOS.get(estado_exemplo.lower(), 'UF')
            await update.message.reply_text(
                f"❌ Encontrei **várias localidades** chamadas *'{cidade}'*.\n\n"
                f"*(Aviso: se você buscou por um Estado inteiro, lembre-se que só busco o clima de CIDADES específicas!)*\n\n"
                f"Caso seja uma cidade, encontrei resultados nestes estados: {estados_str}\n\n"
                "Para saber o clima correto, digite o comando novamente colocando a ',' e a sigla do estado ao final do nome.\n"
                f"👇 Exemplo:\n`/tempo {cidade}, {sigla}`\n"
                "*(Dica: use /estados para ver a lista de siglas)*",
                parse_mode="Markdown"
            )
            return

        if dados.get("codigo_pais") != "BR":
            await update.message.reply_text(
                "❌ Infelizmente não possuo dados de locais que não sejam no Brasil."
            )
            return
            
        mensagem = (
            f"🌍 *{dados['cidade']}, {dados['pais']}*\n"
            f"🌡️ *Temperatura:* {dados['temperatura']}°C (Sensação: {dados['sensacao']}°C)\n"
            f"💧 *Umidade:* {dados['umidade']}%\n"
            f"💨 *Vento:* {dados['vento']} m/s\n"
            f"☁️ *Condição:* {dados['descricao'].capitalize()}"
        )
        await update.message.reply_text(mensagem, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ Localidade *'{cidade}'* não encontrada na base de clima.\n"
            "Lembre-se de verificar a escrita correta. Se você buscou um Estado inteiro, tente buscar pelo nome de uma cidade específica!",
            parse_mode="Markdown"
        )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/previsao <cidade> — Retorna a previsão detalhada para o dia seguinte"""

    if not context.args:
        await update.message.reply_text(
            "❌ Você precisa informar o nome da cidade!\n"
            "Uso correto: `/previsao São Paulo`",
            parse_mode="Markdown"
        )
        return

    cidade = " ".join(context.args)

    if buscar_cidade_invalida(cidade):
        await update.message.reply_text(
            "❌ Por favor, digite o nome de uma **cidade específica**. Eu não busco pelo país todo.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"📡 Analisando satélites de previsão para o amanhã em *{cidade}*...", parse_mode="Markdown")

    dados = buscar_previsao(cidade)

    if dados:
        if dados.get("ambiguo"):
            estados_formatados = []
            for est in dados["estados"]:
                s_est = SIGLAS_ESTADOS.get(est.lower(), "UF")
                estados_formatados.append(f"{est} ({s_est})")
            estados_str = " | ".join(estados_formatados)
            estado_exemplo = dados['estados'][0]
            sigla = SIGLAS_ESTADOS.get(estado_exemplo.lower(), 'UF')
            await update.message.reply_text(
                f"❌ Encontrei **várias localidades** chamadas *'{cidade}'*.\n\n"
                f"*(Aviso: se você buscou por um Estado inteiro, lembre-se que só busco o clima de CIDADES específicas!)*\n\n"
                f"Caso seja uma cidade, encontrei resultados nestes estados: {estados_str}\n\n"
                "Para saber a previsão correta, digite o comando novamente colocando a ',' e a sigla do estado ao final do nome.\n"
                f"👇 Exemplo:\n`/previsao {cidade}, {sigla}`\n"
                "*(Dica: use /estados para ver a lista de siglas)*",
                parse_mode="Markdown"
            )
            return

        if dados.get("codigo_pais") != "BR":
            await update.message.reply_text(
                "❌ Infelizmente não possuo dados de locais que não sejam no Brasil."
            )
            return
            
        # Formata a data de YYYY-MM-DD para DD/MM/YYYY
        partes_data = dados['data'].split("-")
        data_amigavel = f"{partes_data[2]}/{partes_data[1]}/{partes_data[0]}"

        mensagem = (
            f"📅 *Previsão para Amanhã ({data_amigavel})*\n"
            f"🌍 *{dados['cidade']}, {dados['pais']}*\n\n"
            f"🌡️ *Máxima:* {dados['temp_max']:.1f}°C\n"
            f"🧊 *Mínima:* {dados['temp_min']:.1f}°C\n"
            f"💧 *Umidade:* {dados['umidade']}%\n"
            f"💨 *Vento:* {dados['vento']} m/s\n"
            f"☁️ *Condição predominante:* {dados['descricao'].capitalize()}"
        )
        await update.message.reply_text(mensagem, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ Não encontrei a previsão para a localidade *'{cidade}'*.\n"
            "Lembre-se de verificar a escrita. Se você tentou buscar um Estado inteiro, tente buscar pelo nome de uma cidade específica!",
            parse_mode="Markdown"
        )

async def mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mes <mes> — Lê dados sobre o mês nos dados do INMET"""

    if not context.args:
        await update.message.reply_text(
            "❌ Você precisa informar o mês!\n"
            "Uso correto: `/mes janeiro`",
            parse_mode="Markdown"
        )
        return

    mes_buscado = context.args[0]
    
    # Simula aviso de 'lendo...'
    await update.message.reply_text(f"📖 Consultando o sistema de clima para o mês de *{mes_buscado}*...", parse_mode="Markdown")

    texto_pdf = consultar_mes_no_pdf(mes_buscado)

    if texto_pdf:
        mensagem = f"📚 *Consultado o INMET:*\n\n{texto_pdf}"
        
        # O Telegram tem limite de tamanho para mensagens (4096 caracteres)
        # O texto de uma página do PDF deve caber tranquilamente.
        await update.message.reply_text(mensagem)
    else:
        await update.message.reply_text(
            f"❌ Não encontrei informações para *'{mes_buscado}'* no INMET.\n"
            "Verifique se o mês foi digitado corretamente (sem acentos).",
            parse_mode="Markdown"
        )


async def estados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/estados — Lista as siglas de todos os estados"""
    lista = (
        "🗺️ *Siglas dos Estados do Brasil:*\n\n"
        "Acre (AC), Alagoas (AL), Amapá (AP), Amazonas (AM), "
        "Bahia (BA), Ceará (CE), Distrito Federal (DF), Espírito Santo (ES), "
        "Goiás (GO), Maranhão (MA), Mato Grosso (MT), Mato Grosso do Sul (MS), "
        "Minas Gerais (MG), Pará (PA), Paraíba (PB), Paraná (PR), "
        "Pernambuco (PE), Piauí (PI), Rio de Janeiro (RJ), Rio Grande do Norte (RN), "
        "Rio Grande do Sul (RS), Rondônia (RO), Roraima (RR), Santa Catarina (SC), "
        "São Paulo (SP), Sergipe (SE), Tocantins (TO)"
    )
    await update.message.reply_text(lista, parse_mode="Markdown")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/info — Informações sobre o bot"""
    await update.message.reply_text(
        "ℹ️ *Informação*\n\n"
        "Este bot é um trabalho acadêmico simples, desenvolvido para fins de aprendizado. "
        "Os dados fornecidos podem não ser 100% precisos pois dependem de serviços de clima gratuitos.\n\n"
        "Criado em conjunto com Antigravity e linguagem de programação Python!",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════
#  SERVIDOR WEB (Para o Render não dormir)
# ══════════════════════════════════════════════

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Chuvisco está online! ⛅", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ══════════════════════════════════════════════
#  INICIALIZAÇÃO DO BOT
# ══════════════════════════════════════════════

def main():
    """Ponto de entrada — inicia o bot."""

    if not TELEGRAM_TOKEN:
        print("❌ ERRO: Token do Telegram não encontrado!")
        print("   Verifique se o arquivo .env existe e contém TELEGRAM_TOKEN=...")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registra os comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tempo", tempo))
    app.add_handler(CommandHandler("previsao", previsao))
    app.add_handler(CommandHandler("mes", mes))
    app.add_handler(CommandHandler("estados", estados))
    app.add_handler(CommandHandler("info", info))

    # Inicia o servidor web em uma thread separada
    web_thread = threading.Thread(target=run_flask)
    web_thread.daemon = True
    web_thread.start()

    print("[BOT] Bot do Clima esta rodando!")
    print("   Pressione CTRL+C para parar.\n")
    app.run_polling()


if __name__ == "__main__":
    main()
