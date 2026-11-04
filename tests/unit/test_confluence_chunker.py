"""
Testes Unitarios do Motor de Chunking Estrutural (tests/unit/test_confluence_chunker.py).
Roadmap Apendice: roadmap_apendice_conhecimento_multicamada_rag.md (Secao 6)

Valida rigorosamente:
1. Limite maximo absoluto de 1.100 tokens por chunk
2. Injecao do prefixo contextual [breadcrumb] [Secao: secao] em 'conteudo_embed'
3. Divisao de tabelas com repeticao de cabecalho
4. Descarte de hubs de navegacao (HUB-MODULO-*) e paginas sem valor procedimental
5. Fusao de preambulos e notas curtas (<120 tokens)
6. Zero travessoes unicode em todos os arquivos envolvidos

Zero travessoes em todo o arquivo.
"""

import pytest
from core.confluence_chunker import ConfluenceChunker, ConfluenceChunk

@pytest.fixture
def chunker():
    return ConfluenceChunker()

def test_chunker_basic_structure(chunker):
    doc = {
        "codigo_ref": "CONF-1001",
        "modulo": "Faturamento",
        "titulo": "Emissao de NFe",
        "conteudo_completo": """---
path_hierarquia: Retaguarda > Fiscal > Emissao de NFe
url: https://docs.local/pages/1001
versao: 3
---

# Emissao de NFe

## Passo a Passo

Para emitir a nota fiscal no sistema:
1. Acesse o menu Fiscal > Emissao.
2. Selecione o cliente e os itens da venda.
3. Clique em Gravar e Transmitir para a SEFAZ.

## Cancelamento de Nota

Para cancelar a nota emitida no prazo legal:
1. Localize a nota na grade.
2. Clique no botao Cancelar NF-e e justifique com mais de 15 caracteres.
"""
    }
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1
    for c in chunks:
        assert isinstance(c, ConfluenceChunk)
        assert c.doc_id == "CONF-1001"
        assert c.doc_versao == 3
        assert "Emissao de NFe" in c.breadcrumb
        assert c.n_tokens <= 1100
        assert c.conteudo_embed.startswith(f"[{c.breadcrumb}] [Secao: {c.secao}]\n")
        assert len(c.hash_md5) == 32

def test_chunker_filters_out_hub_trackers(chunker):
    hub_doc = {
        "codigo_ref": "HUB-MODULO-RET",
        "modulo": "Ret",
        "titulo": "Modulo Ret",
        "conteudo_completo": "# Retaguarda\nModulo com 12 issues no Jira.\n- QP-101\n- QP-102"
    }
    chunks = chunker.chunk_document(hub_doc)
    assert len(chunks) == 0

def test_chunker_filters_out_empty_or_tiny_pages(chunker):
    empty_doc = {
        "codigo_ref": "CONF-EMPTY",
        "modulo": "Geral",
        "titulo": "Pagina Vazia",
        "conteudo_completo": "Em construcao."
    }
    chunks = chunker.chunk_document(empty_doc)
    assert len(chunks) == 0

def test_chunker_table_preservation_and_split(chunker):
    # Gera tabela com 60 linhas para forcar split inteligente
    table_header = "| Codigo | Nome do Produto | CST ICMS | Aliquota |\n| :--- | :--- | :--- | :--- |\n"
    rows = "\n".join([f"| {i:03d} | PRODUTO DE TESTE {i} | 060 | 18.0% |" for i in range(1, 80)])
    
    doc = {
        "codigo_ref": "CONF-TABELA",
        "modulo": "Cadastro de Produtos",
        "titulo": "Tabela de Tributacao ICMS",
        "conteudo_completo": f"""# Tabela de Tributacao ICMS\n\nEsta tabela lista o mapeamento de produtos fiscais.\n\n{table_header}{rows}"""
    }
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.n_tokens <= 1100
        # Todas as partes da tabela dividida devem conter o cabecalho da tabela
        if "|" in c.conteudo:
            assert "| Codigo | Nome do Produto |" in c.conteudo
            assert "| :--- | :--- |" in c.conteudo

def test_chunker_hard_token_limit_on_massive_section(chunker):
    # Gera paragrafo massivo com mais de 3.000 tokens
    long_text = "Procedimento detalhado de conferencia de pista e encerramento. " * 300
    doc = {
        "codigo_ref": "CONF-MASSIVE",
        "modulo": "Pista",
        "titulo": "Manual Extenso de Procedimentos",
        "conteudo_completo": f"# Manual Extenso de Procedimentos\n\n## Conferencia Geral\n\n{long_text}"
    }
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.n_tokens <= 1100, f"Chunk {c.chunk_idx} estourou o limite de 1.100: {c.n_tokens}"

def test_chunker_preamble_fusion(chunker):
    doc = {
        "codigo_ref": "CONF-PREAMBLE",
        "modulo": "Caixa",
        "titulo": "Fechamento de Caixa",
        "conteudo_completo": """# Fechamento de Caixa
> **NOTE:** Importante conferir o saldo da gaveta antes de encerrar.

## Procedimento de Encerramento
1. Acesse o PDV.
2. Informe o valor do dinheiro contado.
3. Imprima a folha de sangria.
"""
    }
    chunks = chunker.chunk_document(doc)
    # Nao deve gerar um chunk isolado com apenas o NOTE de 2 linhas
    assert len(chunks) == 1
    assert "saldo da gaveta" in chunks[0].conteudo
    assert "Acesse o PDV" in chunks[0].conteudo

def test_zero_unicode_dashes_in_chunker():
    from pathlib import Path
    base_dir = Path(__file__).resolve().parent.parent.parent
    for rel_path in ["core/confluence_chunker.py", "tests/unit/test_confluence_chunker.py"]:
        fpath = base_dir / rel_path
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "\u2014" not in content, f"Em-dash encontrado em {rel_path}"
        assert "\u2013" not in content, f"En-dash encontrado em {rel_path}"
