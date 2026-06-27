import os
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.get("/historico-assertividade")
def historico():
    try:
        # Busca brutalmente simples, sem tentar ordenar, para evitar erro de coluna inexistente
        sug_res = supabase.table("sugestoes").select("*").execute()
        sort_res = supabase.table("sorteios").select("*").execute()
        
        return {"concursos": sug_res.data, "sorteios": sort_res.data}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
