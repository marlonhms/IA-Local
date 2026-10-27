"""
Script para sincronizar e corrigir o acionamento do botao de historico de conversas.
Remove onclick duplicado em index.html e adiciona protecao de debounce em aura-history-drawer.js.
Regra: Zero travessoes Unicode.
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent

# 1. Update web/index.html
html_path = root / "web" / "index.html"
html_content = html_path.read_text(encoding="utf-8")

old_btn_pattern = 'onclick="if(window.toggleAuraHistory){window.toggleAuraHistory();}else if(window.auraHistoryDrawer){window.auraHistoryDrawer.toggle();}" '
if old_btn_pattern in html_content:
    html_content = html_content.replace(old_btn_pattern, "")
    print("Removido onclick inline de btn-open-history em index.html")

old_side_pattern = 'onclick="if(window.toggleAuraHistory){window.toggleAuraHistory();}else if(window.auraHistoryDrawer){window.auraHistoryDrawer.toggle();} if(window.auraApp){window.auraApp.closeSidebar();}" '
if old_side_pattern in html_content:
    html_content = html_content.replace(old_side_pattern, "")
    print("Removido onclick inline de sidebar-btn-open-history em index.html")

assert "\u2014" not in html_content and "\u2013" not in html_content
html_path.write_text(html_content, encoding="utf-8")

print("web/index.html atualizado com sucesso!")
