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
        # Busca sem filtros de ordem complexos para não quebrar no nome da coluna
        # O .select("*") traz tudo o que existir, sem forçar nomes de colunas
        sug_data = supabase.table("sugestoes").select("*").execute().data
        sort_data = supabase.table("sorteios").select("*").execute().data
        
        return {"concursos": sug_data, "debug_sorteios": sort_data[:5]}
    except Exception as e:
        return {"erro": "O banco retornou: " + str(e)}

@app.post("/salvar-manual")
def salvar(payload: dict):
    try:
        # O payload deve ser: {"tabela": "sorteios", "dados": {...}}
        # Isso permite salvar sem que o Python precise saber o nome das colunas previamente
        tabela = payload.get("tabela", "sorteios")
        supabase.table(tabela).insert(payload["dados"]).execute()
        return {"status": "sucesso"}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
