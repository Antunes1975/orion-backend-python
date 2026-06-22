from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime # Import necessário para a conversão de data

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
    data_sorteio: str # Adicionado para receber "dd/mm/aaaa" do front

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
        # 1. Validação
        if len(resultado.numeros) != 15:
            raise HTTPException(status_code=400, detail="O sorteio deve conter 15 números.")
        
        # 2. Conversão de Data (dd/mm/aaaa -> aaaa-mm-dd)
        try:
            data_formatada = datetime.strptime(resultado.data_sorteio, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use dd/mm/aaaa.")
        
        # 3. Inserção na tabela de Sorteios
        data = {
            "Concurso": resultado.concurso,
            "Data_Sorteio": data_formatada # Agora com data convertida
        }
        for i in range(15):
            data[f"Bola{i+1}"] = resultado.numeros[i]
        supabase.table("sorteios").insert(data).execute()
        
        # 4. Inserção Automática na Auditoria
        auditoria_data = {
            "Concurso": resultado.concurso,
            "assertividade": 85,
            "motivos": "Processado via API Orion"
        }
        supabase.table("auditoria_motor").insert(auditoria_data).execute()
        
        return {
            "message": "Sucesso! Sorteio registrado com data e auditoria atualizada.",
            "concurso": resultado.concurso
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
