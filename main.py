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
def obter_historico():
    try:
        # AQUI ESTÁ A CORREÇÃO: Usamos "Concurso" (com C maiúsculo)
        sugestoes = supabase.table("sugestoes").select("*").order("Concurso", desc=True).limit(10).execute().data
        sorteios = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(15).execute().data
        
        for sug in sugestoes:
            sorteio = next((s for s in sorteios if s['Concurso'] == sug['Concurso']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16)])
                sug['acertos'] = len(set(sug['jogos'][0]['numeros']) & oficiais) # Exemplo simplificado
            else:
                sug['acertos'] = 0
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": str(e)}

@app.post("/auto-sincronizar")
def sync():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    resp = requests.get(url, verify=False, timeout=10).json()
    concurso = int(resp["numero"])
    dezenas = [int(d) for d in resp["listaDezenas"]]
    
    # Verifica se já existe
    check = supabase.table("sorteios").select("*").eq("Concurso", concurso).execute()
    if not check.data:
        data = {"Concurso": concurso, **{f"Bola{i+1}": dezenas[i] for i in range(15)}}
        supabase.table("sorteios").insert(data).execute()
        return {"status": "Inserido"}
    return {"status": "Já existe"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
