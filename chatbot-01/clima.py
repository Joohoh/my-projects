import os
import requests
import datetime


def _obter_geolocalizacoes(cidade: str, chave: str, limit: int = 5) -> list:
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={cidade}&limit={limit}&appid={chave}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.json():
            return r.json()
    except:
        pass
    return []


def _chamar_api(cidade: str, chave: str) -> dict | None:
    """Faz a chamada HTTP para a API usando Geocoding e checagem de ambiguidade."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    parametros = {
        "appid": chave,
        "units": "metric",   
        "lang": "pt_br"      
    }
    
    geo_list = _obter_geolocalizacoes(cidade, chave)
    
    # Checagem de ambiguidade se o usuario nao especificou estado com virgula explícita
    # Usa-se a contagem de vírgulas porque a automação já injetou ",BR" na string
    if len(geo_list) > 1 and ("," not in cidade or (cidade.count(",") == 1 and cidade.endswith("BR"))):
        estados = list(dict.fromkeys([g.get("state") for g in geo_list if g.get("state") and g.get("country") == "BR"]))
        if len(estados) > 1:
            return {"ambiguo": True, "estados": estados}

    geo = geo_list[0] if geo_list else None
    
    if geo and geo.get("lat") and geo.get("lon"):
        parametros["lat"] = geo["lat"]
        parametros["lon"] = geo["lon"]
    else:
        parametros["q"] = cidade
        
    try:
        resposta = requests.get(url, params=parametros, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            estado = geo["state"] if geo else ""
            nome_pais = f"{estado}, {dados['sys']['country']}" if estado else dados["sys"]["country"]
            
            # Força o nome da cidade obtido pelo geocode para não exibir nomes de distritos climáticos vizinhos
            nome_cidade = geo["name"] if (geo and geo.get("name")) else dados["name"]
            
            return {
                "cidade": nome_cidade,
                "pais": nome_pais,
                "codigo_pais": dados["sys"]["country"],
                "temperatura": dados["main"]["temp"],
                "sensacao": dados["main"]["feels_like"],
                "umidade": dados["main"]["humidity"],
                "vento": dados["wind"]["speed"],
                "descricao": dados["weather"][0]["description"]
            }
    except requests.RequestException:
        pass
    return None


def buscar_clima(cidade: str) -> dict | None:
    chave = os.getenv("OPENWEATHER_KEY")

    if ",br" not in cidade.lower():
        cidade_br = f"{cidade},BR"
    else:
        cidade_br = cidade
        
    resultado = _chamar_api(cidade_br, chave)
    if resultado:
        return resultado

    resultado = _chamar_api(cidade, chave)
    if resultado:
        return resultado

    return None

def _chamar_api_previsao(cidade: str, chave: str) -> dict | None:
    """Faz a chamada HTTP para a API de FORECAST checando ambiguidade."""
    url = "https://api.openweathermap.org/data/2.5/forecast"
    parametros = {
        "appid": chave,
        "units": "metric",
        "lang": "pt_br"
    }
    
    geo_list = _obter_geolocalizacoes(cidade, chave)
    
    if len(geo_list) > 1 and ("," not in cidade or (cidade.count(",") == 1 and cidade.endswith("BR"))):
        estados = list(dict.fromkeys([g.get("state") for g in geo_list if g.get("state") and g.get("country") == "BR"]))
        if len(estados) > 1:
            return {"ambiguo": True, "estados": estados}

    geo = geo_list[0] if geo_list else None
    
    if geo and geo.get("lat") and geo.get("lon"):
        parametros["lat"] = geo["lat"]
        parametros["lon"] = geo["lon"]
    else:
        parametros["q"] = cidade
        
    try:
        resposta = requests.get(url, params=parametros, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            
            estado = geo["state"] if geo else ""
            if not estado and not (geo and geo.get("lat")):
                geo_fallback_list = _obter_geolocalizacoes(dados["city"]["name"], chave)
                if geo_fallback_list:
                    estado = geo_fallback_list[0].get("state", "")
                 
            nome_pais = f"{estado}, {dados['city']['country']}" if estado else dados["city"]["country"]
            nome_cidade = geo["name"] if (geo and geo.get("name")) else dados["city"]["name"]
            
            amanha = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            previsoes_amanha = [item for item in dados["list"] if item["dt_txt"].startswith(amanha)]
            if not previsoes_amanha:
                return None
                
            temp_min = min(item["main"]["temp_min"] for item in previsoes_amanha)
            temp_max = max(item["main"]["temp_max"] for item in previsoes_amanha)
            
            indice_meio = len(previsoes_amanha) // 2
            meio = previsoes_amanha[indice_meio]
            
            return {
                 "cidade": nome_cidade,
                 "pais": nome_pais,
                 "codigo_pais": dados["city"]["country"],
                 "temp_min": temp_min,
                 "temp_max": temp_max,
                 "umidade": meio["main"]["humidity"],
                 "vento": meio["wind"]["speed"],
                 "descricao": meio["weather"][0]["description"],
                 "data": amanha
            }
    except requests.RequestException:
        pass
    return None

def buscar_previsao(cidade: str) -> dict | None:
    chave = os.getenv("OPENWEATHER_KEY")

    if ",br" not in cidade.lower():
        cidade_br = f"{cidade},BR"
    else:
        cidade_br = cidade

    dados = _chamar_api_previsao(cidade_br, chave)
    if not dados:
        dados = _chamar_api_previsao(cidade, chave)
    
    return dados
