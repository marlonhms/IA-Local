"""
Script de aplicacao da Fase 1 do Apendice C: Nitidez Optica e Tipografia Cristalina.
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


def update_css() -> None:
    """Aplica melhorias de nitidez optica em web/css/aura.css."""
    css_path = WEB_DIR / "css" / "aura.css"
    content = css_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. html, body: restaurar subpixel rendering
    old_hb = """html, body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}"""
    new_hb = """html, body {
  -webkit-font-smoothing: subpixel-antialiased;
  -moz-osx-font-smoothing: auto;
  text-rendering: optimizeLegibility;
}"""
    if old_hb in content_lf:
        content_lf = content_lf.replace(old_hb, new_hb, 1)
        print("[CSS] 1. html, body atualizado para subpixel-antialiased.")
    else:
        print("[CSS] 1. html, body ja estava atualizado ou target nao encontrado.")

    # 2. chat-bubble-user
    old_user = """.chat-bubble-user {
  background: linear-gradient(135deg, rgba(18, 30, 52, 0.92) 0%, rgba(12, 20, 36, 0.98) 100%);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 16px 16px 4px 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  word-break: break-word;
  transition: all 0.2s ease;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  transform: none !important;
}"""
    new_user = """.chat-bubble-user {
  background: linear-gradient(135deg, rgba(18, 30, 52, 0.92) 0%, rgba(12, 20, 36, 0.98) 100%);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 16px 16px 4px 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  word-break: break-word;
  transition: all 0.2s ease;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  -webkit-font-smoothing: subpixel-antialiased !important;
  -moz-osx-font-smoothing: auto !important;
  text-rendering: optimizeLegibility;
  transform: none !important;
  will-change: auto !important;
}"""
    if old_user in content_lf:
        content_lf = content_lf.replace(old_user, new_user, 1)
        print("[CSS] 2. chat-bubble-user atualizado.")
    else:
        print("[CSS] 2. chat-bubble-user ja estava atualizado ou target nao encontrado.")

    # 3. chat-bubble-aura
    old_aura = """.chat-bubble-aura {
  width: 100%;
  max-width: 100%;
  padding: 1.125rem;
  background: linear-gradient(180deg, rgba(14, 21, 37, 0.94) 0%, rgba(9, 14, 26, 0.98) 100%);
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid rgba(168, 180, 197, 0.14);
  border-radius: 18px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  word-break: break-word;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  transform: none !important;
}"""
    new_aura = """.chat-bubble-aura {
  width: 100%;
  max-width: 100%;
  padding: 1.125rem;
  background: linear-gradient(180deg, rgba(14, 21, 37, 0.94) 0%, rgba(9, 14, 26, 0.98) 100%);
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid rgba(168, 180, 197, 0.14);
  border-radius: 18px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  word-break: break-word;
  -webkit-font-smoothing: subpixel-antialiased !important;
  -moz-osx-font-smoothing: auto !important;
  text-rendering: optimizeLegibility;
  transform: none !important;
  will-change: auto !important;
}"""
    if old_aura in content_lf:
        content_lf = content_lf.replace(old_aura, new_aura, 1)
        print("[CSS] 3. chat-bubble-aura atualizado.")
    else:
        print("[CSS] 3. chat-bubble-aura ja estava atualizado ou target nao encontrado.")

    # 4. anti-blur block
    old_blind = """.chat-bubble-aura,
.chat-bubble-aura *,
.chat-bubble-user,
.chat-bubble-user *,
.chat-bubble-welcome,
.chat-bubble-welcome * {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}"""
    new_blind = """.chat-bubble-aura,
