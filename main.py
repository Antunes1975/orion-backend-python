from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Inicialização
load_dotenv()
app = FastAPI()

# Configuração de CORS: Essencial para o Lovable conectar ao seu Backend no Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Modelo para o salvamento de dados
class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]

# --- ROTAS DO MOTOR ORION Ω ---

@app.get("/")
def read_root():
    return {"status": "ORION Motor Ω Online"}

@app.get("/status-base")
def get_status():
    try:
        # Busca simples para testar conexão
        response = supabase.table("sorteios").select("*", count='exact').limit(1).execute()
        return {"message": "Motor conectado ao Supabase", "status": "OK"}
    except Exception as e:
        return {"message": "Erro na conexão", "error": str(e)}

@app.get("/ultimos-concursos")
async def ultimos_concursos():
    try:
        # Busca usando 'Concurso' com C maiúsculo conforme sua tabela
        response = supabase.table("auditoria_motor") \
            .select("Concurso, assertividade, motivos") \
            .order("Concurso", desc=True) \
            .limit(5) \
            .execute()
        return response.data
    except Exception as e:
        # Retorna lista vazia se a tabela de auditoria não existir ainda
        return []

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        # Ajuste: campo Concurso com C maiúsculo para coincidir com seu Supabase
        data = {
            "Concurso": resultado.concurso,
            "numeros": resultado.numeros
        }
        response = supabase.table("sorteios").insert(data).execute()
        return {
            "message": "Sorteio registrado com sucesso no ORION!", 
            "dados": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calcular-media")
async def calcular_media(salarios: list[float]):
    num_descarte = int(len(salarios) * 0.20)
    df_filtrado = sorted(salarios)[num_descarte:]
    media_final = sum(df_filtrado) / len(df_filtrado) if df_filtrado else 0
    
    return {
        "media_final": round(float(media_final), 2),
        "total": len(salarios),
        "descartados": num_descarte
    }
