"""
Testes Unitarios do Hub de Conectores de Dados Abertos Governamentais (Fase 2 - Pilar 3).
Cobre transicoes do Circuit Breaker, parsing em streaming de CSV da ANP,
eficiencia de memoria sub-100ms, extracao COTEPE PMPF do CONFAZ,
series SGS do BACEN e blindagem de resiliencia sem travamentos.
"""

import time
from pathlib import Path
from unittest.mock import patch

import httpx

from core.integrations.public_data import (
    AnpPublicDataConnector,
    BacenSgsConnector,
    CircuitState,
    ConfazPmpfConnector,
    PublicDataCircuitBreaker,
)


def test_circuit_breaker_transitions():
    """
    Testa ciclo completo de transicoes de estado do Circuit Breaker:
    CLOSED -> 3 falhas -> OPEN -> tentativa bloqueada -> expiracao do cooldown -> HALF_OPEN -> sucesso -> CLOSED.
    """
    cb = PublicDataCircuitBreaker(name="test_cb", failure_threshold=3, cooldown_seconds=0.1)

    # 1. Estado inicial: CLOSED
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.can_execute() is True
    assert cb.consecutive_failures == 0

    # 2. Primeira e segunda falhas consecutivas mantem CLOSED
    cb.record_failure("Falha 1: timeout de conexao")
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.consecutive_failures == 1
    assert cb.can_execute() is True

    cb.record_failure("Falha 2: HTTP 502 Bad Gateway")
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.consecutive_failures == 2
    assert cb.can_execute() is True

    # 3. Terceira falha consecutiva atinge o limiar e transita para OPEN
    cb.record_failure("Falha 3: HTTP 504 Gateway Timeout")
    assert cb.get_state() == CircuitState.OPEN.value
    assert cb.consecutive_failures == 3

    # 4. Durante o cooldown, tentativas adicionais sao bloqueadas
    assert cb.can_execute() is False
    assert cb.get_state() == CircuitState.OPEN.value

    # 5. Apos a expiracao do cooldown, transita para HALF_OPEN
    time.sleep(0.12)
    assert cb.can_execute() is True
    assert cb.get_state() == CircuitState.HALF_OPEN.value
    # Apenas 1 requisicao canario e permitida: chamada subsequente antes do resultado deve ser bloqueada
    assert cb.can_execute() is False

    # 6. Requisicao de teste canario bem-sucedida restaura para CLOSED
    cb.record_success()
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.consecutive_failures == 0
    assert cb.can_execute() is True


def test_circuit_breaker_half_open_failure():
    """
    Testa comportamento do estado HALF_OPEN quando a requisicao canario falha:
    deve transitar imediatamente de volta para OPEN sem nova tolerancia.
    """
    cb = PublicDataCircuitBreaker(name="test_cb_half_open", failure_threshold=3, cooldown_seconds=0.1)

    # Induz estado OPEN com 3 falhas consecutivas
    for idx in range(3):
        cb.record_failure(f"Falha preparatoria {idx + 1}")
    assert cb.get_state() == CircuitState.OPEN.value

    # Aguarda cooldown para atingir HALF_OPEN
    time.sleep(0.12)
    assert cb.can_execute() is True
    assert cb.get_state() == CircuitState.HALF_OPEN.value

    # Falha na chamada de teste canario retorna imediatamente para OPEN
    cb.record_failure("Falha no teste canario")
    assert cb.get_state() == CircuitState.OPEN.value
    assert cb.can_execute() is False


