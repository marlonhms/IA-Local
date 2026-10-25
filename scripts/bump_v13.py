with open("ia-banco-local/web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("v=2.10.12", "v=2.10.13")

with open("ia-banco-local/web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Bumped to v=2.10.13")