.chat-bubble-aura *,
.chat-bubble-user,
.chat-bubble-user *,
.chat-bubble-welcome,
.chat-bubble-welcome * {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  -webkit-font-smoothing: subpixel-antialiased !important;
  -moz-osx-font-smoothing: auto !important;
  text-rendering: optimizeLegibility;
  transform: none !important;
  will-change: auto !important;
}"""
    if old_blind in content_lf:
        content_lf = content_lf.replace(old_blind, new_blind, 1)
        print("[CSS] 4. anti-blur block atualizado.")
    else:
        print("[CSS] 4. anti-blur block ja estava atualizado ou target nao encontrado.")

    # 5. prose-aura e lead paragraph
    old_prose = """.prose-aura {
  font-family: var(--font-sans);
  font-weight: 400;
  font-size: 0.915rem;
  line-height: 1.68;
  letter-spacing: 0.005em;
  color: #cbd5e1;
}"""
    new_prose = """.prose-aura {
  font-family: var(--font-sans);
  font-weight: 400;
  font-size: 0.935rem;
  line-height: 1.65;
  letter-spacing: 0.005em;
  color: #e2e8f0;
}"""
    if old_prose in content_lf:
        content_lf = content_lf.replace(old_prose, new_prose, 1)
        print("[CSS] 5. prose-aura base atualizado para 0.935rem / #e2e8f0.")
    else:
        print("[CSS] 5. prose-aura base ja estava atualizado ou target nao encontrado.")

    old_lead = """.prose-aura > p:first-of-type {
  color: #f1f5f9;
  font-size: 0.94rem;
  line-height: 1.6;
  margin-bottom: 0.85rem;
}"""
    new_lead = """.prose-aura > p:first-of-type {
  color: #f8fafc;
  font-size: 0.96rem;
  line-height: 1.6;
  margin-bottom: 0.85rem;
}"""
    if old_lead in content_lf:
        content_lf = content_lf.replace(old_lead, new_lead, 1)
        print("[CSS] 5b. prose-aura lead paragraph atualizado para 0.96rem / #f8fafc.")
    else:
        print("[CSS] 5b. prose-aura lead paragraph ja estava atualizado.")

    # 6. prose-aura td
    old_td = """.prose-aura td {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
  font-variant-numeric: tabular-nums;
  -webkit-font-feature-settings: "tnum" 1;
  font-feature-settings: "tnum" 1;
}"""
    new_td = """.prose-aura td {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
  -webkit-font-feature-settings: "tnum" 1;
  font-feature-settings: "tnum" 1;
}"""
    if old_td in content_lf:
        content_lf = content_lf.replace(old_td, new_td, 1)
        print("[CSS] 6. prose-aura td atualizado para #e2e8f0.")

    # 7. gpu-guard-active smoothing
    old_gpu_block = """html.gpu-guard-active,
body.gpu-guard-active,
.gpu-guard-active,
.gpu-guard-active *,
.gpu-guard-active *::before,
.gpu-guard-active *::after {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
  text-rendering: optimizeLegibility !important;
}"""
    new_gpu_block = """html.gpu-guard-active,
body.gpu-guard-active,
.gpu-guard-active,
.gpu-guard-active *,
.gpu-guard-active *::before,
.gpu-guard-active *::after {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  -webkit-font-smoothing: subpixel-antialiased !important;
  -moz-osx-font-smoothing: auto !important;
  text-rendering: optimizeLegibility !important;
}"""
    if old_gpu_block in content_lf:
        content_lf = content_lf.replace(old_gpu_block, new_gpu_block, 1)
        print("[CSS] 7. gpu-guard-active global smoothing atualizado.")

    old_gpu_bubble = """  transform: none !important;
  will-change: auto !important;
  filter: none !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
  text-rendering: optimizeLegibility !important;"""
    new_gpu_bubble = """  transform: none !important;
  will-change: auto !important;
  filter: none !important;
  -webkit-font-smoothing: subpixel-antialiased !important;
  -moz-osx-font-smoothing: auto !important;
  text-rendering: optimizeLegibility !important;"""
    if old_gpu_bubble in content_lf:
        content_lf = content_lf.replace(old_gpu_bubble, new_gpu_bubble, 1)
        print("[CSS] 7b. gpu-guard-active containers smoothing atualizado.")

    # 8. persona-view-gestor p, persona-view-contador p
    old_persona = """.persona-view-gestor p,
.persona-view-contador p {
  font-family: var(--font-mono);
  font-weight: 400;
  color: #cbd5e1; /* slate-300 */
}"""
    new_persona = """.persona-view-gestor p,
