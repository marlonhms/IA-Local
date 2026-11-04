"""
Sincronizador Incremental Confluence -> RAG Local AURA (scripts/sync_confluence_delta.py).
Busca exclusivamente o que e NOVO (59 paginas) e o que foi EDITADO (188 paginas) no Confluence Cloud
do espaco 'webPosto' (totalizando 247 atualizacoes, sem reprocessar as 719 inalteradas).

Fluxo:
1. Le credenciais de C:\\Users\\Marlon\\Documents\\RAG WP\\quality-rag\\.env
2. Mapeia versoes locais existentes nos arquivos .md
3. Consulta catalogo remoto de paginas (/wiki/api/v2/spaces/1179672/pages)
4. Filtra apenas delta (novas ou com version.number > local)
5. Baixa o corpo HTML, labels e autor de cada pagina do delta
6. Converte para Markdown estruturado e salva em quality-rag/sources/confluence
7. Atualiza o checkpoint confluence_checkpoint.json
8. Upserta imediatamente no banco SQLite FTS5 da AURA (data/webposto_knowledge.db)

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Diretorios do projeto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "webposto_knowledge.db"

RAG_WP_ROOT = Path(r"C:\Users\Marlon\Documents\RAG WP")
SOURCES_CONFLUENCE_DIR = RAG_WP_ROOT / "quality-rag" / "sources" / "confluence"
CHECKPOINT_PATH = RAG_WP_ROOT / "quality-rag" / "checkpoints" / "confluence_checkpoint.json"
ENV_FILE = RAG_WP_ROOT / "quality-rag" / ".env"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sync_confluence")


def carregar_credenciais() -> Tuple[str, str, str]:
    if not ENV_FILE.exists():
        raise FileNotFoundError(f"Arquivo .env nao encontrado em: {ENV_FILE}")

    env_vars = {}
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")

    domain = env_vars.get("ATLASSIAN_DOMAIN", "").rstrip("/")
    email = env_vars.get("ATLASSIAN_EMAIL", "")
    token = env_vars.get("ATLASSIAN_API_TOKEN", "")

    if not domain or not email or not token:
        raise ValueError("Credenciais Atlassian incompletas no arquivo .env.")

    return domain, email, token


def montar_headers(email: str, token: str) -> Dict[str, str]:
    auth_str = f"{email}:{token}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def carregar_documentos_locais() -> Dict[str, Dict[str, Any]]:
    """Indexa paginas locais por page_id com versao e data de atualizacao."""
    locais: Dict[str, Dict[str, Any]] = {}
    if not SOURCES_CONFLUENCE_DIR.exists():
        return locais

    for fpath in SOURCES_CONFLUENCE_DIR.rglob("*.md"):
        try:
            raw = fpath.read_text(encoding="utf-8", errors="ignore")
            if not raw.startswith("---"):
                continue
            partes = raw.split("---", 2)
            if len(partes) < 3:
                continue
            meta = yaml.safe_load(partes[1]) or {}
            pid = str(meta.get("page_id") or "")
            if pid:
                locais[pid] = {
                    "file_path": fpath,
                    "titulo": meta.get("titulo") or fpath.stem,
                    "versao": int(meta.get("versao") or 1),
                    "atualizado": meta.get("atualizado") or "",
                }
        except Exception:
            pass

    return locais


def sanitize_filename(text: str) -> str:
    text = text.strip()
    text = re.sub(r'[\/\\:\*\?"<>\|]', "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-").lower() or "pagina"


def html_to_clean_markdown(html_content: str) -> str:
    """Converte HTML do Confluence para Markdown limpo."""
    if not html_content:
        return "_Pagina sem conteudo._"

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove elementos desnecessarios
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()

    # Trata macros do Confluence
    for macro in soup.find_all("ac:structured-macro"):
        macro_name = macro.get("ac:name", "")
        body = macro.find("ac:rich-text-body")
        if body:
            macro.replace_with(f"\n> **{macro_name.upper()}:**\n> {body.get_text().strip()}\n")
        else:
            macro.decompose()

    # Converte para markdown
    markdown = md(str(soup), heading_style="ATX", strip=["img"])
    # Limpa espacos em excesso
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def resolve_path_parts(page_id: str, page_map: Dict[str, Any], max_depth: int = 8) -> List[str]:
    parts = []
    current_id = page_id
    depth = 0

    while depth < max_depth:
        entry = page_map.get(current_id)
        if not entry:
            break
        parent_id = entry.get("parent_id", "")
        if not parent_id or parent_id not in page_map:
            break
        parts.insert(0, page_map[parent_id]["slug"])
        current_id = parent_id
        depth += 1

    return parts


def resolve_hierarchy_label(page_id: str, page_map: Dict[str, Any], max_depth: int = 8) -> str:
    titles = []
    current_id = page_id
    depth = 0

    while depth < max_depth:
        entry = page_map.get(current_id)
        if not entry:
            break
        titles.insert(0, entry["title"])
        parent_id = entry.get("parent_id", "")
        if not parent_id or parent_id not in page_map:
            break
        current_id = parent_id
        depth += 1

    return " > ".join(titles)


def upsert_pagina_no_banco_aura(
    conn: sqlite3.Connection,
    page_id: str,
    modulo: str,
    titulo: str,
    subtitulo: str,
    resumo: str,
    corpo: str,
    tags: str,
    meta: Dict[str, Any]
):
    """Atualiza ou insere a pagina diretamente no SQLite FTS5 da AURA."""
    codigo_ref = f"CONF-{page_id}"
    with conn:
        conn.execute("""
            INSERT INTO tabela_conhecimento (
                pilar, codigo_ref, modulo, titulo, subtitulo,
                resumo_executivo, conteudo_completo, tabelas_banco,
                impacto_financeiro, acao_recomendada, tags_busca, metadados_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo_ref) DO UPDATE SET
                titulo = excluded.titulo,
                subtitulo = excluded.subtitulo,
                resumo_executivo = excluded.resumo_executivo,
                conteudo_completo = excluded.conteudo_completo,
                tags_busca = excluded.tags_busca,
                metadados_json = excluded.metadados_json;
        """, (
            "confluence_procedimentos",
            codigo_ref,
            modulo,
            titulo,
            subtitulo,
            resumo,
            corpo,
            "",
            "",
            f"Consultar rotina '{titulo}' no modulo {modulo} do webPosto.",
            tags,
            json.dumps(meta, ensure_ascii=False)
        ))


def sincronizar_delta_confluence(max_pages: Optional[int] = None):
    logger.info("=" * 70)
    logger.info("  SINCRONIZACAO INCREMENTAL DO CONFLUENCE -> AURA RAG")
    logger.info("=" * 70)

    domain, email, token = carregar_credenciais()
    headers = montar_headers(email, token)
    locais = carregar_documentos_locais()
    logger.info(f"Paginas locais indexadas anteriormente: {len(locais)}")

    # 1. Carrega todas as paginas do space via v2 (somente metadados de cabecalho)
    space_id = "1179672"
    url_pages = f"{domain}/wiki/api/v2/spaces/{space_id}/pages"
    params = {"limit": 250}

    remote_pages: List[Dict[str, Any]] = []
    cursor = None
    batch_idx = 0

    logger.info("Consultando catalogo de paginas no Confluence Cloud...")
    while True:
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url_pages, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            logger.error(f"Erro ao buscar paginas: {resp.status_code} - {resp.text[:200]}")
            break

        data = resp.json()
        batch = data.get("results", [])
        remote_pages.extend(batch)
        batch_idx += 1
        logger.info(f"  Batch {batch_idx}: +{len(batch)} paginas (Total: {len(remote_pages)})")

        next_link = data.get("_links", {}).get("next", "")
        if not next_link:
            break
        m = re.search(r"cursor=([^&]+)", next_link)
        if not m:
            break
        cursor = m.group(1)
        time.sleep(0.2)

    logger.info(f"Total de paginas ativas no Confluence remoto: {len(remote_pages)}")

    # 2. Constrói mapa de hierarquia para todos os IDs
    page_map: Dict[str, Any] = {}
    for p in remote_pages:
        pid = str(p.get("id"))
        title = p.get("title", "sem-titulo")
        parent_id = str(p.get("parentId") or "")
        page_map[pid] = {
            "title": title,
            "parent_id": parent_id,
            "slug": sanitize_filename(title),
        }

    # 3. Identifica estritamente o delta: Novas ou Editadas
    delta_pages: List[Dict[str, Any]] = []
    novas_count = 0
    editadas_count = 0

    for p in remote_pages:
        pid = str(p.get("id"))
        v_info = p.get("version", {}) or {}
        remote_v = int(v_info.get("number") or 1)
        remote_updated = v_info.get("createdAt") or ""

        if pid not in locais:
            delta_pages.append({
                "page": p,
                "motivo": "NOVA",
                "remote_version": remote_v,
            })
            novas_count += 1
        else:
            loc = locais[pid]
            local_v = loc["versao"]
            local_up = loc["atualizado"]

            if remote_v > local_v or (remote_updated and remote_updated != local_up):
                delta_pages.append({
                    "page": p,
                    "motivo": f"EDITADA (v{local_v} -> v{remote_v})",
                    "remote_version": remote_v,
                    "old_file": loc["file_path"],
                })
                editadas_count += 1

    logger.info("=" * 60)
    logger.info(f"DELTA IDENTIFICADO:")
    logger.info(f"  • Paginas Novas   : {novas_count}")
    logger.info(f"  • Paginas Editadas: {editadas_count}")
    logger.info(f"  • Total para Sincronizar: {len(delta_pages)}")
    logger.info("=" * 60)

    if not delta_pages:
        logger.info("[OK] Nenhuma alteracao encontrada no Confluence. Base ja esta 100% atualizada.")
        return

    if max_pages:
        delta_pages = delta_pages[:max_pages]
        logger.info(f"Limitando execucao para as primeiras {max_pages} paginas.")

    # Conexao com o SQLite da AURA
    conn_aura = sqlite3.connect(str(DB_PATH))

    # 4. Extrai o corpo completo das paginas do delta e grava
    processadas = 0
    erros = 0

    for idx, item in enumerate(delta_pages, 1):
        p_basic = item["page"]
        page_id = str(p_basic.get("id"))
        title = p_basic.get("title", "")
        motivo = item["motivo"]

        logger.info(f"[{idx}/{len(delta_pages)}] Baixando ({motivo}): '{title}' (ID {page_id})...")

        try:
            # Requisita pagina com corpo storage
            url_single = f"{domain}/wiki/api/v2/pages/{page_id}"
            resp_detail = requests.get(url_single, params={"body-format": "storage"}, headers=headers, timeout=20)
            if resp_detail.status_code != 200:
                logger.warning(f"  Falha ao baixar corpo da pagina {page_id}: {resp_detail.status_code}")
                erros += 1
                continue

            page_data = resp_detail.json()
            body_html = page_data.get("body", {}).get("storage", {}).get("value", "")
            markdown_body = html_to_clean_markdown(body_html)

            # Labels da pagina
            url_labels = f"{domain}/wiki/api/v2/pages/{page_id}/labels"
            resp_labels = requests.get(url_labels, headers=headers, timeout=10)
            labels = []
            if resp_labels.status_code == 200:
                labels = [l.get("name") for l in resp_labels.json().get("results", []) if l.get("name")]

            # Metadados
            v_info = page_data.get("version", {}) or {}
            versao = int(v_info.get("number") or 1)
            updated_at = v_info.get("createdAt") or ""
            created_at = page_data.get("createdAt") or ""
            author_id = page_data.get("authorId") or ""
            parent_id = str(page_data.get("parentId") or "")
            parent_title = page_map.get(parent_id, {}).get("title", "") if parent_id else ""

            path_parts = resolve_path_parts(page_id, page_map)
            path_hierarchy = resolve_hierarchy_label(page_id, page_map)
            slug = sanitize_filename(title)

            modulo = "Geral"
            if ">" in path_hierarchy:
                partes_h = [p.strip() for p in path_hierarchy.split(">")]
                if len(partes_h) > 1:
                    modulo = partes_h[1]

            frontmatter = {
                "source": "confluence",
                "page_id": page_id,
                "space": "webPosto",
                "space_id": space_id,
                "titulo": title,
                "slug": slug,
                "parent_id": parent_id or None,
                "parent_titulo": parent_title or None,
                "path_hierarquia": path_hierarchy,
                "labels": labels,
                "autor": author_id or "autor-interno",
                "criado": created_at,
                "atualizado": updated_at,
                "versao": versao,
                "url": f"{domain}/wiki/spaces/webPosto/pages/{page_id}",
                "extraido_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            full_md = f"---\n{yaml.dump(frontmatter, allow_unicode=True)}---\n\n# {title}\n\n{markdown_body}\n"

            # Caminho de arquivo espelhado
            target_file = SOURCES_CONFLUENCE_DIR
            for part in path_parts:
                target_file = target_file / part
            target_file.mkdir(parents=True, exist_ok=True)
            file_dest = target_file / f"{slug}.md"

            # Se for editada e o arquivo anterior tinha outro nome/caminho, podemos sobrescrever
            file_dest.write_text(full_md, encoding="utf-8")

            # Upsert imediato no SQLite FTS5 da AURA
            resumo = ""
            for lin in markdown_body.split("\n"):
                lin_s = lin.strip()
                if len(lin_s) > 40 and not lin_s.startswith("#") and not lin_s.startswith(">"):
                    resumo = lin_s[:350].strip()
                    break
            if not resumo:
                resumo = f"Procedimento e manual do modulo {modulo}: {title}."

            tags_str = f"{slug}, {modulo}, {', '.join(labels)}, webposto, procedimento, tela, manual".lower()

            upsert_pagina_no_banco_aura(
                conn=conn_aura,
                page_id=page_id,
                modulo=modulo,
                titulo=title,
                subtitulo=path_hierarchy,
                resumo=resumo,
                corpo=full_md,
                tags=tags_str,
                meta=frontmatter
            )

            processadas += 1
            time.sleep(0.15)  # Respeito a rate limit da Atlassian

        except Exception as e:
            logger.error(f"Erro ao sincronizar pagina {page_id} ('{title}'): {e}")
            erros += 1

    # 5. Atualiza o checkpoint
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                chk = json.load(f)
        except Exception:
            chk = {}
    else:
        chk = {}

    chk["last_delta_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chk["total_found"] = len(remote_pages)
    chk["processed_ids"] = list(set(chk.get("processed_ids", []) + [str(p["page"]["id"]) for p in delta_pages]))
    chk["page_map"] = page_map

    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(chk, f, indent=2, ensure_ascii=False)

    conn_aura.close()

    logger.info("\n" + "=" * 70)
    logger.info(f"  SINCRONIZACAO CONCLUIDA COM SUCESSO:")
    logger.info(f"  • Paginas processadas e atualizadas no RAG AURA: {processadas}")
    logger.info(f"  • Erros ocorridos: {erros}")
    logger.info(f"  • Checkpoint atualizado em: {CHECKPOINT_PATH}")
    logger.info(f"  • Banco AURA atualizado em: {DB_PATH}")
    logger.info("=" * 70)


if __name__ == "__main__":
    sincronizar_delta_confluence()
