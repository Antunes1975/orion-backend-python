import os
import random
import requests
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from supabase import create_client

load_dotenv()
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Conexão Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# --- MOTOR DE INTELIGÊNCIA ---
DEZENAS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
DEZENAS_PARES = {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24}
DEZENAS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & DEZENAS_PRIMOS)
    pares = len(set(jogo) & DEZENAS_PARES)
    moldura = len(set(jogo) & DEZENAS_MOLDURA)
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def gerar_cenario_ancora():
    todas = list(range(1, 26))
    for _ in range(1000):
        jogo = sorted(random.sample(todas, 15))
        if validar_zona_ouro(jogo): return jogo
    return sorted(random.sample(todas, 15))

# --- ROTAS ---
@app.get("/")
def read_root(): return {"status": "ORION Ω Engine Online"}

@app.get("/status-base")
def status():
    resp = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(1).execute()
    ult = resp.data[0]['Concurso'] if resp.data else 0
    return {"ultimo": ult, "alvo": 3720}

@app.get("/historico-assertividade")
def obter_historico():
    try:
        resp = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute()
        return {"concursos": resp.data if resp.data else []}
    except: return {"concursos": []}

@app.post("/gerar-jogos")
def gerar_jogos():
    jogos = [{"nome": "JOGO Ω A", "numeros": gerar_cenario_ancora()}, {"nome": "JOGO Ω B", "numeros": gerar_cenario_ancora()}]
    return {"motor": "ORION Ω", "jogos": jogos}

@app.post("/auto-sincronizar")
def sync():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    resp = requests.get(url, verify=False, timeout=10)
    dados = resp.json()
    concurso = dados["numero"]
    dezenas = [int(d) for d in dados["listaDezenas"]]
    data = {"Concurso": concurso}
    for i in range(15): data[f"Bola{i+1}"] = dezenas[i]
    supabase.table("sorteios").insert(data).execute()
    return {"status": "Sucesso", "concurso": concurso}
@app.get("/configuracoes")
def get_config(): return {"motor_padrao": "RACE", "janela_estatistica": 50}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
