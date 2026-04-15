from markitdown import MarkItDown

md = MarkItDown()
result = md.convert(r"E:\Automatizaciones\Python\VGCTeams.html")

with open("resultado.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)

print("Listo!")
