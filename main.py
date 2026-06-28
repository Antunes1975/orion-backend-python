import os
import random
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from supabase import create_client

# Inicialização
load_dotenv()
app = FastAPI()

# --- MIDDLEWARE DE SEGURANÇA E CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Conexão Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# --- MODELOS ---
class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

class ConfigMotor(BaseModel):
    motor_padrao: str = "RACE"
    janela_estatistica: int = 50
    simulacoes_monte_carlo: int = 25000
    threshold_css: float = 60.0

# --- CONSTANTES ---
DEZENAS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
DEZENAS_PARES = {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24}
DEZENAS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

CONFIG_CACHE = {"motor_padrao": "RACE", "janela_estatistica": 50, "simulacoes_monte_carlo": 25000, "threshold_css": 62.3}

# --- FUNÇÕES ---
def verificar_status_concurso():
    # Aspas duplas forçam o Postgres a aceitar "Concurso" maiúsculo
    response = supabase.table("sorteios").select('"Concurso"').order('"Concurso"', desc=True).limit(1).execute()
    ultimo_registrado = response.data[0].get('Concurso') if response.data else 0
    return ultimo_registrado < 3720, ultimo_registrado

def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & DEZENAS_PRIMOS)
    pares = len(set(jogo) & DEZENAS_PARES)
    moldura = len(set(jogo) & DEZENAS_MOLDURA)
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def calcular_pesos_dezenas():
    response = supabase.table("sorteios").select("*").order('"Concurso"', desc=True).limit(CONFIG_CACHE["janela_estatistica"]).execute()
    contagem = {i: 0 for i in range(1, 26)}
    for sorteio in response.data:
        for i in range(1, 16):
            dezena = sorteio.get(f"Bola{i}")
            if dezena: contagem[dezena] += 1
    total = len(response.data) if response.data else 1
    return [contagem[i] / total for i in range(1, 26)]

def gerar_cenario_ancora():
    pesos = calcular_pesos_dezenas()
    todas = list(range(1, 26))
    while True:
        jogo = sorted(list(set(random.choices(todas, weights=pesos, k=15))))
        if len(jogo) == 15 and validar_zona_ouro(jogo): return jogo

# --- ROTAS ---
@app.get("/")
def read_root(): return {"status": "ORION Ω Engine Online", "versao": "2.4.0-Estável"}

@app.get("/status-base")
def get_status_base():
    liberado, ultimo = verificar_status_concurso()
    return {"ultimo_concurso_supabase": ultimo, "status_geracao": "LIBERADO" if liberado else "BLOQUEADO"}

@app.get("/historico-assertividade")
def historico():
    sug = supabase.table("sugestoes").select("*").execute().data
    sort = supabase.table("sorteios").select("*").execute().data
    return {"concursos": sug, "sorteios": sort}

@app.post("/gerar-jogos")
async def gerar_jogos():
    concurso_alvo = 3720
    check = supabase.table("sugestoes").select("*").eq("concurso", concurso_alvo).execute()
    if len(check.data) > 0: return {"motor": "Recuperado", "jogos": check.data[0]['jogos']}
    
    jogo_1 = gerar_cenario_ancora()
    jogo_2 = gerar_cenario_ancora()
    jogos = [{"nome": "JOGO A", "numeros": jogo_1}, {"nome": "JOGO B", "numeros": jogo_2}]
    
    supabase.table("sugestoes").insert({"concurso": concurso_alvo, "jogos": jogos}).execute()
    return {"motor": "ORION Ω", "jogos": jogos}

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    # Aspas duplas resolvem o erro 42703
    data = {'"Concurso"': resultado.concurso}
    for i in range(15): data[f'"Bola{i+1}"'] = resultado.numeros[i]
    supabase.table("sorteios").insert(data).execute()
    return {"status": "Registrado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
