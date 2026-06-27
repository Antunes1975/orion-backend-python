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
        # A DICA DO BANCO FOI: use "concurso" (minúsculo)
        res = supabase.table("sugestoes").select("*").order("concurso", desc=True).limit(10).execute()
        sugestoes = res.data
        
        # A tabela sorteios usa "Concurso" (maiúsculo, confirmado antes)
        sort_res = supabase.table("sorteios").select("*").order("Concurso", desc=True).limit(15).execute()
        sorteios = sort_res.data
        
        for sug in sugestoes:
            # Cruzamento: sug['concurso'] (min) com sorteio['Concurso'] (mai)
            sorteio = next((s for s in sorteios if s['Concurso'] == sug['concurso']), None)
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}")])
                # Acessa 'jogos' diretamente como a estrutura JSON que você tem
                if 'jogos' in sug and isinstance(sug['jogos'], list) and len(sug['jogos']) > 0:
                    sug['acertos'] = len(set(sug['jogos'][0].get('numeros', [])) & oficiais)
                else:
                    sug['acertos'] = 0
            else:
                sug['acertos'] = 0
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": "Erro final de mapeamento: " + str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
