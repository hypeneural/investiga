import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://tijucas.atende.net/transparencia/item/despesas-publicas"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, context=ctx) as resp:
        html = resp.read().decode('utf-8')
        print(f"Loaded {len(html)} bytes")
        print(html[:1500])
except Exception as e:
    print("Failed to load:", e)