.persona-view-contador p {
  font-family: var(--font-mono);
  font-weight: 400;
  color: #e2e8f0; /* slate-200 */
}"""
    if old_persona in content_lf:
        content_lf = content_lf.replace(old_persona, new_persona, 1)
        print("[CSS] 8. persona-views monospace atualizado para #e2e8f0.")

    # 9. .prose-aura .aura-data-token
    old_token = """.prose-aura .aura-data-token {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  -webkit-font-feature-settings: "tnum" 1;
  font-feature-settings: "tnum" 1;
  font-size: 0.86em;
  font-weight: 500;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.08rem 0.35rem;
  border-radius: 5px;
  white-space: nowrap;
  display: inline-block;
  vertical-align: baseline;
}"""
    new_token = """.prose-aura .aura-data-token {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  -webkit-font-feature-settings: "tnum" 1;
  font-feature-settings: "tnum" 1;
  font-size: 0.88em;
  font-weight: 500;
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 0.08rem 0.35rem;
  border-radius: 5px;
  white-space: nowrap;
  display: inline-block;
  vertical-align: baseline;
}"""
    if old_token in content_lf:
        content_lf = content_lf.replace(old_token, new_token, 1)
        print("[CSS] 9. aura-data-token atualizado para #f8fafc e maior nitidez.")

    # 10. aura-chat-disclosure inner font
    old_disclosure = """.aura-chat-disclosure summary:hover {
  color: #67e8f9;
}"""
    new_disclosure = """.aura-chat-disclosure summary:hover {
  color: #67e8f9;
}

.aura-chat-disclosure .prose-aura,
.aura-chat-disclosure > div {
  font-size: 0.935rem;
  line-height: 1.65;
  color: #e2e8f0;
}"""
    if old_disclosure in content_lf and ".aura-chat-disclosure .prose-aura" not in content_lf:
        content_lf = content_lf.replace(old_disclosure, new_disclosure, 1)
        print("[CSS] 10. aura-chat-disclosure regras de nitidez aplicadas.")

    # Gravar arquivo preservando CRLF
    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    css_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(css_path)


def update_js() -> None:
    """Aplica melhorias de nitidez em web/js/aura-chat.js."""
    js_path = WEB_DIR / "js" / "aura-chat.js"
    content = js_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    target = '<div class="p-3 pt-2 border-t border-white/5 space-y-2 text-xs text-slate-300">'
    replacement = '<div class="p-3 pt-2 border-t border-white/5 space-y-2 text-[0.935rem] leading-relaxed text-slate-200">'

    count = content_lf.count(target)
    if count > 0:
        content_lf = content_lf.replace(target, replacement)
        print(f"[JS] Substituidas {count} ocorrencias de text-xs em aura-chat.js.")
    else:
        print("[JS] text-xs em disclosure ja estava atualizado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    js_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(js_path)


def update_html() -> None:
    """Atualiza classe de antialiasing no body em web/index.html."""
    html_path = WEB_DIR / "index.html"
    content = html_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    target = 'text-slate-200 antialiased selection:bg-auraCyan'
    replacement = 'text-slate-200 subpixel-antialiased selection:bg-auraCyan'

    if target in content_lf:
        content_lf = content_lf.replace(target, replacement, 1)
        print("[HTML] body antialiased substituido por subpixel-antialiased em index.html.")
    else:
        print("[HTML] body subpixel-antialiased ja configurado em index.html.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    html_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(html_path)


def sync_dist() -> None:
    """Sincroniza arquivos de web/ para dist/AuraBackend/_internal/web/."""
    for rel_path in ["css/aura.css", "js/aura-chat.js", "index.html"]:
        src = WEB_DIR / rel_path
        dst = DIST_WEB_DIR / rel_path
        if src.exists() and dst.parent.exists():
            shutil.copy2(src, dst)
            print(f"[SYNC] Sincronizado: {rel_path} -> dist/")


if __name__ == "__main__":
    print("Iniciando aplicacao da Fase 1...")
    update_css()
    update_js()
    update_html()
    sync_dist()
    print("Fase 1 concluida com sucesso!")
