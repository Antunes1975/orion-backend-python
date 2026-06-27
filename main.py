import os
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

app = FastAPI()
# CORS aberto para qualquer origem
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.get("/status")
def status():
    return {"status": "online"}

@app.get("/historico-assertividade")
def historico():
    try:
        # Busca direta, sem ordenações complexas para evitar erro de coluna
        res = supabase.table("sugestoes").select("*").limit(5).execute()
        return {"concursos": res.data}
    except Exception as e:
        return {"erro": str(e)}

@app.post("/salvar-manual")
def salvar_manual(payload: dict):
    # payload deve ser: {"concurso": 3720, "bolas": [1, 2, ...]}
    try:
        data = {"Concurso": payload["concurso"], **{f"Bola{i+1}": payload["bolas"][i] for i in range(15)}}
        supabase.table("sorteios").insert(data).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
