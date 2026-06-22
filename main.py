from fastapi import FastAPI, HTTPException
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Inicialização
load_dotenv()
app = FastAPI()

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
        response = supabase.table("sorteios").select("*", count='exact').limit(1).execute()
        return {"message": "Motor conectado ao Supabase", "status": "OK"}
    except Exception as e:
        return {"message": "Erro na conexão", "error": str(e)}

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        # Insere o dado na tabela 'sorteios' do Supabase
        data = {
            "concurso": resultado.concurso,
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
    # Manteve a lógica de cálculo que você aprovou antes
    num_descarte = int(len(salarios) * 0.20)
    df_filtrado = sorted(salarios)[num_descarte:]
    media_final = sum(df_filtrado) / len(df_filtrado) if df_filtrado else 0
    
    return {
        "media_final": round(float(media_final), 2),
        "total": len(salarios),
        "descartados": num_descarte
    }
