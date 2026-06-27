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
        # Busca tudo sem filtro de coluna para garantir que nada seja bloqueado
        sug_res = supabase.table("sugestoes").select("*").execute()
        sort_res = supabase.table("sorteios").select("*").execute()
        
        sugestoes = sug_res.data
        sorteios = sort_res.data
        
        # Lógica de preenchimento forçado se o ID estiver vazio
        for sug in sugestoes:
            # Se não houver concurso_id, assume que é o último (3720) para testar o gráfico
            cid = sug.get('concurso_id') or sug.get('concurso') or 3720
            
            sorteio = next((s for s in sorteios if str(s.get('Concurso', '')) == str(cid)), None)
            
            if sorteio:
                oficiais = set([sorteio.get(f"Bola{i}") for i in range(1, 16) if sorteio.get(f"Bola{i}")])
                if isinstance(sug.get('jogos'), list) and len(sug['jogos']) > 0:
                    sug['acertos'] = len(set(sug['jogos'][0].get('numeros', [])) & oficiais)
                else:
                    sug['acertos'] = 0
            else:
                sug['acertos'] = 0
        
        return {"concursos": sugestoes}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
