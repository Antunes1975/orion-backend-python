from fastapi import FastAPI
from supabase import create_client
import os
from dotenv import load_dotenv

# Carrega variáveis do .env local se existirem
load_dotenv()

app = FastAPI()

# Configuração do Supabase vinda das variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def read_root():
    return {"status": "ORION Motor Ω Online"}

@app.get("/status-base")
def get_status():
    try:
        # Testa a conexão buscando o total de registros na tabela sorteios
        response = supabase.table("sorteios").select("*", count='exact').limit(1).execute()
        return {"message": "Motor conectado ao Supabase", "status": "OK"}
    except Exception as e:
        return {"message": "Erro na conexão", "error": str(e)}
