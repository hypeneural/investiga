import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://tijucas.atende.net/api/WCPDadosAbertos"
endpoints = [
    "/despesas/empenhos?dataInicial=01/01/2025&dataFinal=31/01/2025",
    "/contratos?ano=2025",
    "/licitacoes?ano=2025"
]

for ep in endpoints:
    url = base + ep
    print(f"\nTesting {ep}...")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("  SUCCESS!")
            if "retorno" in data and len(data["retorno"]) > 0:
                print("  Type of first return:", type(data["retorno"][0]))
                if isinstance(data["retorno"][0], dict):
                    print("  Sample keys:", data["retorno"][0].keys())
                else:
                    print("  Sample data:", data["retorno"][0])
    except Exception as e:
        print("  Failed:", e)
