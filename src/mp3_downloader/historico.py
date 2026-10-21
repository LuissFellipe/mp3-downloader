"""Histórico de downloads, guardado na pasta de dados do usuário.

Antes o arquivo ficava ao lado do código, dentro do repositório, e entrou no
git com a lista real de músicas baixadas. Agora vai para a pasta de dados do
sistema (~/.local/share no Linux, %APPDATA% no Windows), fora de qualquer
repositório.
"""

import json
import os
import sys
from pathlib import Path


def pasta_de_dados():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "mp3-downloader"


def arquivo_historico():
    return pasta_de_dados() / "historico.json"


def carregar(caminho=None):
    caminho = Path(caminho or arquivo_historico())
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (OSError, ValueError):
        return []


def salvar(historico, caminho=None):
    caminho = Path(caminho or arquivo_historico())
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # Grava num arquivo temporário e troca: uma falha no meio da escrita não
    # deixa o histórico pela metade.
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(caminho)
