with open("web/js/aura-aux-panel.js", "r", encoding="utf-8") as f:
    text = f.read()

# Replace missing backticks around template literals
old_chunk1 = """    capsule.style.left = ${sourceRect.left}px;
    capsule.style.top = ${sourceRect.top}px;
    capsule.style.width = ${sourceRect.width}px;
    capsule.style.height = ${sourceRect.height}px;
    capsule.style.borderRadius = ${window.getComputedStyle(triggerEl).borderRadius || '12px'};"""

new_chunk1 = """    capsule.style.left = `${sourceRect.left}px`;
    capsule.style.top = `${sourceRect.top}px`;
    capsule.style.width = `${sourceRect.width}px`;
    capsule.style.height = `${sourceRect.height}px`;
    capsule.style.borderRadius = `${window.getComputedStyle(triggerEl).borderRadius || '12px'}`;"""

if old_chunk1 not in text:
    print("ERROR: old_chunk1 not found")
else:
    text = text.replace(old_chunk1, new_chunk1, 1)

old_chunk2 = """          capsule.style.left = ${targetRect.left}px;
          capsule.style.top = ${targetRect.top}px;
          capsule.style.width = ${targetRect.width}px;
          capsule.style.height = ${targetRect.height}px;"""

new_chunk2 = """          capsule.style.left = `${targetRect.left}px`;
          capsule.style.top = `${targetRect.top}px`;
          capsule.style.width = `${targetRect.width}px`;
          capsule.style.height = `${targetRect.height}px`;"""

if old_chunk2 not in text:
    print("ERROR: old_chunk2 not found")
else:
    text = text.replace(old_chunk2, new_chunk2, 1)

with open("web/js/aura-aux-panel.js", "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESS: syntax error fixed in web/js/aura-aux-panel.js")
