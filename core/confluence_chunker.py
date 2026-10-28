"""
Motor de Chunking Estrutural para Documentos do Confluence (core/confluence_chunker.py).
Roadmap Apendice: roadmap_apendice_conhecimento_multicamada_rag.md (Secao 6)

Regras do Chunker:
1. Unidade estrutural primeiro: divisao por cabecalhos Markdown (#, ##, ###)
2. Janela alvo de 500 a 900 tokens por chunk; maximo absoluto de 1.100 tokens
3. Sobreposicao (overlap) de 10-15% (aprox. 80 tokens) estritamente dentro da mesma secao
4. Preservacao de tabelas estruturadas (com repeticao de cabecalho se dividida) e passos numerados
5. Fusao de chunks pequenos (<120 tokens) com o vizinho da mesma secao
6. Descarte inteligente de hubs nao-procedimentais (HUB-MODULO-*) e paginas vazias
7. Prefixo contextual obrigatorio em 'conteudo_embed': [{breadcrumb}] [Secao: {secao}]

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import re
import yaml
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class ConfluenceChunk:
    doc_id: str
    doc_titulo: str
    doc_url: Optional[str]
    doc_versao: Optional[int]
    breadcrumb: str
    secao: str
    chunk_idx: int
    chunk_total: int
    conteudo: str
    conteudo_embed: str
    n_tokens: int
    hash_md5: str
    camada: str = "erp"
    vertical: Optional[str] = "posto"
    erp: Optional[str] = "webposto"
    tenant_id: str = "posto_local"
    status: str = "ativo"
    fonte: str = "confluence"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_titulo": self.doc_titulo,
            "doc_url": self.doc_url,
            "doc_versao": self.doc_versao,
            "breadcrumb": self.breadcrumb,
            "secao": self.secao,
            "chunk_idx": self.chunk_idx,
            "chunk_total": self.chunk_total,
            "conteudo": self.conteudo,
            "conteudo_embed": self.conteudo_embed,
            "n_tokens": self.n_tokens,
            "hash_md5": self.hash_md5,
            "camada": self.camada,
            "vertical": self.vertical,
            "erp": self.erp,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "fonte": self.fonte,
        }

class ConfluenceChunker:
    """Segmentador semantico de alta fidelidade para base de conhecimento operacional."""

    TARGET_MIN_TOKENS = 120
    TARGET_IDEAL_TOKENS = 700
    TARGET_MAX_TOKENS = 900
    HARD_LIMIT_TOKENS = 1100
    OVERLAP_TOKENS = 80

    # Palavras-chave que indicam conteudo procedimental util
    PROCEDURAL_TERMS = {
        "acesse", "clique", "selecione", "menu", "modulo", "tela", "botao",
        "salvar", "cadastro", "entrada", "saida", "campo", "configurar",
        "emitir", "cancelar", "fechamento", "caixa", "conferencia", "pdv",
        "passo", "procedimento", "como", "relatorio", "nota", "fiscal", "sefaz"
    }

    def __init__(self):
        pass

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimativa precisa de tokens para portugues (media BPE Gemini/Llama).
        Combina contagem de palavras e comprimento de caracteres.
        """
        if not text:
            return 0
        words = len(text.split())
        chars = len(text)
        # 1 palavra em pt-br costuma equivaler a ~1.3 tokens
        # 1 token costuma ter ~3.8 a 4.2 caracteres
        return max(1, int(max(words * 1.3, chars / 3.9)))

    @staticmethod
    def clean_markdown(raw_text: str) -> str:
        """Remove macros sem valor do Confluence e higieniza a formatacao."""
        if not raw_text:
            return ""

        text = raw_text

        # 1. Remove macros de TOC / CODE vazias do Confluence
        text = re.sub(r">\s*\*\*TOC:\*\*\s*>", "", text)
        text = re.sub(r">\s*\*\*CODE:\*\*\s*>", "", text)

        # 2. Remove sintaxe de anexos/imagens Confluence
        text = re.sub(r"![a-zA-Z0-9_\-\.]+\.(?:png|jpg|jpeg|gif|webp|svg)!", "", text)
        text = re.sub(r"!worddav[a-zA-Z0-9_]+!", "", text)

        # 3. Remove emoticons tipicos do Confluence
        text = re.sub(r"\((?:warning|info|flag|check|error|plus|minus)\)", "", text)

        # 4. Remove tags HTML residuais
        text = re.sub(r"<\/?(?:p|div|span|br|b|i|u|strong|em)[^>]*>", " ", text)
        text = text.replace("&nbsp;", " ")

        # 5. Normaliza linhas horizontais avulsas (---)
        text = re.sub(r"\n\s*---\s*\n", "\n\n", text)

        # 6. Normaliza quebras de linha excessivas
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        """Extrai cabecalho YAML se presente no inicio do markdown."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if match:
            fm_text = match.group(1)
            body = text[match.end():]
            try:
                fm = yaml.safe_load(fm_text) or {}
                return fm, body
            except Exception:
                # Fallback por regex se yaml falhar
                fm = {}
                for line in fm_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip().strip("'\"")
                return fm, body
        return {}, text

    def is_procedural_document(self, doc_data: Dict[str, Any], body: str) -> bool:
        """Determina se o documento e um guia procedimental ou apenas um indice/tracker."""
        codigo_ref = str(doc_data.get("codigo_ref") or "")
        
        # 1. Ignora explicitamente trackers/hubs do Jira
        if codigo_ref.startswith("HUB-"):
            return False

        # 2. Ignora paginas vazias
        clean_body = re.sub(r"\s+", "", body)
        if len(clean_body) < 80:
            return False

        # 3. Verifica presenca de termos procedimentais
        body_lower = body.lower()
        matched_terms = sum(1 for term in self.PROCEDURAL_TERMS if term in body_lower)
        if matched_terms < 1 and len(clean_body) < 250:
            return False

        return True

    def split_into_sections(self, body: str, doc_titulo: str) -> List[Tuple[str, str]]:
        """
        Divide o texto com base nos cabecalhos Markdown (#, ##, ###, ####).
        Retorna lista de tuplas (titulo_da_secao, conteudo_da_secao).
        """
        lines = body.split("\n")
        sections: List[Tuple[str, List[str]]] = []
        current_section = doc_titulo or "Introducao"
        current_lines: List[str] = []

        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            match = header_pattern.match(line.strip())
            if match:
                # Salva secao anterior se tiver conteudo
                if current_lines:
                    text_sec = "\n".join(current_lines).strip()
                    if text_sec:
                        sections.append((current_section, current_lines))
                    current_lines = []
                
                header_title = match.group(2).strip()
                # Remove asteriscos ou marcacoes do titulo do cabecalho
                header_title = re.sub(r"[\*_]+", "", header_title).strip()
                current_section = header_title or doc_titulo
            else:
                current_lines.append(line)

        if current_lines:
            text_sec = "\n".join(current_lines).strip()
            if text_sec:
                sections.append((current_section, current_lines))

        # Se nao encontrou nenhum cabecalho, retorna o corpo inteiro
        if not sections and body.strip():
            sections.append((doc_titulo or "Geral", lines))

        return [(sec_title, "\n".join(sec_lines).strip()) for sec_title, sec_lines in sections]

    def _split_table(self, lines: List[str], max_tokens: int) -> List[str]:
        """Divide uma tabela markdown grande preservando cabecalho em todas as partes."""
        preamble: List[str] = []
        table_rows: List[str] = []
        in_table = False

        for l in lines:
            stripped = l.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                in_table = True
                table_rows.append(stripped)
            elif not in_table:
                preamble.append(l)

        if len(table_rows) < 3:
            return ["\n".join(lines)]

        header = table_rows[0]
        separator = table_rows[1]
        data_rows = table_rows[2:]

        chunks: List[str] = []
        current_rows: List[str] = []
        preamble_text = "\n".join(preamble).strip()

        for row in data_rows:
            test_content = header + "\n" + separator + "\n" + "\n".join(current_rows + [row])
            if not chunks and preamble_text:
                test_content = preamble_text + "\n\n" + test_content

            if self.estimate_tokens(test_content) > max_tokens and current_rows:
                part = header + "\n" + separator + "\n" + "\n".join(current_rows)
                if not chunks and preamble_text:
                    part = preamble_text + "\n\n" + part
                chunks.append(part)
                current_rows = [row]
            else:
                current_rows.append(row)

        if current_rows:
            part = header + "\n" + separator + "\n" + "\n".join(current_rows)
            if not chunks and preamble_text:
                part = preamble_text + "\n\n" + part
            chunks.append(part)

        return chunks

    def subdivide_section_content(
        self,
        section_title: str,
        section_text: str,
        doc_titulo: str
    ) -> List[str]:
        """
        Subdivide secoes que excedem a janela ideal (900 tokens).
        Respeita tabelas, passos numerados e listas. Aplica sobreposicao de ~80 tokens.
        """
        total_tokens = self.estimate_tokens(section_text)
        if total_tokens <= self.TARGET_MAX_TOKENS:
            return [section_text]

        # Verifica se e primariamente uma tabela
        lines = section_text.split("\n")
        table_lines = [l for l in lines if l.strip().startswith("|") and l.strip().endswith("|")]
        if len(table_lines) > 5 and len(table_lines) >= len(lines) * 0.6:
            return self._split_table(lines, self.TARGET_MAX_TOKENS)

        # Divisao por blocos logicos (passos, itens de lista ou paragrafos duplos)
        blocks = re.split(r"\n(?=\d+[\.\)]\s+|\*\s+|\-\s+|\n)", section_text)
        blocks = [b.strip() for b in blocks if b.strip()]

        if not blocks:
            # Fallback por paragrafos simples
            blocks = [p.strip() for p in section_text.split("\n\n") if p.strip()]

        chunks: List[str] = []
        current_chunk_parts: List[str] = []
        current_tokens = 0

        for block in blocks:
            b_tokens = self.estimate_tokens(block)

            # Se um unico bloco for gigantesco (ex: texto sem quebras), divide em frases
            if b_tokens > self.TARGET_MAX_TOKENS:
                sentences = re.split(r"(?<=[.!?])\s+", block)
                for sent in sentences:
                    s_tokens = self.estimate_tokens(sent)
                    if current_tokens + s_tokens > self.TARGET_MAX_TOKENS and current_chunk_parts:
                        chunks.append("\n\n".join(current_chunk_parts).strip())
                        # Aplica overlap pegando a ultima sentenca
                        overlap_text = current_chunk_parts[-1] if self.estimate_tokens(current_chunk_parts[-1]) <= self.OVERLAP_TOKENS else ""
                        current_chunk_parts = [overlap_text, sent] if overlap_text else [sent]
                        current_tokens = self.estimate_tokens("\n\n".join(current_chunk_parts))
                    else:
                        current_chunk_parts.append(sent)
                        current_tokens += s_tokens
                continue

            if current_tokens + b_tokens > self.TARGET_MAX_TOKENS and current_chunk_parts:
                full_chunk = "\n\n".join(current_chunk_parts).strip()
                chunks.append(full_chunk)

                # Gera overlap pegando o ultimo item
                last_item = current_chunk_parts[-1]
                if self.estimate_tokens(last_item) <= self.OVERLAP_TOKENS:
                    current_chunk_parts = [last_item, block]
                else:
                    current_chunk_parts = [block]
                current_tokens = self.estimate_tokens("\n\n".join(current_chunk_parts))
            else:
                current_chunk_parts.append(block)
                current_tokens += b_tokens

        if current_chunk_parts:
            chunks.append("\n\n".join(current_chunk_parts).strip())

        return chunks

    def merge_small_chunks(self, raw_chunks: List[str]) -> List[str]:
        """Funde chunks com menos de TARGET_MIN_TOKENS com o vizinho se couberem."""
        if len(raw_chunks) <= 1:
            return raw_chunks

        merged: List[str] = []
        buffer_text = ""

        for ch in raw_chunks:
            if not buffer_text:
                buffer_text = ch
                continue

            buf_tokens = self.estimate_tokens(buffer_text)
            ch_tokens = self.estimate_tokens(ch)

            if buf_tokens < self.TARGET_MIN_TOKENS and (buf_tokens + ch_tokens <= self.TARGET_MAX_TOKENS):
                buffer_text = buffer_text + "\n\n" + ch
            else:
                merged.append(buffer_text)
                buffer_text = ch

        if buffer_text:
            # Se o ultimo pedaco sobrou pequeno, tenta anexar ao anterior
            if merged and self.estimate_tokens(buffer_text) < self.TARGET_MIN_TOKENS:
                last_tokens = self.estimate_tokens(merged[-1])
                if last_tokens + self.estimate_tokens(buffer_text) <= self.HARD_LIMIT_TOKENS:
                    merged[-1] = merged[-1] + "\n\n" + buffer_text
                else:
                    merged.append(buffer_text)
            else:
                merged.append(buffer_text)

        return merged

    def chunk_document(self, doc_data: Dict[str, Any]) -> List[ConfluenceChunk]:
        """
        Processa um documento bruto do Confluence e gera a lista de chunks padronizados.
        Retorna lista vazia se o documento for nao-procedimental ou descartavel.
        """
        raw_content = doc_data.get("conteudo_completo") or ""
        if not raw_content.strip():
            return []

        doc_id = str(doc_data.get("codigo_ref") or "DOC-DESCONHECIDO")
        doc_titulo = str(doc_data.get("titulo") or "").strip()
        modulo = str(doc_data.get("modulo") or "").strip()

        # 1. Extrai cabecalho YAML se presente
        frontmatter, body = self.extract_frontmatter(raw_content)

        # 2. Higieniza corpo Markdown
        clean_body = self.clean_markdown(body)

        # 3. Valida se o documento e procedimental
        if not self.is_procedural_document(doc_data, clean_body):
            return []

        # 4. Resolve metadados contextuais
        breadcrumb = (
            frontmatter.get("path_hierarquia")
            or f"{modulo} > {doc_titulo}"
            if modulo and modulo != doc_titulo
            else doc_titulo
        )
        # Normaliza nomes de sistema no breadcrumb para manter consistencia
        breadcrumb = breadcrumb.replace("webPosto", "Seu ERP").replace("webposto", "Seu ERP")

        doc_url = frontmatter.get("url") or None
        doc_versao = frontmatter.get("versao")
        if doc_versao is not None:
            try:
                doc_versao = int(doc_versao)
            except Exception:
                doc_versao = None

        # 5. Divide em secoes estruturais por cabecalho
        raw_sections = self.split_into_sections(clean_body, doc_titulo)

        # 5.1. Funde preambulos/secoes introdutorias minusculas (< 100 tokens) na secao seguinte
        if len(raw_sections) > 1:
            first_name, first_text = raw_sections[0]
            first_tokens = self.estimate_tokens(first_text)
            if first_tokens < 100:
                next_name, next_text = raw_sections[1]
                combined_text = f"{first_text}\n\n{next_text}".strip()
                raw_sections = [(next_name, combined_text)] + raw_sections[2:]

        # 6. Subdivide secoes grandes e funde secoes minusculas
        prepared_chunks: List[Tuple[str, str]] = []  # (secao_nome, conteudo)

        for sec_name, sec_text in raw_sections:
            sub_parts = self.subdivide_section_content(sec_name, sec_text, doc_titulo)
            sub_parts = self.merge_small_chunks(sub_parts)
            for part in sub_parts:
                prepared_chunks.append((sec_name, part))

        # 6.1. Passada final de fusao inter-secoes para chunks residuais que ficaram < TARGET_MIN_TOKENS
        if len(prepared_chunks) > 1:
            merged_final: List[Tuple[str, str]] = []
            for sec_name, part_text in prepared_chunks:
                if not merged_final:
                    merged_final.append((sec_name, part_text))
                    continue
                
                prev_name, prev_text = merged_final[-1]
                prev_tokens = self.estimate_tokens(prev_text)
                curr_tokens = self.estimate_tokens(part_text)

                if prev_tokens < self.TARGET_MIN_TOKENS and (prev_tokens + curr_tokens <= self.HARD_LIMIT_TOKENS):
                    # Funde o anterior pequeno no atual
                    merged_final[-1] = (sec_name, prev_text + "\n\n" + part_text)
                elif curr_tokens < self.TARGET_MIN_TOKENS and (prev_tokens + curr_tokens <= self.TARGET_MAX_TOKENS):
                    # Funde o atual pequeno no anterior
                    merged_final[-1] = (prev_name, prev_text + "\n\n" + part_text)
                else:
                    merged_final.append((sec_name, part_text))
            prepared_chunks = merged_final

        if not prepared_chunks:
            return []

        # 7. Constroi os objetos ConfluenceChunk finais com prefixo contextual
        total_chunks = len(prepared_chunks)
        results: List[ConfluenceChunk] = []

        for idx, (sec_name, part_text) in enumerate(prepared_chunks):
            # Prefixo contextual: essencial para o embedding compreender a origem sem alucinacao
            contextual_prefix = f"[{breadcrumb}] [Secao: {sec_name}]\n"
            conteudo_embed = contextual_prefix + part_text
            
            n_tokens = self.estimate_tokens(conteudo_embed)
            
            # Trava rigida de seguranca: nunca permite exceder HARD_LIMIT_TOKENS
            if n_tokens > self.HARD_LIMIT_TOKENS:
                # Truncamento de contingencia por caracteres
                max_chars = self.HARD_LIMIT_TOKENS * 3
                part_text = part_text[:max_chars]
                conteudo_embed = contextual_prefix + part_text
                n_tokens = self.estimate_tokens(conteudo_embed)

            hash_md5 = hashlib.md5(conteudo_embed.encode("utf-8")).hexdigest()

            results.append(
                ConfluenceChunk(
                    doc_id=doc_id,
                    doc_titulo=doc_titulo,
                    doc_url=doc_url,
                    doc_versao=doc_versao,
                    breadcrumb=breadcrumb,
                    secao=sec_name,
                    chunk_idx=idx,
                    chunk_total=total_chunks,
                    conteudo=part_text,
                    conteudo_embed=conteudo_embed,
                    n_tokens=n_tokens,
                    hash_md5=hash_md5,
                    camada="erp",
                    vertical="posto",
                    erp="webposto",
                    tenant_id="posto_local",
                    status="ativo",
                    fonte="confluence",
                )
            )

        return results
