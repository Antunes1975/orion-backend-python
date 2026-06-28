import os
import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Inicializa Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

@app.get("/status-base")
def get_status_base():
    try:
        # Tenta buscar usando 'concurso' minúsculo (padrão mais comum)
        response = supabase.table("sorteios").select("concurso").order("concurso", desc=True).limit(1).execute()
        ultimo = response.data[0].get('concurso') if response.data else 0
        return {"ultimo_concurso": ultimo, "status": "OK"}
    except Exception as e:
        # Se falhar, tenta com 'Concurso' (maiusculo) para diagnóstico
        try:
            response = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(1).execute()
            ultimo = response.data[0].get('Concurso') if response.data else 0
            return {"ultimo_concurso": ultimo, "status": "OK (via maiusculo)"}
        except Exception as e2:
            return {"status": "Erro", "detalhe": str(e2)}

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        # Tenta salvar conforme a estrutura detectada
        data = {"concurso": resultado.concurso}
        for i in range(15): data[f"bola{i+1}"] = resultado.numeros[i]
        supabase.table("sorteios").insert(data).execute()
        return {"status": "Registrado"}
    except Exception as e:
        # Fallback para nomes com maiúsculas
        try:
            data = {"Concurso": resultado.concurso}
            for i in range(15): data[f"Bola{i+1}"] = resultado.numeros[i]
            supabase.table("sorteios").insert(data).execute()
            return {"status": "Registrado (via maiusculo)"}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))
