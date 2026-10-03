"""
Seed de Dados de Vendas da Loja de Conveniência (Market Basket Analysis).
Popula transações realistas com múltiplos itens em `pedido` e `itemped` no ERP dev (porta 5433/5435)
para permitir mineração de regras de associação e cálculo de Suporte, Confiança e Lift.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, time

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.tools import get_erp_connection

def seed_conveniencia(force: bool = False):
    conn = get_erp_connection()
    with conn.cursor() as cur:
        # Verifica se já existem pedidos de conveniência semeados (codi iniciando com '2')
        cur.execute("SELECT COUNT(*) FROM pedido WHERE TRIM(codi) LIKE '20%';")
        qtd_existente = cur.fetchone()[0]
        if qtd_existente > 0 and not force:
            print(f"[SEED] Tabela 'pedido' já possui {qtd_existente} registros de conveniência semeados. Pulando seed.")
            conn.close()
            return qtd_existente

        if force and qtd_existente > 0:
            print("[SEED] Limpando dados de conveniência semeados anteriormente...")
            cur.execute("DELETE FROM itemped WHERE TRIM(pedido) LIKE '20%';")
            cur.execute("DELETE FROM pedido WHERE TRIM(codi) LIKE '20%';")
            conn.commit()

        # Obtém chaves válidas de fechacaixa (2026-09-01 para não interferir nos testes de conciliação do dia 02/09)
        cur.execute("""
            SELECT fc.dtmov, fc.turno, fc.codpdv
            FROM fechacaixa fc
            WHERE fc.dtmov = '2026-09-01' AND fc.codpdv = '004'
            LIMIT 1;
        """)
        row_fc = cur.fetchone()
        if not row_fc:
            cur.execute("SELECT dtmov, turno, codpdv FROM fechacaixa WHERE dtmov != '2026-09-02' LIMIT 1;")
            row_fc = cur.fetchone()

        dtmov, turno, codpdv = row_fc

        cur.execute("SELECT cli_cod_a FROM clientes LIMIT 1;")
        clie = cur.fetchone()[0]

        cur.execute("SELECT matr FROM funcionarios LIMIT 1;")
        vendedor = cur.fetchone()[0]

        cur.execute("SELECT codpra FROM prazos LIMIT 1;")
        formapg = cur.fetchone()[0]

        # Produtos reais do catálogo com preços
        # 00022: CERVEJA HEINEKEN LN 330ML (11.00)
        # 00095: GELO ESCAMA 10 KGS (15.00)
        # 00079: BATATA ONDULADA TIZCO CEBOLA SALSA 80G (9.99)
        # 00132: CAFE EXPRESSO 400ML. (7.00)
        # 00133: PÃO DE QUEIJO UN. (5.00)
        # 00026: AGUA MINERAL MINALBA SEM GAS 1,5L (6.00)
        # 00051: REFRIGERANTE COCA COLA ZERO 600ML (7.99)
        # 00148: SALGADO ASSADO CONSUMO (6.00)
        # 00078: CHOCOLATE KIT KAT AO LEITE 41,5G (4.99)
        # 00198: ENERGETICO RED BULL TRADICIONAL 473ML (14.90)
        # 00053: BALA HALLS MENTA 28GX (2.99)
        # 00074: BISCOITO CHOCOLICIA 132G (11.49)

        precos = {
            "00022": Decimal("11.00"),
            "00095": Decimal("15.00"),
            "00079": Decimal("9.99"),
            "00132": Decimal("7.00"),
            "00133": Decimal("5.00"),
            "00026": Decimal("6.00"),
            "00051": Decimal("7.99"),
            "00148": Decimal("6.00"),
            "00078": Decimal("4.99"),
            "00198": Decimal("14.90"),
            "00053": Decimal("2.99"),
            "00074": Decimal("11.49"),
        }

        # Definição das cestas de compra (60 transações)
        cestas = []
        # Combo 1: Cerveja Heineken + Gelo (22 cestas)
        for _ in range(22):
            cestas.append(["00022", "00095"])
        # Combo 1 triplo: Cerveja Heineken + Gelo + Batata (3 cestas)
        for _ in range(3):
            cestas.append(["00022", "00095", "00079"])
        # Cerveja avulsa (4 cestas)
        for _ in range(4):
            cestas.append(["00022"])
        # Gelo avulso (3 cestas)
        for _ in range(3):
            cestas.append(["00095"])

        # Combo 2: Café Expresso + Pão de Queijo (20 cestas)
        for _ in range(20):
            cestas.append(["00132", "00133"])
        # Combo 2 triplo: Café Expresso + Pão de Queijo + Água (4 cestas)
        for _ in range(4):
            cestas.append(["00132", "00133", "00026"])
        # Café avulso (3 cestas)
        for _ in range(3):
            cestas.append(["00132"])
        # Pão de Queijo avulso (2 cestas)
        for _ in range(2):
            cestas.append(["00133"])

        # Combo 3: Coca-Cola Zero + Salgado Assado (14 cestas)
        for _ in range(14):
            cestas.append(["00051", "00148"])
        # Combo 3 triplo: Coca-Cola + Salgado + Kit Kat (3 cestas)
        for _ in range(3):
            cestas.append(["00051", "00148", "00078"])
        # Coca-Cola avulsa (5 cestas)
        for _ in range(5):
            cestas.append(["00051"])
        # Salgado avulso (4 cestas)
        for _ in range(4):
            cestas.append(["00148"])

        # Combo 4: Red Bull + Halls Menta (10 cestas)
        for _ in range(10):
            cestas.append(["00198", "00053"])
        # Red Bull avulso (3 cestas)
        for _ in range(3):
            cestas.append(["00198"])
        # Halls avulso (5 cestas)
        for _ in range(5):
            cestas.append(["00053"])

        # Cestas variadas (Água + Biscoito Chocolícia) (6 cestas)
        for _ in range(6):
            cestas.append(["00026", "00074"])

        pedidos_inseridos = 0
        itens_inseridos = 0

        for idx, itens_cesta in enumerate(cestas, start=1):
            codi = f"20{idx:04d}"
            cupom = f"C{idx:04d}"
            
            # Calcula valor total do pedido
            total_pedido = sum(precos[sku] for sku in itens_cesta)

            # Insere pedido
            cur.execute("""
                INSERT INTO pedido (
                    codi, cupom, pdv, turno, clie, vendedor, dtem, situ, valortotal, formapg, hsmov
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                );
            """, (
                f"{codi:<8}",
                f"{cupom:<8}",
                codpdv,
                turno,
                clie,
                vendedor,
                dtmov,
                None,
                total_pedido,
                formapg,
                time(8 + (idx % 12), (idx * 7) % 60, 0)
            ))
            pedidos_inseridos += 1

            # Insere itemped
            for controle, sku in enumerate(itens_cesta, start=1):
                preco_unit = precos[sku]
                cur.execute("""
                    INSERT INTO itemped (
                        pedido, controle, codpec, cupom, quant, valunit, valitem, dtmov, turno
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                """, (
                    f"{codi:<8}",
                    controle,
                    sku,
                    f"{cupom:<8}",
                    Decimal("1.000"),
                    preco_unit,
                    preco_unit,
                    dtmov,
                    turno
                ))
                itens_inseridos += 1

        conn.commit()
        print(f"[SEED CONCLUÍDO] {pedidos_inseridos} pedidos e {itens_inseridos} itens inseridos com sucesso!")
        conn.close()
        return pedidos_inseridos

if __name__ == "__main__":
    seed_conveniencia(force=True)
