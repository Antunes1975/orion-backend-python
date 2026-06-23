from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime

# Inicialização
load_dotenv()
app = FastAPI()

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class ResultadoSorteio(BaseModel):
    concurso: int
    numeros: list[int]
    data_sorteio: str

# --- ROTAS DO MOTOR ORION Ω ---

@app.get("/")
def read_root():
    return {"status": "ORION Motor Ω Online"}

@app.get("/status-base")
def get_status():
    return {"message": "Motor conectado ao Supabase", "status": "OK"}

@app.get("/ultimos-concursos")
async def ultimos_concursos():
    try:
        response = supabase.table("auditoria_motor") \
            .select("Concurso, assertividade, motivos") \
            .order("Concurso", desc=True) \
            .limit(5) \
            .execute()
        return response.data
    except Exception as e:
        return []

@app.post("/salvar-resultado")
async def salvar_resultado(resultado: ResultadoSorteio):
    try:
        if len(resultado.numeros) != 15:
            raise HTTPException(status_code=400, detail="O sorteio deve conter 15 números.")
        
        try:
            data_formatada = datetime.strptime(resultado.data_sorteio, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use dd/mm/aaaa.")
        
        data = {
            "Concurso": resultado.concurso,
            "Data_Sorteio": data_formatada
        }
        for i in range(15):
            data[f"Bola{i+1}"] = resultado.numeros[i]
        supabase.table("sorteios").insert(data).execute()
        
        auditoria_data = {
            "Concurso": resultado.concurso,
            "assertividade": 85,
            "motivos": "Processado via API Orion"
        }
        supabase.table("auditoria_motor").insert(auditoria_data).execute()
        
        return {
            "message": "Sucesso! Sorteio registrado e auditoria atualizada.",
            "concurso": resultado.concurso
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTA: AUDITORIA DE PERFORMANCE (Integrada à feedback_assertividade) ---

def calcular_acertos(numeros_sugeridos, numeros_sorteados):
    return len(set(numeros_sugeridos) & set(numeros_sorteados))

@app.post("/auditar-diario-bordo")
async def auditar_diario(concurso: int):
    try:
        # Busca o resultado oficial
        oficial = supabase.table("sorteios").select("*").eq("Concurso", concurso).execute()
        if not oficial.data:
            raise HTTPException(status_code=404, detail="Sorteio oficial não encontrado.")
        
        numeros_oficiais = [oficial.data[0][f"Bola{i+1}"] for i in range(15)]
        
        # Busca sugestões (assumindo tabela 'sugestoes_geradas')
        sugestoes = supabase.table("sugestoes_geradas").select("*").eq("concurso", concurso).execute()
        
        for jogo in sugestoes.data:
            acertos = calcular_acertos(jogo["numeros"], numeros_oficiais)
            
            # Gravação na sua nova tabela oficial de feedback
            feedback_data = {
                "concurso": concurso,
                "sugestao_id": jogo["id"],
                "acertos": acertos,
                "data_conferencia": datetime.now().isoformat()
            }
            supabase.table("feedback_assertividade").insert(feedback_data).execute()
            
        return {"message": f"Auditoria concluída com sucesso na tabela feedback_assertividade para o concurso {concurso}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROTA ORIGINAL DE CÁLCULO ---

@app.post("/calcular-media")
async def calcular_media(salarios: list[float]):
    num_descarte = int(len(salarios) * 0.20)
    df_filtrado = sorted(salarios)[num_descarte:]
    media_final = sum(df_filtrado) / len(df_filtrado) if df_filtrado else 0
    return {
        "media_final": round(float(media_final), 2),
        "total": len(salarios),
        "descartados": num_descarte
    }
