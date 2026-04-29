import os
import time
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Carrega as variáveis de ambiente
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configuração do RAG ---

def criar_cadeia_rag():
    """Cria a cadeia RAG: carrega o banco vetorial + conecta com o Gemini."""
    
    # Mesmo modelo de embeddings usado no processamento do PDF
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    # Carrega o banco de dados vetorial já criado
    db = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings
    )
    
    # Configura o retriever (buscador) - busca os 5 trechos mais relevantes
    retriever = db.as_retriever(search_kwargs={"k": 5})
    
    # Modelo de linguagem do Groq para gerar as respostas
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3  # Baixa temperatura para respostas mais precisas e factuais
    )
    
    # Prompt personalizado para o agente
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "Você é um assistente especializado no Edital do Vestibular UEG 2026/1. "
         "Responda APENAS com base nas informações do edital fornecidas no contexto abaixo. "
         "Se a pergunta não puder ser respondida com as informações disponíveis, diga: "
         "'Desculpe, não encontrei essa informação no edital.' "
         "Seja claro, objetivo e organize bem a resposta. "
         "Use emojis quando apropriado para deixar a resposta mais amigável.\n\n"
         "Contexto do Edital:\n{context}"),
        ("human", "{input}")
    ])
    
    # Cria a cadeia de combinação de documentos
    cadeia_documentos = create_stuff_documents_chain(llm, prompt)
    
    # Cria a cadeia RAG completa (retrieval + resposta)
    cadeia = create_retrieval_chain(retriever, cadeia_documentos)
    
    return cadeia

# Inicializa a cadeia RAG ao iniciar o bot
print("Carregando o banco de dados vetorial e configurando o RAG...")
cadeia_rag = criar_cadeia_rag()
print("RAG pronto!")

# --- Handlers do Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Mensagem de boas-vindas."""
    mensagem = (
        "🎓 *Olá! Eu sou o Assistente do Vestibular UEG 2026/1!*\n\n"
        "Eu conheço todo o edital do vestibular e posso te ajudar com informações sobre:\n\n"
        "📅 Datas importantes\n"
        "📝 Processo de inscrição\n"
        "📚 Conteúdos e provas\n"
        "💰 Taxas e isenções\n"
        "🏫 Cursos disponíveis\n"
        "📋 Documentação necessária\n\n"
        "É só me mandar sua pergunta! 😊"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda - Mostra como usar o bot."""
    mensagem = (
        "📖 *Como me usar:*\n\n"
        "Basta digitar sua pergunta normalmente!\n\n"
        "*Exemplos de perguntas:*\n"
        "• Quando são as provas?\n"
        "• Quais cursos estão disponíveis?\n"
        "• Como faço a inscrição?\n"
        "• Qual o valor da taxa de inscrição?\n"
        "• Quais documentos preciso para a matrícula?\n\n"
        "💡 Quanto mais específica a pergunta, melhor a resposta!"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def responder_pergunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a pergunta do usuário e responde usando o RAG."""
    pergunta = update.message.text
    
    # Mostra que o bot está "digitando"
    await update.message.chat.send_action("typing")
    
    # Tenta até 3 vezes com espera progressiva (para lidar com rate limit)
    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            # Faz a consulta no RAG
            resultado = cadeia_rag.invoke({"input": pergunta})
            resposta = resultado["answer"]
            
            # Limita o tamanho da resposta para o Telegram (máx 4096 chars)
            if len(resposta) > 4000:
                resposta = resposta[:4000] + "\n\n✂️ _Resposta cortada por ser muito longa._"
            
            await update.message.reply_text(resposta, parse_mode="Markdown")
            return  # Sucesso, sai da função
            
        except Exception as e:
            erro = str(e)
            print(f"Erro (tentativa {tentativa}/{max_tentativas}): {erro}")
            
            if "429" in erro or "RESOURCE_EXHAUSTED" in erro:
                if tentativa < max_tentativas:
                    espera = 20 * tentativa
                    print(f"Rate limit - esperando {espera}s antes de tentar novamente...")
                    await update.message.chat.send_action("typing")
                    time.sleep(espera)
                    continue
            
            # Se não é rate limit ou já esgotou tentativas
            await update.message.reply_text(
                "⚠️ Desculpe, ocorreu um erro ao processar sua pergunta. "
                "Tente novamente em alguns segundos!"
            )
            return

# --- Servidor Web Dummy para o Render ---

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot do Telegram está rodando!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- Inicialização do Bot ---

def main():
    """Função principal que inicia o bot."""
    print("Iniciando o servidor web para o Render...")
    # Roda o servidor Flask em uma thread separada para não bloquear o bot
    threading.Thread(target=run_web_server, daemon=True).start()
    
    print("Iniciando o bot do Telegram...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Registra os handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pergunta))
    
    print("Bot está rodando! Envie mensagens pelo Telegram.")
    print("Pressione Ctrl+C para parar.")
    app.run_polling()

if __name__ == "__main__":
    main()
