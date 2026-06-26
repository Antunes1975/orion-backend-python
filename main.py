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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.middleware("http")
async def handle_options_and_trailing_slash(request: Request, call_next):
    # Trata pré-flight requests do navegador
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        })
    # Remove barras no final para evitar erros de rota
    if request.url.path.endswith("/") and request.url.path != "/":
        request.scope["path"] = request.url.path.rstrip("/")
    return await call_next(request)

# Conexão Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

# --- CONSTANTES ESTATÍSTICAS ---
DEZENAS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
DEZENAS_PARES = {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24}
DEZENAS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# --- FUNÇÕES DO MOTOR ---

def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & DEZENAS_PRIMOS)
    pares = len(set(jogo) & DEZENAS_PARES)
    moldura = len(set(jogo) & DEZENAS_MOLDURA)
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def calcular_pesos_dezenas():
    response = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(50).execute()
    contagem = {i: 0 for i in range(1, 26)}
    for sorteio in response.data:
        for i in range(1, 16):
            dezena = sorteio.get(f"Bola{i}")
            if dezena: contagem[dezena] += 1
    total = len(response.data) if response.data else 1
    return [contagem[i] / total for i in range(1, 26)]

def gerar_cenario_ancora():
    pesos = calcular_pesos_dezenas()
    todas_dezenas = list(range(1, 26))
    while True:
        jogo = random.choices(todas_dezenas, weights=pesos, k=15)
        jogo = sorted(list(set(jogo)))
        if len(jogo) < 15:
            faltam = 15 - len(jogo)
            extras = [d for d in todas_dezenas if d not in jogo]
            jogo = sorted(jogo + random.sample(extras, faltam))
        if validar_zona_ouro(jogo):
            return jogo

# --- ROTAS DA API ---

@app.get("/")
def read_root():
    return {"status": "ORION Ω Engine Online - Fase 2"}

@app.post("/gerar-jogos")
async def gerar_jogos_quantitativos():
    jogo_1 = gerar_cenario_ancora()
    for _ in range(2000):
        jogo_2 = gerar_cenario_ancora()
        if len(set(jogo_1) & set(jogo_2)) <= 9:
            break
    
    return {
        "motor": "ORION Ω Engine - Fase 2 (Ponderada)",
        "jogos": [
            {"nome": "JOGO Ω A", "numeros": jogo_1, "metricas": {"soma": sum(jogo_1), "primos": len(set(jogo_1)&DEZENAS_PRIMOS), "pares": len(set(jogo_1)&DEZENAS_PARES), "moldura": len(set(jogo_1)&DEZENAS_MOLDURA)}},
            {"nome": "JOGO Ω B", "numeros": jogo_2, "metricas": {"soma": sum(jogo_2), "primos": len(set(jogo_2)&DEZENAS_PRIMOS), "pares": len(set(jogo_2)&DEZENAS_PARES), "moldura": len(set(jogo_2)&DEZENAS_MOLDURA)}}
        ]
    }

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    data = {"Concurso": resultado.concurso}
    for i in range(15): data[f"Bola{i+1}"] = resultado.numeros[i]
    supabase.table("sorteios").insert(data).execute()
    return {"status": "Registrado"}

@app.post("/auditar-diario-bordo")
async def auditar_diario(concurso: int):
    return {"status": "Auditado"}
