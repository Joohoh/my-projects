# 🎓 Agente IA do Vestibular (PDF RAG)

Este é um bot para Telegram construído em Python que funciona como um Assistente Virtual especializado no **Edital do Vestibular**. Ele lê o edital em PDF, entende o contexto e responde às dúvidas dos candidatos de forma inteligente e rápida.

## 🛠️ Como Funciona? (Arquitetura)

O projeto utiliza a técnica de **RAG (Retrieval-Augmented Generation)**. Ao invés de tentarmos "ensinar" (fazer fine-tuning) um modelo inteiro sobre o edital, nós damos a ele o dom da leitura e pesquisa em tempo real:

1. **Processamento do PDF (`pdf_processor.py`)**: Lemos o PDF de 56 páginas, quebramos ele em pequenos pedaços de texto (chunks) e usamos a API do Google (Gemini) para converter esses textos em coordenadas matemáticas (Embeddings).
2. **Banco de Dados Vetorial**: Esses embeddings são salvos localmente num banco de dados chamado **ChromaDB**.
3. **O Bot (`bot.py`)**: Quando o usuário faz uma pergunta no Telegram, o bot converte a pergunta em embedding, busca no ChromaDB quais são os 5 trechos do edital mais parecidos com a pergunta, e envia esses trechos para uma Inteligência Artificial (Groq/Llama 3) formular a resposta final.

---

## 🚧 Desafios e Decisões de Design (O "Porquê" das coisas)

Durante o desenvolvimento deste projeto, testamos diferentes abordagens e nos deparamos com alguns desafios da vida real de implantação em nuvem gratuita:

### 1. Por que Groq e não o Gemini (Google) para as respostas?
Inicialmente, o projeto inteiro foi desenhado para rodar no Google Gemini. Porém, o plano gratuito do Google possui limites rigorosos de Requisições por Dia (RPD). Apenas processando o edital e fazendo alguns testes, nós estouramos a cota (*Erro 429 RESOURCE_EXHAUSTED*). 

**A solução:** Trocamos a Inteligência artificial que "fala" com o usuário para a nuvem da **Groq**, rodando o modelo open-source `Llama-3.3-70b-versatile`. O Groq tem limites gratuitos incrivelmente generosos e é extremamente rápido. Mantivemos o Google apenas para a criação dos *embeddings* da pergunta (o que consome quase nada da cota).

### 2. Por que subir a pasta `chroma_db` pro GitHub?
Normalmente, pastas de banco de dados ficam no `.gitignore`. Porém, nós a subimos para o repositório. Por que?
Se o servidor da nuvem (Render) rodasse o arquivo `pdf_processor.py` para ler as 56 páginas toda vez que fosse reiniciado, ele gastaria nossa cota diária do Google em segundos, além de demorar vários minutos para o bot ficar online. Processando no nosso computador e subindo o banco já pronto, o bot na nuvem liga instantaneamente e de forma gratuita!

### 3. O servidor web "Falso" (Flask) e o Anti-Sleep
O bot roda em modo *Polling* no Telegram. No entanto, o plano grátis do **Render** não permite *Background Workers*, apenas *Web Services* (que exigem uma porta HTTP aberta). 
**A solução:** Criamos um mini-servidor web invisível usando `Flask` rodando numa *Thread* separada no `bot.py`. E para impedir que o Render desligue a máquina após 15 minutos de inatividade, configuramos um serviço como o [cron-job.org](https://cron-job.org) para "cutucar" o site a cada 10 minutos, garantindo que o bot do Telegram fique 100% online, 24 horas por dia.

---

## 💻 Como Rodar Localmente no seu PC

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Crie um arquivo `.env` na raiz do projeto e insira as suas chaves:
   ```env
   TELEGRAM_TOKEN=sua_chave_do_telegram
   GOOGLE_API_KEY=sua_chave_do_google_aistudio
   GROQ_API_KEY=sua_chave_do_groq
   ```
3. (Opcional) Caso o edital mude, rode o processador de PDF para recriar o banco:
   ```bash
   python pdf_processor.py
   ```
4. Ligue o bot:
   ```bash
   python bot.py
   ```

## ☁️ Como Fazer o Deploy (Render)

1. Suba este código (incluindo a pasta `chroma_db`) para um repositório no GitHub. **NUNCA suba o arquivo `.env`**.
2. Crie um **Web Service** no Render integrado ao seu GitHub.
3. Nas configurações:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. Na aba **Environment Variables**, crie as variáveis `TELEGRAM_TOKEN`, `GOOGLE_API_KEY` e `GROQ_API_KEY` com suas respectivas chaves.
5. Crie um job no [cron-job.org](https://cron-job.org) apontando para a URL que o Render gerar, rodando a cada 14 minutos.
