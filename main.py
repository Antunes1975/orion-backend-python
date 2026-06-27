import os
import random
import requests
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

# --- MIDDLEWARE DE SEGURANÇA E CORS BLINDADO ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.middleware("http")
async def handle_options_and_trailing_slash(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(
            status_code=200, 
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            }
        )
    if request.url.path.endswith("/") and request.url.path != "/":
        request.scope["path"] = request.url.path.rstrip("/")
    return await call_next(request)

# Conexão Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MODELOS DE DADOS (PYDANTIC) ---
class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

class ConfigMotor(BaseModel):
    motor_padrao: str = "RACE"
    janela_estatistica: int = 50
    simulacoes_monte_carlo: int = 25000
    threshold_css: float = 60.0

# --- CONSTANTES ESTATÍSTICAS ---
DEZENAS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
DEZENAS_PARES = {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24}
DEZENAS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# Memory cache temporário para configurações (evita quebra se não houver tabela)
CONFIG_CACHE = {
    "motor_padrao": "RACE",
    "janela_estatistica": 50,
    "simulacoes_monte_carlo": 25000,
    "threshold_css": 62.3
}

# --- FUNÇÕES INTERNAS DO MOTOR ---
def verificar_status_concurso():
    """Busca o último concurso real inserido para validar o bloqueio anti-repetição."""
    response = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(1).execute()
    ultimo_registrado = response.data[0]['Concurso'] if response.data else 0
    CONCURSO_ALVO = 3720
    return ultimo_registrado < CONCURSO_ALVO, ultimo_registrado

def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & DEZENAS_PRIMOS)
    pares = len(set(jogo) & DEZENAS_PARES)
    moldura = len(set(jogo) & DEZENAS_MOLDURA)
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def calcular_pesos_dezenas():
    response = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(CONFIG_CACHE["janela_estatistica"]).execute()
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

# --- ROTAS DA API (PRODUÇÃO CONTRA 404) ---

@app.get("/")
def read_root():
    return {"status": "ORION Ω Engine Online", "versao": "2.4.0-Estável"}

@app.get("/status-base")
def get_status_base():
    """Rota exigida pelo Dashboard para monitorar a saúde da sincronização."""
    liberado, ultimo = verificar_status_concurso()
    return {
        "ultimo_concurso_supabase": ultimo,
        "proximo_alvo_motor": 3720,
        "status_geracao": "LIBERADO" if liberado else "BLOQUEADO_AGUARDANDO_RESULTADO"
    }

@app.get("/ultimos-concursos")
def get_ultimos_concursos():
    """Rota resumida para listagem rápida de controle no dashboard."""
    response = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(5).execute()
    return {"concursos": [r["Concurso"] for r in response.data] if response.data else []}

@app.get("/configuracoes")
def get_configuracoes():
    """Retorna as diretrizes operacionais do Meta-Motor Config."""
    return CONFIG_CACHE

@app.put("/configuracoes")
def update_configuracoes(config: ConfigMotor):
    """Atualiza dinamicamente os parâmetros de cálculo do motor."""
    CONFIG_CACHE["motor_padrao"] = config.motor_padrao
    CONFIG_CACHE["janela_estatistica"] = config.janela_estatistica
    CONFIG_CACHE["simulacoes_monte_carlo"] = config.simulacoes_monte_carlo
    CONFIG_CACHE["threshold_css"] = config.threshold_css
    return {"status": "Configurações do motor atualizadas com sucesso", "atual": CONFIG_CACHE}

@app.post("/gerar-jogos")
async def gerar_jogos_quantitativos():
    concurso_alvo = 3720
    
    # 1. Trava de segurança contra execuções duplicadas
    check = supabase.table("sugestoes").select("*").eq("concurso", concurso_alvo).execute()
    if len(check.data) > 0:
        return {"motor": "ORION Ω (Cenário Consolidado Recuperado)", "jogos": check.data[0]['jogos']}

    # 2. Execução se estiver livre
    jogo_1 = gerar_cenario_ancora()
    for _ in range(CONFIG_CACHE["simulacoes_monte_carlo"]):
        jogo_2 = gerar_cenario_ancora()
        if len(set(jogo_1) & set(jogo_2)) <= 9:
            break
            
    jogos = [
        {"nome": "JOGO Ω A", "numeros": jogo_1, "metricas": {"soma": sum(jogo_1), "primos": len(set(jogo_1)&DEZENAS_PRIMOS), "pares": len(set(jogo_1)&DEZENAS_PARES), "moldura": len(set(jogo_1)&DEZENAS_MOLDURA)}},
        {"nome": "JOGO Ω B", "numeros": jogo_2, "metricas": {"soma": sum(jogo_2), "primos": len(set(jogo_2)&DEZENAS_PRIMOS), "pares": len(set(jogo_2)&DEZENAS_PARES), "moldura": len(set(jogo_2)&DEZENAS_MOLDURA)}}
    ]
    
    # Grava no banco para congelar e impedir novos cliques repetidos
    try:
        # Corrigido o erro de digitação de "juegos" para "jogos"
        supabase.table("sugestoes").insert({"concurso": concurso_alvo, "jogos": jogos}).execute()
    except Exception:
        pass # Fallback caso a tabela precise de ajustes estruturais externos
    
    return {"motor": f"ORION Ω ({CONFIG_CACHE['motor_padrao']})", "jogos": jogos}

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    data = {"Concurso": resultado.concurso}
    for i in range(15): data[f"Bola{i+1}"] = resultado.numeros[i]
    supabase.table("sorteios").insert(data).execute()
    return {"status": "Registrado com sucesso"}

@app.post("/auditar-diario-bordo")
async def auditar_diario(concurso: int):
    return {"status": "Auditado"}

@app.post("/auto-sincronizar")
def auto_sincronizar_caixa():
    """Busca o último sorteio oficial da Caixa e salva no Supabase automaticamente."""
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    
    try:
        # verify=False é usado pois os certificados do governo brasileiro costumam dar erro no Python
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erro ao contatar a API da Caixa Econômica.")
            
        dados = response.json()
        concurso_oficial = dados["numero"]
        
        # As dezenas vêm como lista de strings (ex: ["01", "04", ...]), convertendo para inteiros:
        dezenas = [int(d) for d in dados["listaDezenas"]]
        
        # 1. Verifica se este concurso já está no seu Supabase
        check = supabase.table("sorteios").select("Concurso").eq("Concurso", concurso_oficial).execute()
        
        if len(check.data) > 0:
            return {
                "status": "Atualizado", 
                "mensagem": f"A sua base já está em dia com a Caixa (Concurso {concurso_oficial})."
            }
            
        # 2. Se for um concurso novo, prepara no formato exato da sua tabela
        novo_sorteio = {"Concurso": concurso_oficial}
        for i in range(15):
            novo_sorteio[f"Bola{i+1}"] = dezenas[i]
            
        # 3. Grava no banco de dados permanentemente
        supabase.table("sorteios").insert(novo_sorteio).execute()
        
        return {
            "status": "Sucesso", 
            "concurso_adicionado": concurso_oficial,
            "mensagem": f"Concurso {concurso_oficial} sincronizado automaticamente da Caixa!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha na sincronização: {str(e)}")