def test_anp_connector_csv_streaming_parsing():
    """
    Valida parsing de payload CSV da ANP com acentos, separadores ;,
    delimitadores e filtragem in-flight por municipio e UF sem retencao de descartados.
    """
    connector = AnpPublicDataConnector()

    csv_content = (
        "Região - Sigla;Estado - Sigla;Município;Revenda;CNPJ da Revenda;Produto;Data da Coleta;Valor de Venda;Bandeira;Unidade de Medida\n"
        "SE;SP;SAO PAULO;AUTO POSTO CENTRO LTDA;11.222.333/0001-44;GASOLINA COMUM;14/10/2026;5,89;BRANCA;R$ / litro\n"
        "SE;SP;CAMPINAS;AUTO POSTO CAMPINAS LTDA;22.333.444/0001-55;GASOLINA COMUM;14/10/2026;5,79;IPIRANGA;R$ / litro\n"
        "SE;RJ;RIO DE JANEIRO;POSTO PRAIA LTDA;33.444.555/0001-66;ETANOL HIDRATADO;14/10/2026;4,19;VIBRA;R$ / litro\n"
        "S;PR;CURITIBA;POSTO PINHAIS LTDA;44.555.666/0001-77;DIESEL S10;14/10/2026;6,09;SHELL;R$ / litro\n"
    )

    # 1. Parsing total sem filtro
    todos = connector.parse_precos_csv(csv_content.encode("utf-8"))
    assert len(todos) == 4

    primeiro = todos[0]
    assert primeiro["regiao"] == "SE"
    assert primeiro["estado_sigla"] == "SP"
    assert primeiro["municipio"] == "SAO PAULO"
    assert primeiro["revenda"] == "AUTO POSTO CENTRO LTDA"
    assert primeiro["cnpj_revenda"] == "11.222.333/0001-44"
    assert primeiro["produto"] == "GASOLINA COMUM"
    assert primeiro["data_coleta"] == "14/10/2026"
    assert primeiro["valor_venda"] == 5.89
    assert primeiro["bandeira"] == "BRANCA"
    assert primeiro["unidade_medida"] == "R$ / litro"

    # 2. Filtragem in-flight por municipio
    res_mun = connector.parse_precos_csv(csv_content, filtro_municipio="SAO PAULO")
    assert len(res_mun) == 1
    assert res_mun[0]["municipio"] == "SAO PAULO"
    assert res_mun[0]["valor_venda"] == 5.89

    # 3. Filtragem in-flight por UF
    res_uf = connector.parse_precos_csv(csv_content, filtro_uf="RJ")
    assert len(res_uf) == 1
    assert res_uf[0]["estado_sigla"] == "RJ"
    assert res_uf[0]["produto"] == "ETANOL HIDRATADO"

    # 4. Compatibilidade com encoding latin1
    csv_latin1 = csv_content.encode("latin1")
    res_latin = connector.parse_precos_csv(csv_latin1, filtro_municipio="CAMPINAS")
    assert len(res_latin) == 1
    assert res_latin[0]["municipio"] == "CAMPINAS"

    # 5. Parsing de base SICOP cadastral de postos com UTF-8 BOM
    sicop_content = (
        b"\xef\xbb\xbfCNPJ;Raz\xc3\xa3o Social;Nome Fantasia;UF;Munic\xc3\xadpio;Bairro;Endere\xc3\xa7o;CEP;Bandeira;Capacidade Tancagem;Status\n"
        b"11.222.333/0001-44;AUTO POSTO CENTRO LTDA;POSTO CENTRO;SP;SAO PAULO;CENTRO;RUA DIREITA 100;01000-000;BRANCA;45000;ATIVO\n"
        b"99.888.777/0001-11;POSTO MINEIRO LTDA;POSTO MINEIRO;MG;BELO HORIZONTE;SAVASSI;AV CONTORNO 200;30000-000;IPIRANGA;30000;ATIVO\n"
    )
    res_sicop = connector.parse_postos_sicop(sicop_content, filtro_uf="SP")
    assert len(res_sicop) == 1
    assert res_sicop[0]["cnpj"] == "11.222.333/0001-44"
    assert res_sicop[0]["capacidade_tancagem"] == 45000.0

    # 6. Precos com UTF-8 BOM e alias de Preco de Venda
    csv_bom_alias = (
        b"\xef\xbb\xbfRegi\xc3\xa3o - Sigla;Estado - Sigla;Munic\xc3\xadpio;Revenda;CNPJ da Revenda;Produto;Data da Coleta;Pre\xc3\xa7o de Venda;Bandeira;Unidade de Medida\n"
        b"SE;SP;SANTOS;POSTO PRAIA MAR;55.666.777/0001-88;GASOLINA ADITIVADA;15/10/2026;6,15;IPIRANGA;R$ / litro\n"
    )
    res_bom = connector.parse_precos_csv(csv_bom_alias)
    assert len(res_bom) == 1
    assert res_bom[0]["regiao"] == "SE"
    assert res_bom[0]["valor_venda"] == 6.15


