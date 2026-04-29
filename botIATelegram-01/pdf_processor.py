import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Carrega as variáveis de ambiente (chave do Gemini)
load_dotenv()

def processar_pdf():
    pdf_path = "Edital do Vestibular UEG 2026-1_vf2.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Erro: O arquivo '{pdf_path}' não foi encontrado.")
        return

    print("1. Carregando o PDF...")
    loader = PyPDFLoader(pdf_path)
    documentos = loader.load()
    
    print(f"   Páginas carregadas: {len(documentos)}")

    print("2. Dividindo o texto em pedaços (chunks)...")
    # Divide o texto em blocos de 1000 caracteres, com uma sobreposição de 200 caracteres
    # A sobreposição ajuda a não perder o contexto entre um pedaço e outro
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documentos)
    
    print(f"   Total de pedaços gerados: {len(chunks)}")

    print("3. Criando os embeddings e salvando no banco de dados vetorial...")
    # Usa o modelo de embeddings do Google Gemini
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    # Cria o banco de dados Chroma localmente na pasta 'chroma_db'
    diretorio_db = "./chroma_db"
    
    # Processa em lotes pequenos com retry para respeitar o rate limit do plano gratuito
    import time
    tamanho_lote = 5
    total_lotes = (len(chunks) + tamanho_lote - 1) // tamanho_lote
    max_tentativas = 5
    
    def processar_com_retry(funcao, *args, **kwargs):
        """Tenta executar a função, esperando mais tempo a cada falha."""
        for tentativa in range(1, max_tentativas + 1):
            try:
                return funcao(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    espera = 15 * tentativa  # 15s, 30s, 45s, 60s, 75s
                    print(f"      Rate limit atingido. Esperando {espera}s (tentativa {tentativa}/{max_tentativas})...")
                    time.sleep(espera)
                else:
                    raise e
        raise Exception("Número máximo de tentativas excedido.")
    
    # Cria o banco com o primeiro lote
    primeiro_lote = chunks[:tamanho_lote]
    print(f"   Processando lote 1/{total_lotes} ({len(primeiro_lote)} pedaços)...")
    db = processar_com_retry(
        Chroma.from_documents,
        documents=primeiro_lote,
        embedding=embeddings,
        persist_directory=diretorio_db
    )
    
    # Adiciona os lotes restantes
    for i in range(tamanho_lote, len(chunks), tamanho_lote):
        lote_num = (i // tamanho_lote) + 1
        lote = chunks[i:i + tamanho_lote]
        print(f"   Processando lote {lote_num}/{total_lotes} ({len(lote)} pedaços)...")
        time.sleep(10)  # Pausa de 10s entre lotes
        processar_com_retry(db.add_documents, lote)
    
    print(f"\nConcluído! Banco de dados vetorial salvo em '{diretorio_db}'.")
    print(f"Total de {len(chunks)} pedaços processados com sucesso!")

if __name__ == "__main__":
    processar_pdf()
