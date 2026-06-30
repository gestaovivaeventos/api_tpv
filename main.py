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
                    AND o.ds_mensagem NOT ILIKE '%%estorno%%'
                    AND o.ds_mensagem NOT ILIKE '%%migração%%'
                    AND o.ds_mensagem NOT ILIKE '%%distrato%%'
                    AND o.ds_mensagem NOT ILIKE '%%teste tarifa%%'
                    AND o.ds_mensagem NOT ILIKE '%%devolução%%'
                    AND o.ds_mensagem NOT ILIKE '%%transferencia%%'
                    AND o.ds_mensagem NOT ILIKE '%%Arrecadação Anterior - Pago%%'
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
