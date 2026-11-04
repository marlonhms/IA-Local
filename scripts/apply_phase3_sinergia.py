"""
Script de aplicacao da Fase 3 do Apendice C: Contrato Zero Repeticao no Backend e Prompts.
Repositorio: ia-banco-local
Regra estrita: ZERO travessoes Unicode (\u2014 e \u2013) em todo o codigo e comentarios.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def verify_no_unicode_dashes(path: Path) -> None:
    """Verifica que o arquivo nao possui nenhum travessao Unicode."""
    text = path.read_text(encoding="utf-8")
    c_em = text.count("\u2014")
    c_en = text.count("\u2013")
    if c_em > 0 or c_en > 0:
        raise ValueError(
            f"Arquivo {path} contem {c_em} em-dash e {c_en} en-dash proibidos!"
        )
    print(f"[OK] {path.name}: 0 travessoes Unicode encontrados.")


def update_system_prompts() -> None:
    """Atualiza system_prompts.py com a clausula estrita de Zero Repeticao."""
    prompts_path = BASE_DIR / "core" / "prompts" / "system_prompts.py"
    content = prompts_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. build_fiscal_audit_prompt
    old_fiscal_block = """  1. Diagnostico do Bloqueio: Explique com clareza a rejeicao SEFAZ ou erro fiscal e o impacto imediato no faturamento.
  2. Resolucao no webPosto: Diga exatamente onde e o que o operador deve ajustar na retaguarda.
  3. Direcionamento para a Intelligent UI: Avise o gestor que o card lateral traz os parametros completos da regra e o botao para copiar o parecer direto para o contador.
- REGRA CRITICA: NAO reproduza XMLs extensos nem listas exaustivas no chat. Mantenha o foco em destravar o faturamento e a operacao da pista."""

    new_fiscal_block = """  1. Diagnostico do Bloqueio: Explique com clareza a rejeicao SEFAZ ou erro fiscal e o impacto imediato no faturamento.
  2. Resolucao no webPosto: Diga exatamente onde e o que o operador deve ajustar na retaguarda.
  3. Direcionamento para a Intelligent UI: Avise o gestor que o card lateral traz os parametros completos da regra e o botao para copiar o parecer direto para o contador.
- REGRA ESTRITA DE ZERO REPETICAO: Quando o Companion Canvas estiver ativo, NUNCA descreva itens individuais, produtos linha por linha ou tabelas repetitivas no texto. Agrupe os fatos geradores pela causa raiz e convide o gestor a inspecionar os detalhes tabulares no Canvas.
- REGRA CRITICA: NAO reproduza XMLs extensos nem listas exaustivas no chat. Mantenha o foco em destravar o faturamento e a operacao da pista."""

    if old_fiscal_block in content_lf:
        content_lf = content_lf.replace(old_fiscal_block, new_fiscal_block, 1)
        print("[PROMPTS] 1. build_fiscal_audit_prompt atualizado com regra de zero repeticao.")
    else:
        print("[PROMPTS] 1. build_fiscal_audit_prompt ja estava atualizado.")

    # 2. build_system_prompt
    old_system_block = """  1. Diagnostico e Posicionamento: Exponha o veredito estrategico direto (gap de preco frente ao mercado municipal, status da operacao, volume em risco).
  2. Destaque Principal: Aponte o concorrente mais agressivo ou dado lider (ex: o posto mais barato da cidade e seu preco).
  3. Direcionamento para a Intelligent UI: Oriente o gestor para o painel interativo lateral onde o ranking completo, os indicadores confrontados e os botoes de acao (HITL) estao projetados.
- REGRA CRITICA: NAO repita listas de postos, tabelas exaustivas ou itens linha por linha no texto do chat quando a Intelligent UI estiver ativa. A densidade de dados e as acoes pertencem exclusivamente a tela da Intelligent UI."""

    new_system_block = """  1. Diagnostico e Posicionamento: Exponha o veredito estrategico direto (gap de preco frente ao mercado municipal, status da operacao, volume em risco).
  2. Destaque Principal: Aponte o concorrente mais agressivo ou dado lider (ex: o posto mais barato da cidade e seu preco).
  3. Direcionamento para a Intelligent UI: Oriente o gestor para o painel interativo lateral onde o ranking completo, os indicadores confrontados e os botoes de acao (HITL) estao projetados.
