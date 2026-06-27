import os
import random
import requests
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from supabase import create_client

# Inicialização
load_dotenv()
app = FastAPI()

# --- MIDDLEWARE ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def handle_options_and_trailing_slash(request: Request, call_next):
    if request.method == "OPTIONS": return Response(status_code=200)
    if request.url.path.endswith("/") and request.url.path != "/": request.scope["path"] = request.url.path.rstrip("/")
    return await call_next(request)

# Conexão Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# --- MODELOS E CACHE ---
class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

CONFIG_CACHE = {"motor_padrao": "RACE", "janela_estatistica": 50, "simulacoes_monte_carlo": 25000, "threshold_css": 62.3}

# --- LÓGICA DO MOTOR ---
def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & {2, 3, 5, 7, 11, 13, 17, 19, 23})
    pares = len(set(jogo) & {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24})
    moldura = len(set(jogo) & {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25})
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def gerar_cenario_ancora():
    todas = list(range(1, 26))
    for _ in range(1000): # Tenta gerar com filtros até 1000 vezes
        jogo = sorted(random.sample(todas, 15))
        if validar_zona_ouro(jogo): return jogo
    return sorted(random.sample(todas, 15)) # Fallback

# --- ROTAS ---
@app.get("/")
def read_root(): return {"status": "ORION Ω Engine Online"}

@app.get("/status-base")
def get_status_base():
    resp = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(1).execute()
    ult = resp.data[0]['Concurso'] if resp.data else 0
    return {"ultimo_concurso_supabase": ult, "proximo_alvo_motor": 3720}

@app.get("/configuracoes")
def get_configuracoes(): return CONFIG_CACHE

@app.get("/historico-assertividade")
def obter_historico_assertividade():
    resp = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute()
    return {"concursos": resp.data if resp.data else []}

@app.post("/gerar-jogos")
async def gerar_jogos():
    concurso_alvo = 3720
    jogos = [{"nome": "JOGO Ω A", "numeros": gerar_cenario_ancora()}, {"nome": "JOGO Ω B", "numeros": gerar_cenario_ancora()}]
    try: supabase.table("sugestoes").insert({"concurso": concurso_alvo, "jogos": jogos}).execute()
    except: pass
    return {"motor": "ORION Ω", "jogos": jogos}

@app.post("/auto-sincronizar")
def auto_sincronizar_caixa():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    resp = requests.get(url, verify=False, timeout=10)
    dados = resp.json()
    concurso = dados["numero"]
    dezenas = [int(d) for d in dados["listaDezenas"]]
    data = {"Concurso": concurso}
    for i in range(15): data[f"Bola{i+1}"] = dezenas[i]
    supabase.table("sorteios").insert(data).execute()
    return {"status": "Sucesso", "concurso": concurso}