def test_anp_connector_memory_efficiency():
    """
    Simula parsing de lote volumoso com 10.000 linhas comprovando
    eficiencia de streaming e tempo de execucao inferior a 100ms.
    """
    connector = AnpPublicDataConnector()

    cabecalho = "Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Produto;Data da Coleta;Valor de Venda;Bandeira;Unidade de Medida"
    linhas = [cabecalho]

    # Gera 10.000 linhas simuladas com distribuicao realista
    for i in range(10000):
        mun = "SAO PAULO" if i % 50 == 0 else f"MUNICIPIO_{i}"
        linhas.append(
            f"SE;SP;{mun};POSTO REVENDEDOR {i};12.345.678/0001-90;GASOLINA COMUM;15/10/2026;5,89;BRANCA;R$ / litro"
        )

    payload_bytes = "\n".join(linhas).encode("utf-8")
    assert len(payload_bytes) > 900000  # Payload proximo a 1 MB

    t0 = time.perf_counter()
    registros = connector.parse_precos_csv(payload_bytes, filtro_municipio="SAO PAULO")
    tempo_execucao = time.perf_counter() - t0

    assert len(registros) == 200
    assert tempo_execucao < 0.100, f"Tempo de parsing {tempo_execucao * 1000:.2f} ms excedeu o teto de 100ms"


def test_confaz_pmpf_connector_parsing():
    """
    Valida parsing de Atos COTEPE PMPF estruturados por UF com conversao
    de decimais em padrao monetario brasileiro para reais.
    """
    connector = ConfazPmpfConnector()

    tabela_cotepe = (
        "UF;Gasolina Comum;Gasolina Aditivada;Etanol Hidratado;Diesel S10;Diesel S500;GLP\n"
        "SP;5,850;6,020;3,920;5,990;5,890;8,450\n"
        "RJ;6,050;6,220;4,100;6,150;6,020;8,600\n"
        "MG;5,920;6,110;3,980;6,050;5,940;8,500\n"
    )

    # 1. Parsing completo
    dados = connector.parse_cotepe_text(tabela_cotepe.encode("utf-8"))
    assert len(dados) == 3

    sp = next(r for r in dados if r["uf"] == "SP")
    assert sp["gasolina_comum"] == 5.85
    assert sp["gasolina_aditivada"] == 6.02
    assert sp["etanol_hidratado"] == 3.92
    assert sp["diesel_s10"] == 5.99
    assert sp["diesel_s500"] == 5.89
    assert sp["glp"] == 8.45

    # 2. Filtragem por UF especifica
    dados_mg = connector.parse_cotepe_text(tabela_cotepe, filtro_uf="MG")
    assert len(dados_mg) == 1
    assert dados_mg[0]["uf"] == "MG"
    assert dados_mg[0]["gasolina_comum"] == 5.92
    assert dados_mg[0]["diesel_s10"] == 6.05

    # 3. Parsing com formato HTML de publicacao no DOU
    html_dou = (
        "<table>"
        "<tr><th>UF</th><th>Gasolina Comum</th><th>Gasolina Aditivada</th><th>Etanol Hidratado</th><th>Diesel S10</th><th>Diesel S500</th><th>GLP</th></tr>"
        "<tr><td>PR</td><td>5,750</td><td>5,950</td><td>3,850</td><td>5,890</td><td>5,790</td><td>8,300</td></tr>"
        "</table>"
    )
    dados_html = connector.parse_cotepe_text(html_dou)
    assert len(dados_html) == 1
    assert dados_html[0]["uf"] == "PR"
    assert dados_html[0]["gasolina_comum"] == 5.75

    # 4. Parsing com UTF-8 BOM, colunas fora de ordem e nomenclatura oficial COTEPE/DOU
    dou_bom = (
        b"\xef\xbb\xbfUF;Diesel S-10;Etanol Hidratado Combust\xc3\xadvel (EHC);G\xc3\xa1s Liquefeito de Petr\xc3\xb3leo;Gasolina Comum\n"
        b"BA;6,120;4,250;8,700;5,950\n"
    )
    dados_dou = connector.parse_cotepe_text(dou_bom)
    assert len(dados_dou) == 1
    ba = dados_dou[0]
    assert ba["uf"] == "BA"
    assert ba["diesel_s10"] == 6.12
    assert ba["etanol_hidratado"] == 4.25
    assert ba["glp"] == 8.70
    assert ba["gasolina_comum"] == 5.95


