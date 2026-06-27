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
        # CORREÇÃO: Usando "concurso_id" (o nome real que apareceu na imagem)
        res = supabase.table("sugestoes").select("*").order("concurso_id", desc=True).limit(10).execute()
        sugestoes = res.data
        
        # Busca sorteios usando "Concurso" (que confirmamos antes)
        sort_res = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(15).execute()
        sorteios = sort_res.data
        
        for sug in sugestoes:
            sorteio = next((s for s in sorteios if s['Concurso'] == sug['concurso_id']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}")])
                # A sua coluna 'jogos' já é JSON, então usamos diretamente
                sug['acertos'] = len(set(sug['jogos'][0]['numeros']) & oficiais)
            else:
                sug['acertos'] = 0
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": "Falha na estrutura da tabela: " + str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
