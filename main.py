from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Inicialização
load_dotenv()
app = FastAPI()

# Configuração de CORS
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

class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]

# --- ROTAS ---

@app.get("/")
def read_root():
    return {"status": "ORION Motor Ω Online"}

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        # Mapeamento dinâmico para as colunas Bola1, Bola2... Bola15
        if len(resultado.numeros) != 15:
            raise HTTPException(status_code=400, detail="O sorteio deve conter exatamente 15 números.")
        
        data = {"Concurso": resultado.concurso}
        for i, valor in enumerate(resultado.numeros, 1):
            data[f"Bola{i}"] = valor
        
        response = supabase.table("sorteios").insert(data).execute()
        return {"message": "Sorteio registrado!", "dados": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/ultimos-concursos")
async def ultimos_concursos():
    try:
        # Ajustado para o nome da coluna "Concurso"
        response = supabase.table("auditoria_motor") \
            .select("Concurso, assertividade, motivos") \
            .order("Concurso", desc=True) \
            .limit(5) \
            .execute()
        return response.data
    except Exception as e:
        return []