def test_bacen_sgs_connector_json_parsing():
    """
    Valida parsing de JSON das series canonicas do BACEN SGS:
    Selic diaria (11), PTAX Dolar Venda (10813) e IPCA mensal (433).
    """
    connector = BacenSgsConnector()

    json_selic = b'[{"data": "14/10/2026", "valor": "10.65"}, {"data": "15/10/2026", "valor": "10.75"}]'
    json_ptax = b'[{"data": "15/10/2026", "valor": "5.6540"}]'
    json_ipca = b'[{"data": "01/09/2026", "valor": "0.44"}]'

    # 1. Fetch de serie isolada com payload mock
    res_selic = connector.fetch_serie(11, mock_payload=json_selic)
    assert res_selic.success is True
    assert res_selic.records_count == 2
    assert res_selic.data[1]["data"] == "15/10/2026"
    assert res_selic.data[1]["data_iso"] == "2026-10-15"
    assert res_selic.data[1]["valor"] == 10.75

    # 2. Fetch consolidado de indicadores financeiros com calculo de custo de estoque
    res_macro = connector.fetch_indicadores_financeiros(
        mock_payloads={
            11: json_selic,
            10813: json_ptax,
            433: json_ipca,
        }
    )
    assert res_macro.success is True
    assert res_macro.records_count == 1
    snapshot = res_macro.data[0]
    assert snapshot["selic_anual"] == 10.75
    assert snapshot["ptax_dolar_venda"] == 5.6540
    assert snapshot["ipca_mensal"] == 0.44
    assert snapshot["data_referencia"] == "2026-10-15"
    assert snapshot["custo_carregamento_estoque"] > 0

    # 3. Validacao da formula de custo de carregamento
    custo_calculado = connector.calcular_custo_carregamento(
        volume_litros=50000.0,
        custo_unitario=5.0,
        taxa_selic_anual=10.75,
        dias_estoque=30,
    )
    assert custo_calculado == snapshot["custo_carregamento_estoque"]

    # 4. Compatibilidade com UTF-8 BOM no payload JSON
    json_bom = b'\xef\xbb\xbf[{"data": "16/10/2026", "valor": "10.80"}]'
    res_bom = connector.fetch_serie(11, mock_payload=json_bom)
    assert res_bom.success is True
    assert res_bom.records_count == 1
    assert res_bom.data[0]["valor"] == 10.80

    # 5. Parametros em formato string e defensivos no calculo de custo de estoque
    custo_str = connector.calcular_custo_carregamento("50000", "5.0", "10.75", "30")
    assert custo_str == custo_calculado


