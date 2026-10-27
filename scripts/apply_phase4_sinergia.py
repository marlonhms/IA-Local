"""
Script de aplicacao da Fase 4 do Apendice C: Limpeza da Redundancia Interna no Canvas.
Repositorio: ia-banco-local
Regra estrita: ZERO travessoes Unicode (\u2014 e \u2013) em todo o codigo e comentarios.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DIST_WEB_DIR = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"


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


def update_aura_engine() -> None:
    """Atualiza build_canonical_genui_envelope em aura_engine.py para eliminar duplicidade de gestorText."""
    engine_path = BASE_DIR / "core" / "aura_engine.py"
    content = engine_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    old_persona_block = """            textos_gestor = []
            textos_contador = []
            bases_legais = []
            for a in apontamentos:
                reg_id = a.get("regra_id", "")
                # Se for codigo generico de validacao interna sem valor legal (ex: SEFAZ-VAL-NEG), omite a tag interna
                is_generico = bool(re.match(r"^SEFAZ-(VAL-NEG|W\d|I\d|CHAVE-LEN|CHAVE-01)", reg_id))
                prefixo = f"• [{reg_id}]: " if (reg_id and not is_generico) else "• "
                if a.get("explicacao_executiva"):
                    textos_gestor.append(f"{prefixo}{a.get('explicacao_executiva')}")
                if a.get("explicacao_tecnica"):
                    textos_contador.append(f"{prefixo}{a.get('explicacao_tecnica')}")
                for bl in (a.get("base_legal") or []):
                    if bl not in bases_legais:
                        bases_legais.append(bl)

            persona_views = {
                "gestor": "\\n".join(textos_gestor) if textos_gestor else "Nenhuma rejeicao ou inconformidade encontrada no documento.",
                "contador": "\\n".join(textos_contador) if textos_contador else "Documento validado com sucesso perante regras estruturais e de negocio.",
                "base_legal": bases_legais if bases_legais else ["MOC 7.0", "NT SEFAZ"],
            }
            props["persona_views"] = persona_views"""

    new_persona_block = """            # FASE 4: Limpeza da Redundancia Interna no Canvas (Card Resumo de Impacto da Pista)
            # Remove a repeticao em lista de todas as explicacoes executivas que ja aparecem nos cards abaixo
            regras_nao_genericas = [
                a.get("regra_id", "") for a in apontamentos
                if a.get("regra_id") and not re.match(r"^SEFAZ-(VAL-NEG|W\\d|I\\d|CHAVE-LEN|CHAVE-01)", a.get("regra_id", ""))
            ]
            regras_ref = f" [{', '.join(regras_nao_genericas)}]" if regras_nao_genericas else ""

            if invalidos:
                gestor_text = (
                    f"Impacto na Operacao: Documento bloqueado com {len(invalidos)} apontamento(s) impeditivo(s){regras_ref}. "
                    "Faturamento retido no PDV/webPosto. Resolucao guiada indicada nos cards abaixo."
                )
            elif alertas:
                gestor_text = (
                    f"Impacto na Operacao: Documento autorizavel com {len(alertas)} alerta(s) tributario(s){regras_ref}. "
                    "Nao ha retencao imediata na pista, porem requer regularizacao cadastral na retaguarda."
                )
            else:
                gestor_text = "Impacto na Operacao: Documento 100% conforme. Faturamento e emissao liberados perante a SEFAZ."

            bases_legais = []
            textos_contador = []
            for a in apontamentos:
                reg_id = a.get("regra_id", "")
                is_generico = bool(re.match(r"^SEFAZ-(VAL-NEG|W\d|I\d|CHAVE-LEN|CHAVE-01)", reg_id))
                prefixo = f"• [{reg_id}]: " if (reg_id and not is_generico) else "• "
                if a.get("explicacao_tecnica"):
                    textos_contador.append(f"{prefixo}{a.get('explicacao_tecnica')}")
                for bl in (a.get("base_legal") or []):
                    if bl not in bases_legais:
                        bases_legais.append(bl)

            persona_views = {
                "gestor": gestor_text,
                "contador": "\\n".join(textos_contador) if textos_contador else "Documento validado com sucesso perante regras estruturais e de negocio.",
                "base_legal": bases_legais if bases_legais else ["MOC 7.0", "NT SEFAZ"],
                "faturamento_status": "Bloqueado para Autorizacao SEFAZ" if invalidos else ("Sob Alerta Tributario" if alertas else "Faturamento Liberado"),
                "tempo_retencao": "~3 a 5 min na pista" if invalidos else ("Sem retencao imediata" if alertas else "0 min"),
            }
            props["persona_views"] = persona_views"""

    if old_persona_block in content_lf:
        content_lf = content_lf.replace(old_persona_block, new_persona_block, 1)
        print("[ENGINE] persona_views atualizado para Card Resumo de Impacto da Pista.")
    else:
        print("[ENGINE] persona_views ja estava atualizado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    engine_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(engine_path)


def update_genui_widgets() -> None:
    """Atualiza FiscalShieldInspectorUI e fiscal_findings_list em aura-genui-widgets.js."""
    widgets_path = WEB_DIR / "js" / "aura-genui-widgets.js"
    content = widgets_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. renderLayer1 de FiscalShieldInspectorUI
    old_l1 = """          <!-- Painel Visao Gestor -->
          <div class="persona-view-panel persona-view-gestor ${this.activePersona === 'gestor' ? '' : 'hidden'} p-3 rounded-xl bg-slate-950/50 border border-emerald-500/20 space-y-1.5 animate-fade-in">
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-emerald-400 font-bold uppercase">${escapeHtml(subtitle)}</span>
              <span class="text-emerald-400/80">Operacao &amp; Acao Imediata</span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed whitespace-pre-line">
              ${formatFiscalHighlightText(gestorText, 'emerald')}
            </p>
          </div>

          <!-- Painel Visao Contador -->
          <div class="persona-view-panel persona-view-contador ${this.activePersona === 'contador' ? '' : 'hidden'} p-3 rounded-xl bg-slate-950/50 border border-cyan-500/20 space-y-1.5 animate-fade-in">
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-cyan-400 font-bold uppercase">${escapeHtml(subtitle)}</span>
              <span class="text-cyan-400/80">MOC 7.0 &amp; EFD / SPED Fiscal</span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed whitespace-pre-line">
              ${formatFiscalHighlightText(contadorText, 'cyan')}
            </p>
            ${basesLegais.length > 0 ? `
              <div class="pt-2 border-t border-white/5 flex flex-wrap gap-1.5">
                <span class="text-[10px] font-mono text-slate-400">Base Legal:</span>
                ${basesLegais.map(bl => `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">${escapeHtml(bl)}</span>`).join('')}
              </div>
            ` : ''}
          </div>"""

    new_l1 = """          <!-- Painel Visao Gestor: Card Resumo de Impacto da Pista (Apendice C - Fase 4) -->
          <div class="persona-view-panel persona-view-gestor ${this.activePersona === 'gestor' ? '' : 'hidden'} p-3.5 rounded-xl bg-slate-950/60 border border-emerald-500/30 space-y-2.5 animate-fade-in">
            <div class="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1.5">
              <span class="text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                <span>⛽</span>
                <span>Resumo de Impacto na Pista &amp; Faturamento</span>
              </span>
              <span class="text-emerald-400/90 font-semibold px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/30">
                Operacao Direta
              </span>
            </div>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-sans">
              <div class="p-2.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-0.5">
                <span class="text-[10px] text-slate-400 font-mono uppercase">Impacto no Faturamento:</span>
                <p class="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full ${personaViews.faturamento_status && personaViews.faturamento_status.toLowerCase().includes('bloqueado') ? 'bg-rose-400 animate-pulse' : 'bg-emerald-400'}"></span>
                  <span>${escapeHtml(personaViews.faturamento_status || 'Operacao Normal')}</span>
                </p>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-0.5">
                <span class="text-[10px] text-slate-400 font-mono uppercase">Tempo Estimado na Pista:</span>
                <p class="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span>⏱</span>
                  <span>${escapeHtml(personaViews.tempo_retencao || '0 min')}</span>
                </p>
              </div>
            </div>

            <p class="text-xs text-slate-300 leading-relaxed font-sans">
              ${formatFiscalHighlightText(gestorText, 'emerald')}
            </p>
          </div>

          <!-- Painel Visao Contador: Auditoria Tecnica MOC 7.0 & SPED -->
          <div class="persona-view-panel persona-view-contador ${this.activePersona === 'contador' ? '' : 'hidden'} p-3.5 rounded-xl bg-slate-950/60 border border-cyan-500/30 space-y-2.5 animate-fade-in">
            <div class="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1.5">
              <span class="text-cyan-400 font-bold uppercase flex items-center gap-1.5">
                <span>💻</span>
                <span>Auditoria Tecnica MOC 7.0 &amp; EFD / SPED Fiscal</span>
              </span>
              <span class="text-cyan-400/90 font-semibold px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30">
                Escrituracao Contabil
              </span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed whitespace-pre-line">
              ${formatFiscalHighlightText(contadorText, 'cyan')}
            </p>
            ${basesLegais.length > 0 ? `
              <div class="pt-2 border-t border-white/5 flex flex-wrap gap-1.5 items-center">
                <span class="text-[10px] font-mono text-slate-400">Base Legal:</span>
                ${basesLegais.map(bl => `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">${escapeHtml(bl)}</span>`).join('')}
              </div>
            ` : ''}
          </div>"""

    if old_l1 in content_lf:
        content_lf = content_lf.replace(old_l1, new_l1, 1)
        print("[WIDGETS] 1. renderLayer1 de FiscalShieldInspectorUI atualizado.")
    else:
        print("[WIDGETS] 1. renderLayer1 ja estava atualizado.")

    # 2. fiscal_findings_list adaptativo por persona
    old_finding_item = """                <div class="p-3.5 rounded-xl border ${cardBorderClass} transition-all space-y-2">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 flex-1 space-y-0.5">
                      <h5 class="text-xs sm:text-sm font-semibold text-slate-100 leading-snug">
                        ${escapeHtml(cleanTit)}
                      </h5>
                      ${ruleCode ? `
                        <div class="text-[10px] text-slate-400 font-mono">
                          Regra: ${escapeHtml(ruleCode)}
                        </div>
                      ` : ''}
                    </div>
                    <div class="text-right flex-shrink-0">
                      ${statusBtnHtml}
                    </div>
                  </div>

                  ${execMsg ? `
                    <p class="text-xs text-slate-300 leading-relaxed font-mono font-normal">
                      ${escapeHtml(execMsg)}
                    </p>
                  ` : ''}

                  ${fields.length > 0 ? `
                    <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                      <span class="text-slate-500">Campos XML:</span>
                      ${fields.map(f => `<span class="bg-slate-900 px-1.5 py-0.5 rounded border border-white/5 text-slate-300">${escapeHtml(f)}</span>`).join('')}
                    </div>
                  ` : ''}

                  ${acaoMsg ? `
                    <div class="p-2.5 rounded-lg bg-cyan-950/40 border border-cyan-500/20 text-xs text-cyan-200 flex items-start gap-2">
                      <span class="text-cyan-400 flex-shrink-0 text-sm">💡</span>
                      <div class="leading-relaxed">
                        <strong class="text-cyan-300 font-semibold">Como resolver no webPosto: </strong>
                        <span>${escapeHtml(acaoMsg)}</span>
                      </div>
                    </div>
                  ` : ''}
                </div>"""

    new_finding_item = """                <div class="p-3.5 rounded-xl border ${cardBorderClass} transition-all space-y-2">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 flex-1 space-y-0.5">
                      <h5 class="text-xs sm:text-sm font-semibold text-slate-100 leading-snug">
                        ${escapeHtml(cleanTit)}
                      </h5>
                      ${ruleCode ? `
                        <div class="text-[10px] text-slate-400 font-mono">
                          Regra: ${escapeHtml(ruleCode)}
                        </div>
                      ` : ''}
                    </div>
                    <div class="text-right flex-shrink-0">
                      ${statusBtnHtml}
                    </div>
                  </div>

                  <!-- FASE 4: Visualizacao Diferenciada por Persona (Gestor vs. Contador) -->
                  <!-- Modo Gestor (Foco de Pista & Destravamento) -->
                  <div class="finding-view-gestor space-y-2">
                    ${execMsg ? `
                      <p class="text-xs text-slate-300 leading-relaxed font-sans">
                        ${escapeHtml(execMsg)}
                      </p>
                    ` : ''}
                    ${acaoMsg ? `
                      <div class="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-200 flex items-start gap-2">
                        <span class="text-emerald-400 flex-shrink-0 text-sm">💡</span>
                        <div class="leading-relaxed">
                          <strong class="text-emerald-300 font-semibold">Como destravar no webPosto: </strong>
                          <span>${escapeHtml(acaoMsg)}</span>
                        </div>
                      </div>
                    ` : ''}
                  </div>

                  <!-- Modo Contador (Foco Contabil, Tags XML & SPED) -->
                  <div class="finding-view-contador hidden space-y-2">
                    ${item.explicacao_tecnica ? `
                      <p class="text-xs text-cyan-200/90 leading-relaxed font-mono">
                        ${escapeHtml(item.explicacao_tecnica)}
                      </p>
                    ` : (execMsg ? `
                      <p class="text-xs text-slate-300 leading-relaxed font-mono">
                        ${escapeHtml(execMsg)}
                      </p>
                    ` : '')}
                    ${fields.length > 0 ? `
                      <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                        <span class="text-cyan-400 font-semibold">Tags XML:</span>
                        ${fields.map(f => `<span class="bg-slate-900 px-1.5 py-0.5 rounded border border-cyan-500/30 text-cyan-300">${escapeHtml(f)}</span>`).join('')}
                      </div>
                    ` : ''}
                    ${(Array.isArray(item.base_legal) && item.base_legal.length > 0) ? `
                      <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                        <span class="text-slate-500">Fundamentacao:</span>
                        ${item.base_legal.map(b => `<span class="bg-slate-900 px-1.5 py-0.5 rounded border border-white/5 text-slate-300">${escapeHtml(b)}</span>`).join('')}
                      </div>
                    ` : ''}
                  </div>
                </div>"""

    if old_finding_item in content_lf:
        content_lf = content_lf.replace(old_finding_item, new_finding_item, 1)
        print("[WIDGETS] 2. fiscal_findings_list adaptado para visualizacao dupla Gestor/Contador.")
    else:
        print("[WIDGETS] 2. fiscal_findings_list ja estava atualizado.")

    # 3. bindEvents para alternar finding-view-gestor e finding-view-contador
    old_bind = """            const gestorPanel = rootElement.querySelector('.persona-view-gestor');
            const contadorPanel = rootElement.querySelector('.persona-view-contador');
            if (gestorPanel) gestorPanel.classList.toggle('hidden', targetPersona !== 'gestor');
            if (contadorPanel) contadorPanel.classList.toggle('hidden', targetPersona !== 'contador');
          });"""

    new_bind = """            const gestorPanel = rootElement.querySelector('.persona-view-gestor');
            const contadorPanel = rootElement.querySelector('.persona-view-contador');
            if (gestorPanel) gestorPanel.classList.toggle('hidden', targetPersona !== 'gestor');
            if (contadorPanel) contadorPanel.classList.toggle('hidden', targetPersona !== 'contador');

            // FASE 4: Alterna o detalhamento interno dos cards de findings
            const isGestor = (targetPersona === 'gestor');
            rootElement.querySelectorAll('.finding-view-gestor').forEach(el => el.classList.toggle('hidden', !isGestor));
            rootElement.querySelectorAll('.finding-view-contador').forEach(el => el.classList.toggle('hidden', isGestor));
          });"""

    if old_bind in content_lf:
        content_lf = content_lf.replace(old_bind, new_bind, 1)
        print("[WIDGETS] 3. bindEvents atualizado para alternar findings por persona.")
    else:
        print("[WIDGETS] 3. bindEvents ja estava atualizado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    widgets_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(widgets_path)


def sync_dist() -> None:
    """Sincroniza aura-genui-widgets.js com dist/."""
    src = WEB_DIR / "js" / "aura-genui-widgets.js"
    dst = DIST_WEB_DIR / "js" / "aura-genui-widgets.js"
    if src.exists() and dst.parent.exists():
        shutil.copy2(src, dst)
        print("[SYNC] Sincronizado: js/aura-genui-widgets.js -> dist/")


if __name__ == "__main__":
    print("Iniciando aplicacao da Fase 4...")
    update_aura_engine()
    update_genui_widgets()
    sync_dist()
    print("Fase 4 aplicada com sucesso!")
