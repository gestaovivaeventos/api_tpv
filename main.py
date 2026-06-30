from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool = None
try:
    pool = SimpleConnectionPool(
        minconn=1, maxconn=10,
        host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DB"), user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"), cursor_factory=RealDictCursor
    )
except psycopg2.OperationalError as e:
    print(f"ERRO CRÍTICO: Falha ao inicializar o pool de conexões. {e}")

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/dados")
def obter_dados(limit: int = 5000, offset: int = 0):
    if not pool:
        raise HTTPException(status_code=503, detail="Serviço indisponível: pool de conexões falhou.")

    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cursor:
            query = """
                SELECT
	TO_CHAR(
		DATE_TRUNC('month', o.dt_liquidacao),
		'DD/MM/YYYY'
	) AS "MÊS",
	u.nm_unidade,
	SUM(o.vl_pago) AS "TOTAL_ARRECADADO"
FROM
	tb_ordem o
	JOIN tb_fundo f ON f.id = o.fundo_id
	JOIN tb_unidade u ON u.id = f.unidade_id
	JOIN tb_integrante i ON i.id = o.integrante_id
WHERE
	o.vl_pago IS NOT NULL
	AND o.fl_ativo IS TRUE
	AND u.categoria = '2' -- FRANQUIA VIVA EVENTOS
	AND f.tipocliente_id NOT IN (7, 14, 16)
	AND o.vl_pago > 0
	AND o.dt_liquidacao IS NOT NULL
	AND o.dt_liquidacao BETWEEN '2026-01-01' AND current_date
	AND (
		o.fl_cobranca_royalties IS FALSE
		OR o.fl_cobranca_royalties IS NULL
	)
	AND o.ds_mensagem NOT ILIKE '%estorno%'
	AND o.ds_mensagem NOT ILIKE '%migração%'
	AND o.ds_mensagem NOT ILIKE '%distrato%'
	AND o.ds_mensagem NOT ILIKE '%teste tarifa%'
	AND o.ds_mensagem NOT ILIKE '%devolução%'
	AND o.ds_mensagem NOT ILIKE '%transferencia%'
	AND o.ds_mensagem NOT ILIKE '%Arrecadação Anterior - Pago%'
GROUP BY
	DATE_TRUNC('month', o.dt_liquidacao),
	u.nm_unidade
ORDER BY
	DATE_TRUNC('month', o.dt_liquidacao),
	u.nm_unidade
LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, offset))
            dados = cursor.fetchall()
        
        return {"dados": dados}
    except Exception as e:
        # Isso vai te ajudar a ver o erro real no log do Vercel se acontecer de novo
        print(f"Erro na query: {e}") 
        raise HTTPException(status_code=500, detail=f"Erro ao consultar o banco de dados: {e}")
    finally:
        if conn:
            pool.putconn(conn)
