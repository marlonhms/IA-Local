import os

html_path = "ia-banco-local/web/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("css/aura.css?v=2.10.11", "css/aura.css?v=2.10.12")
html = html.replace("aura-aux-panel.js?v=2.10.10", "aura-aux-panel.js?v=2.10.12")
html = html.replace("aura-chat.js?v=2.10.11", "aura-chat.js?v=2.10.12")
html = html.replace("aura-genui-widgets.js?v=2.10.5", "aura-genui-widgets.js?v=2.10.12")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("index.html cache versions bumped to v=2.10.12")
