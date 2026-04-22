# Chuvisco - Bot Meteorológico Brasileiro ⛅

Bot do Telegram desenvolvido como trabalho acadêmico para consulta de clima atual, previsão e guias climáticos mensais do Brasil.

## 🤖 Acesso ao Bot
Para testar o bot, procure por **@ChuviscoClimaBot** no Telegram ou acesse: [t.me/ChuviscoClimaBot](https://t.me/ChuviscoClimaBot)

## 🛠️ Tecnologias e Ferramentas
- **Linguagem:** Python 3.x
- **Bibliotecas:** `python-telegram-bot` (Interface), `requests` (API), `Flask` (Health Check), `pypdf` (Leitura de dados), `python-dotenv`.
- **API de Clima:** OpenWeatherMap.
- **Desenvolvimento:** Criado em parceria com a IA **Antigravity**.
- **Hospedagem:** Render (PaaS) com suporte a Web Service.

## 📋 Evolução do Projeto
1. **Planejamento:** Definição dos comandos principais (`/tempo`, `/previsao`, `/mes`).
2. **Modularização:** Separação da lógica em arquivos distintos (`bot.py`, `clima.py`, `leitor_pdf.py`) para facilitar manutenção.
3. **Limpeza:** Remoção de scripts auxiliares e arquivos temporários antes do deploy.
4. **Deploy:** Configuração de servidor web paralelo para manter o bot ativo no Render (Free Tier).

## 🚀 Como Executar
1. Instale as dependências: `pip install -r requirements.txt`
2. Configure o arquivo `.env` com seu `TELEGRAM_TOKEN` e `OPENWEATHER_KEY`.
3. Rode o bot: `python bot.py`

---
*Projeto desenvolvido para fins educacionais.*
