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
        # Usando "concurso" minúsculo para ambas as tabelas
        sug_res = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute()
        sort_res = supabase.table("sorteios").select("*").order("concurso", desc=True).limit(15).execute()
        
        sugestoes = sug_res.data
        sorteios = sort_res.data
        
        for sug in sugestoes:
            # Cruzamento usando "concurso" em ambos
            sorteio = next((s for s in sorteios if s['concurso'] == sug['concurso']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}")])
                if 'jogos' in sug and isinstance(sug['jogos'], list) and len(sug['jogos']) > 0:
                    sug['acertos'] = len(set(sug['jogos'][0].get('numeros', [])) & oficiais)
                else:
                    sug['acertos'] = 0
            else:
                sug['acertos'] = 0
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": "Erro de mapeamento: " + str(e)}

@app.post("/auto-sincronizar")
def sync():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    try:
        resp = requests.get(url, verify=False, timeout=10).json()
        concurso_atual = int(resp["numero"])
        dezenas = [int(d) for d in resp["listaDezenas"]]
        
        # Usando "concurso" minúsculo
        check = supabase.table("sorteios").select("concurso").eq("concurso", concurso_atual).execute()
        
        if not check.data:
            data = {"concurso": concurso_atual, **{f"Bola{i+1}": dezenas[i] for i in range(15)}}
            supabase.table("sorteios").insert(data).execute()
            return {"status": "Inserido"}
        return {"status": "Já existe"}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
