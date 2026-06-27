import os
import random
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

load_dotenv()
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Conexão Segura
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# --- MOTOR ESTATÍSTICO ---
def validar_zona_ouro(jogo):
    soma = sum(jogo)
    primos = len(set(jogo) & {2, 3, 5, 7, 11, 13, 17, 19, 23})
    pares = len(set(jogo) & {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24})
    moldura = len(set(jogo) & {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25})
    return (175 <= soma <= 215) and (primos in [5, 6]) and (pares in [7, 8]) and (moldura in [9, 10])

def gerar_cenario_ancora():
    todas = list(range(1, 26))
    for _ in range(1000):
        jogo = sorted(random.sample(todas, 15))
        if validar_zona_ouro(jogo): return jogo
    return sorted(random.sample(todas, 15))

# --- ROTAS DE PRODUÇÃO ---

@app.get("/")
def read_root(): return {"status": "ORION Ω Engine Online"}

@app.get("/status-base")
def status():
    resp = supabase.table("sorteios").select("Concurso").order("Concurso", desc=True).limit(1).execute()
    ult = resp.data[0]['Concurso'] if resp.data else 3714
    return {"ultimo": ult, "alvo": 3720}

@app.get("/historico-assertividade")
def obter_historico():
    try:
        sugestoes = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute().data
        sorteios = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(15).execute().data
        
        for sug in sugestoes:
            sorteio = next((s for s in sorteios if s['Concurso'] == sug['concurso']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}") is not None])
                if len(oficiais) == 15:
                    for jogo in sug['jogos']:
                        acertos = len(set(jogo['numeros']) & oficiais)
                        jogo.update({"acertos": acertos, "status": "HIT" if acertos >= 13 else "PARCIAL" if acertos >= 11 else "MISS"})
                else:
                    for jogo in sug['jogos']: jogo.update({"acertos": 0, "status": "DADO_INCOMPLETO"})
            else:
                for jogo in sug['jogos']: jogo.update({"acertos": 0, "status": "AGUARDANDO"})
        return {"concursos": sugestoes}
    except Exception as e:
        return {"concursos": [], "erro": str(e)}

@app.post("/inserir-manual")
def inserir_manual(concurso: int, numeros: list[int]):
    if len(numeros) != 15: raise HTTPException(status_code=400, detail="Requer 15 dezenas.")
    data = {"Concurso": concurso, **{f"Bola{i+1}": numeros[i] for i in range(15)}}
    supabase.table("sorteios").upsert(data).execute()
    return {"status": "Sucesso", "concurso": concurso}

@app.post("/auto-sincronizar")
def sync():
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    resp = requests.get(url, verify=False, timeout=10).json()
    concurso_caixa = int(resp["numero"])
    dezenas = [int(d) for d in resp["listaDezenas"]]
    
    check = supabase.table("sorteios").select("*").eq("Concurso", concurso_caixa).execute()
    if check.data:
        # Auto-Cura: se estiver incompleto, preenche
        if any(check.data[0].get(f"Bola{i+1}") is None for i in range(15)):
            data = {f"Bola{i+1}": dezenas[i] for i in range(15)}
            supabase.table("sorteios").update(data).eq("Concurso", concurso_caixa).execute()
            return {"status": "Registro manual completado pela Caixa", "concurso": concurso_caixa}
        return {"status": "Registro completo preservado", "concurso": concurso_caixa}
    else:
        # Insere novo
        data = {"Concurso": concurso_caixa, **{f"Bola{i+1}": dezenas[i] for i in range(15)}}
        supabase.table("sorteios").insert(data).execute()
        return {"status": "Novo concurso importado", "concurso": concurso_caixa}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
