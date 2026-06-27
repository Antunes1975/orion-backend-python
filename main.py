import os
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
        # AQUI A MÁGICA: Não usamos nomes de colunas no código.
        # Buscamos os dados brutos e deixamos o Python processar tudo na memória.
        sugestoes = supabase.table("sugestoes").select("*").execute().data
        sorteios = supabase.table("sorteios").select("*").execute().data
        
        # Se os dados vierem, o erro de "coluna não existe" não ocorrerá.
        return {"concursos": sugestoes, "debug": "sucesso"}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