- REGRA ESTRITA DE ZERO REPETICAO: Quando o Companion Canvas estiver ativo, NUNCA descreva itens individuais, produtos linha por linha ou tabelas repetitivas no texto. Agrupe os fatos geradores pela causa raiz e convide o gestor a inspecionar os detalhes tabulares no Canvas.
- REGRA CRITICA: NAO repita listas de postos, tabelas exaustivas ou itens linha por linha no texto do chat quando a Intelligent UI estiver ativa. A densidade de dados e as acoes pertencem exclusivamente a tela da Intelligent UI."""

    if old_system_block in content_lf:
        content_lf = content_lf.replace(old_system_block, new_system_block, 1)
        print("[PROMPTS] 2. build_system_prompt atualizado com regra de zero repeticao.")
    else:
        print("[PROMPTS] 2. build_system_prompt ja estava atualizado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    prompts_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(prompts_path)


def update_aura_engine() -> None:
    """Atualiza aura_engine.py com clusterizacao causal em sinteses contingenciais e diretiva no contexto."""
    engine_path = BASE_DIR / "core" / "aura_engine.py"
    content = engine_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. Assinatura de _resolver_contexto_ferramenta
    old_sig = """    def _resolver_contexto_ferramenta(
        self,
        pergunta: str,
        intencao: str,
        query_vector: Optional[list] = None,
    ) -> Tuple[str, Any, Optional[Dict[str, Any]], bool, float]:"""

    new_sig = """    def _resolver_contexto_ferramenta(
        self,
        pergunta: str,
        intencao: str,
        query_vector: Optional[list] = None,
        genui_active: bool = False,
    ) -> Tuple[str, Any, Optional[Dict[str, Any]], bool, float]:"""

    if old_sig in content_lf:
        content_lf = content_lf.replace(old_sig, new_sig, 1)
        print("[ENGINE] 1. Assinatura de _resolver_contexto_ferramenta atualizada.")

    # 2. Chamada de _resolver_contexto_ferramenta no pipeline streaming
    old_call = """        (
            contexto_extra,
            resultado_bruto,
            telemetria_retrieval,
            cache_hit,
            tool_latency_ms,
        ) = await asyncio.to_thread(
            self._resolver_contexto_ferramenta,
            pergunta_efetiva,
            intencao,
            query_vector,
        )"""

    new_call = """        (
            contexto_extra,
            resultado_bruto,
            telemetria_retrieval,
            cache_hit,
            tool_latency_ms,
        ) = await asyncio.to_thread(
            self._resolver_contexto_ferramenta,
            pergunta_efetiva,
            intencao,
            query_vector,
            (genui_meta is not None and genui_active),
        )"""

    if old_call in content_lf:
        content_lf = content_lf.replace(old_call, new_call, 1)
        print("[ENGINE] 2. Chamada de _resolver_contexto_ferramenta atualizada no pipeline.")

    # 3. Diretiva Dual-Channel em _resolver_contexto_ferramenta para auditoria fiscal
    old_fiscal_ctx = """            elif intencao in ("auditoria_fiscal_sefaz", "conhecimento_fiscal", "fiscal_sefaz"):
                resultado_bruto = self.tools.auditar_documento_ou_chave_fiscal(pergunta)
                contexto_extra = (
                    "Auditoria Fiscal e Diagnostico Especialista SEFAZ (Agent Sefaz + webPosto RAG):\\n"
                    f"{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\\n"
                )"""

    new_fiscal_ctx = """            elif intencao in ("auditoria_fiscal_sefaz", "conhecimento_fiscal", "fiscal_sefaz"):
                resultado_bruto = self.tools.auditar_documento_ou_chave_fiscal(pergunta)
                directive = ""
                if genui_active:
                    directive = (
                        "\\n[DIRETIVA DUAL-CHANNEL ATIVA]: O Companion Canvas esta ativo ao lado. "
                        "NUNCA descreva itens individuais, produtos linha por linha ou tabelas repetitivas no texto. "
                        "Agrupe os fatos geradores pela causa raiz e convide o gestor a inspecionar os detalhes tabulares no Canvas.\\n"
                    )
                contexto_extra = (
                    f"Auditoria Fiscal e Diagnostico Especialista SEFAZ (Agent Sefaz + webPosto RAG):{directive}\\n"
                    f"{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\\n"
                )"""

    if old_fiscal_ctx in content_lf:
        content_lf = content_lf.replace(old_fiscal_ctx, new_fiscal_ctx, 1)
        print("[ENGINE] 3. Diretiva Dual-Channel inserida em contexto_extra fiscal.")

    # 4. _gerar_sintese_contingencia_ferramenta para xml_documento com clusterizacao causal
    old_xml_sintese = """                if genui_active:
                    return (
                        f"### Auditoria de Documento XML ({status_badge})\\n\\n"
                        f"Documento Modelo {res.get('modelo', '55')} (rota {res.get('emit_uf', 'SP')} -> {res.get('dest_uf', 'SP')}): {conclusao}\\n\\n"
                        "- **Resolucao e Parecer:** Os apontamentos detalhados da SEFAZ e o parecer para o contador estao no **painel lateral**."
                    )"""

    new_xml_sintese = """                if genui_active:
                    # FASE 3: Contrato Zero Repeticao (Sintese Representativa e Observavel por Causa Raiz)
                    # NUNCA lista produtos linha por linha ou itens individuais no texto do chat
                    linhas = [
                        f"### Auditoria de Documento XML ({status_badge})",
                        "",
                    ]
                    # 1. Veredito macro
                    if erros > 0:
                        linhas.append(
                            f"Documento Modelo {res.get('modelo', '55')} (rota {res.get('emit_uf', 'SP')} -> {res.get('dest_uf', 'SP')}) "
                            f"bloqueado com **{erros} inconsistencia(s) impeditiva(s)** de autorizacao SEFAZ."
                        )
                    elif alertas > 0:
                        linhas.append(
                            f"Documento Modelo {res.get('modelo', '55')} (rota {res.get('emit_uf', 'SP')} -> {res.get('dest_uf', 'SP')}) "
                            f"autorizavel perante a SEFAZ, com **{alertas} alerta(s) de conformidade tributaria**."
                        )
                    else:
                        linhas.append(
                            f"Documento Modelo {res.get('modelo', '55')} (rota {res.get('emit_uf', 'SP')} -> {res.get('dest_uf', 'SP')}) "
                            "em **total conformidade fiscal** perante regras SEFAZ MOC 7.0 e SPED."
                        )

                    linhas.append("")

                    # 2. Causa Raiz Geral (clusterizada)
                    aponts = res.get("apontamentos", [])
                    causas = []
                    has_neg = any(
                        a.get("status") == "INVALID" and (
                            "negativo" in (a.get("titulo") or "").lower() or
                            "negativo" in (a.get("explicacao_executiva") or "").lower()
                        ) for a in aponts
                    )
                    has_prot = any(
                        "protocolo" in (a.get("titulo") or "").lower() or
                        "protocolo" in (a.get("explicacao_executiva") or "").lower()
                        for a in aponts
                    )
                    has_cst = any(
                        "cst" in (a.get("titulo") or "").lower() or
                        "aliquota" in (a.get("explicacao_executiva") or "").lower()
                        for a in aponts
                    )

                    if has_neg:
                        causas.append("Descontos comerciais de aplicativo ou abatimentos foram declarados incorretamente como acrescimo negativo em campo nao permitido pelo MOC.")
                    if has_prot:
                        causas.append("Ausencia de protocolo de autorizacao valido ou lote pendente de processamento no ambiente autorizador.")
                    if has_cst:
                        causas.append("Divergencia entre regime tributario monofasico e aliquotas declaradas nos itens de combustiveis.")
                    if not causas and (erros > 0 or alertas > 0):
                        top_apont = aponts[0] if aponts else {}
                        causas.append(top_apont.get("explicacao_executiva") or "Inconformidades de validacao estrutural ou regras de negocio SEFAZ.")

                    if causas:
                        linhas.append(f"- **Causa Raiz Geral:** {' '.join(causas)}")

                    # 3. Resolucao no ERP webPosto
                    if has_neg:
                        linhas.append("- **Resolucao no webPosto:** Acesse **Faturamento > Notas Fiscais**, localize o documento e mova os valores para o campo oficial de Desconto (`vDesc`), evitando acrescimos negativos.")
                    elif has_prot:
                        linhas.append("- **Resolucao no webPosto:** Acesse **Faturamento > Monitor SEFAZ**, execute Consulta de Lote ou retransmita o documento apos restabelecer a comunicacao.")
                    elif erros > 0:
                        linhas.append("- **Resolucao no webPosto:** Acesse **Faturamento > Notas Fiscais**, ajuste as regras tributarias dos itens indicados e revalide o documento.")
                    else:
                        linhas.append("- **Status Operacional:** Nenhuma correcao necessaria na retaguarda do webPosto.")

                    # 4. Ponte Contextual para o Canvas
                    if erros > 0 or alertas > 0:
                        qtd_itens = len(aponts)
                        linhas.append(
                            f"- **Ponte Contextual:** A matriz detalhada com os {qtd_itens} apontamento(s) individualizado(s), "
                            "o totalizador de impacto e o parecer tecnico para o contador estao no **painel lateral** (Canvas)."
                        )
                    else:
                        linhas.append("- **Ponte Contextual:** O espelho fiscal e a chave de acesso estao disponiveis no **painel lateral** (Canvas).")

                    return "\\n".join(linhas)"""

    if old_xml_sintese in content_lf:
        content_lf = content_lf.replace(old_xml_sintese, new_xml_sintese, 1)
        print("[ENGINE] 4. Sintese contingencial de xml_documento clusterizada com 4 blocos.")
    else:
        print("[ENGINE] 4. Sintese contingencial de xml_documento ja estava atualizada.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    engine_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(engine_path)


if __name__ == "__main__":
    print("Iniciando aplicacao da Fase 3...")
    update_system_prompts()
    update_aura_engine()
    print("Fase 3 aplicada com sucesso!")
