import json
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PASTA_DESTINO = Path(__file__).parent / "recebidos"
TAMANHO_MAXIMO = 10 * 1024 * 1024


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
            raiz = ET.fromstring(conteudo)
        except ET.ParseError as e:
            return self.responder(400, erro=f"XML inválido: {e}")

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