def test_connectors_circuit_breaker_integration():
    """
    Simula falhas de rede (HTTP 500 e timeout) e ativação transparente do Circuit Breaker
    em cada um dos tres conectores sem propagar excecoes nao tratadas para a aplicacao.
    """
    conectores = [
        AnpPublicDataConnector(circuit_breaker=PublicDataCircuitBreaker(name="anp_cb", failure_threshold=3, cooldown_seconds=3600.0)),
        ConfazPmpfConnector(circuit_breaker=PublicDataCircuitBreaker(name="confaz_cb", failure_threshold=3, cooldown_seconds=3600.0)),
        BacenSgsConnector(circuit_breaker=PublicDataCircuitBreaker(name="bacen_cb", failure_threshold=3, cooldown_seconds=3600.0)),
    ]

    for conector in conectores:
        cb = conector.circuit_breaker
        assert cb.get_state() == CircuitState.CLOSED.value

        # Simula 3 falhas consecutivas de rede via mock do httpx
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = httpx.ConnectTimeout("Falha de conexao com gateway governamental")

            for tentativa in range(3):
                res = conector.fetch_latest_data()
                assert res.success is False
                assert res.cached is False
                assert "Falha de conexao" in (res.error_message or "")

        # O circuito deve agora estar OPEN
        assert cb.get_state() == CircuitState.OPEN.value
        assert conector.is_healthy is False

        # Quarta tentativa deve ser bloqueada localmente pelo Circuit Breaker sem disparar HTTP
        with patch("httpx.Client.get") as mock_get:
            res_bloqueado = conector.fetch_latest_data()
            mock_get.assert_not_called()
            assert res_bloqueado.success is False
            assert res_bloqueado.cached is True
            assert "bloqueadas" in (res_bloqueado.error_message or "").lower() or "suspensas" in (res_bloqueado.error_message or "").lower()


def test_connectors_health_check():
    """
    Valida metodo check_health() para cada conector governamental.
    """
    conector_anp = AnpPublicDataConnector()
    conector_confaz = ConfazPmpfConnector()
    conector_bacen = BacenSgsConnector()

    for conector in (conector_anp, conector_confaz, conector_bacen):
        status = conector.check_health()
        assert isinstance(status, dict)
        assert status["source_name"] == conector.source_name
        assert status["is_healthy"] is True
        assert status["circuit_state"] == CircuitState.CLOSED.value
        assert isinstance(status["latency_ms"], float)
        assert status["latency_ms"] >= 0.0

    # Valida degradacao de saude quando circuito abre
    conector_anp.circuit_breaker.state = CircuitState.OPEN
    status_degradado = conector_anp.check_health()
    assert status_degradado["is_healthy"] is False
    assert status_degradado["circuit_state"] == CircuitState.OPEN.value


def test_ausencia_travessoes_conectores():
    """
    Garante ausencia estrita de travessoes Unicode (\\u2014 e \\u2013) em todo
    o codigo dos conectores de dados abertos e seus respectivos testes.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    diretorio_conectores = repo_root / "core" / "integrations" / "public_data"
    arquivos_alvo = list(diretorio_conectores.glob("*.py"))
    arquivos_alvo.append(repo_root / "core" / "integrations" / "__init__.py")
    arquivos_alvo.append(repo_root / "docs" / "roadmap_integracao_apis_publicas.md")
    arquivos_alvo.append(Path(__file__).resolve())

    assert len(arquivos_alvo) >= 7, f"Esperado ao menos 7 arquivos no pacote, encontrado {len(arquivos_alvo)}"

    for arquivo in arquivos_alvo:
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "\u2014" not in conteudo, f"Travessao em-dash (\\u2014) encontrado no arquivo {arquivo.name}"
        assert "\u2013" not in conteudo, f"Travessao en-dash (\\u2013) encontrado no arquivo {arquivo.name}"
