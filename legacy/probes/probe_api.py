import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://tijucas.atende.net/api/WCPDadosAbertos"
endpoints = [
    "/empenhos?dataInicial=01/01/2025&dataFinal=31/01/2025",
    "/despesas/empenhos?dataInicial=01/01/2025&dataFinal=31/01/2025",
    "/empenho?dataInicial=01/01/2025&dataFinal=31/01/2025"
]

for ep in endpoints:
    url = base + ep
    print(f"Testing {ep}...")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("  SUCCESS!")
            print("  Keys:", data.keys())
            if "retorno" in data and len(data["retorno"]) > 0:
                print("  Sample keys:", data["retorno"][0].keys())
    except Exception as e:
        print("  Failed:", e)
