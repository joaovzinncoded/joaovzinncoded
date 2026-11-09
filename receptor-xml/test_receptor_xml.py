import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import receptor_xml


class TestReceptorXML(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.pasta = Path(pasta.name)
        patch = mock.patch.object(receptor_xml, "PASTA_DESTINO", self.pasta)
        patch.start()
        self.addCleanup(patch.stop)

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), receptor_xml.ReceptorXML)
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    def enviar(self, corpo):
        conexao = http.client.HTTPConnection(*self.servidor.server_address)
        conexao.request("POST", "/", body=corpo, headers={"Content-Type": "application/xml"})
        resposta = conexao.getresponse()
        return resposta.status, json.loads(resposta.read())

    def test_xml_valido_e_salvo(self):
        xml = "<?xml version='1.0' encoding='UTF-8'?><nota><valor>10,50</valor></nota>".encode()
        status, dados = self.enviar(xml)
        self.assertEqual(status, 201)
        self.assertEqual(dados["raiz"], "nota")
        self.assertEqual((self.pasta / dados["arquivo"]).read_bytes(), xml)

    def test_xml_invalido_e_rejeitado(self):
        status, dados = self.enviar(b"<nota><valor>10</nota>")
        self.assertEqual(status, 400)
        self.assertIn("XML inválido", dados["erro"])
        self.assertEqual(list(self.pasta.iterdir()), [])

    def test_arquivo_grande_e_rejeitado(self):
        with mock.patch.object(receptor_xml, "TAMANHO_MAXIMO", 10):
            status, _ = self.enviar(b"<nota>muito grande</nota>")
        self.assertEqual(status, 413)
        self.assertEqual(list(self.pasta.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
