with open("ia-banco-local/web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("v=2.10.15", "v=2.10.16")

with open("ia-banco-local/web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Bumped index.html to v=2.10.16")
