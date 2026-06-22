from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        # Validação simples
        if len(resultado.numeros) != 15:
            raise HTTPException(status_code=400, detail="Envie exatamente 15 números.")
        
        # Mapeamento para as colunas Bola1 a Bola15
        data = {"Concurso": resultado.concurso}
        for i in range(15):
            data[f"Bola{i+1}"] = resultado.numeros[i]
        
        response = supabase.table("sorteios").insert(data).execute()
        return {"message": "Sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status-base")
def get_status():
    return {"status": "OK"}
