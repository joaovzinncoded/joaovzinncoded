"""Receptor de arquivos XML via HTTP (só biblioteca padrão).

Iniciar:
    python receptor_xml.py [porta]          # padrão: 8000

Enviar um arquivo:
    curl -X POST --data-binary @nota.xml -H "Content-Type: application/xml" http://localhost:8000/

Cada XML válido é salvo em ./recebidos/ e a resposta é um JSON com o nome do arquivo.
"""
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PASTA_DESTINO = Path(__file__).parent / "recebidos"
TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10 MB


class ReceptorXML(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            tamanho = int(self.headers.get("Content-Length", ""))
        except ValueError:
            tamanho = -1
        if tamanho < 0:
            return self.responder(411, erro="Content-Length obrigatório")
        if tamanho > TAMANHO_MAXIMO:
            return self.responder(413, erro=f"Arquivo maior que {TAMANHO_MAXIMO} bytes")

        conteudo = self.rfile.read(tamanho)
        try:
            raiz = ET.fromstring(conteudo)  # Expat >= 2.4.1 já bloqueia "billion laughs"
        except ET.ParseError as e:
            return self.responder(400, erro=f"XML inválido: {e}")

        # O nome é gerado aqui, nunca vem do cliente (evita path traversal).
        nome = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.xml"
        PASTA_DESTINO.mkdir(exist_ok=True)
        (PASTA_DESTINO / nome).write_bytes(conteudo)
        self.responder(201, arquivo=nome, raiz=raiz.tag, bytes=tamanho)

    def responder(self, status, **dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Recebendo XML em http://localhost:{porta}/ -> {PASTA_DESTINO}")
    ThreadingHTTPServer(("", porta), ReceptorXML).serve_forever()
