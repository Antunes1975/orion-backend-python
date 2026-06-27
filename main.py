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
        # Busca na tabela sugestoes usando "concurso" (minúsculo, conforme seu banco)
        sugestoes_res = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute()
        sugestoes = sugestoes_res.data
        
        # Busca na tabela sorteios usando "Concurso" (maiúsculo, conforme seu banco)
        sorteios_res = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(15).execute()
        sorteios = sorteios_res.data
        
        for sug in sugestoes:
            # Cruza: sug['concurso'] (min) com sorteio['Concurso'] (mai)
            sorteio = next((s for s in sorteios if s['Concurso'] == sug['concurso']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}")])
                # Calcula acertos comparando com a lista de jogos
                if 'jogos' in sug and len(sug['jogos']) > 0:
                    sug['acertos'] = len(set(sug['jogos'][0]['numeros']) & oficiais)
                else:
                    sug['acertos'] = 0
            else:
                sug['acertos'] = 0
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": f"Erro de banco de dados: {str(e)}"}

@app.post("/auto-sincronizar")
def sync():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    try:
        resp = requests.get(url, verify=False, timeout=10).json()
        concurso_atual = int(resp["numero"])
        dezenas = [int(d) for d in resp["listaDezenas"]]
        
        # Verifica se o concurso atual já existe na tabela sorteios
        check = supabase.table("sorteios").select("Concurso").eq("Concurso", concurso_atual).execute()
        
        if not check.data:
            # Insere dados usando "Concurso" (maiúsculo)
            data = {"Concurso": concurso_atual, **{f"Bola{i+1}": dezenas[i] for i in range(15)}}
            supabase.table("sorteios").insert(data).execute()
            return {"status": "Concurso novo inserido com sucesso", "concurso": concurso_atual}
        
        return {"status": "Concurso já existe, nada alterado", "concurso": concurso_atual}
    except Exception as e:
        return {"erro": f"Falha na sincronização: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
