"""Monta o comando do yt-dlp e interpreta o resultado.

Fica separado da interface para poder ser testado sem abrir janela nenhuma.
"""

import os
from dataclasses import dataclass

FORMATOS_AUDIO = ["mp3", "flac", "wav", "ogg", "m4a"]
QUALIDADES = ["320k", "256k", "192k", "128k", "96k"]
TIPOS = ["audio", "video (mp4)", "video (webm)"]
# Sem perda: o bitrate não se aplica, e o yt-dlp usa a melhor qualidade (0).
SEM_PERDA = ("flac", "wav")


@dataclass(frozen=True)
class Opcoes:
    tipo: str = "audio"
    formato: str = "mp3"
    qualidade: str = "320k"

    def __post_init__(self):
        if self.tipo not in TIPOS:
            raise ValueError(f"tipo desconhecido: {self.tipo}")
        if self.tipo == "audio" and self.formato not in FORMATOS_AUDIO:
            raise ValueError(f"formato de áudio desconhecido: {self.formato}")
        if self.qualidade not in QUALIDADES:
            raise ValueError(f"qualidade desconhecida: {self.qualidade}")

    @property
    def video(self):
        return self.tipo.startswith("video")

    @property
    def rotulo(self):
        """Formato gravado no histórico: o de áudio, ou mp4/webm para vídeo."""
        if self.video:
            return "mp4" if "mp4" in self.tipo else "webm"
        return self.formato


def montar_comando(url, destino, opcoes):
    saida = os.path.join(destino, "%(title)s.%(ext)s")
    # --print after_move devolve o caminho final do arquivo, já convertido, e é
    # de onde sai o título mostrado na tela.
    comuns = ["--output", saida, "--no-playlist", "--print", "after_move:%(filepath)s"]
    if opcoes.video:
        ext = opcoes.rotulo
        return [
            "yt-dlp",
            "--format", f"bestvideo[ext={ext}]+bestaudio/best[ext={ext}]/best",
            "--merge-output-format", ext,
            *comuns,
            url,
        ]
    qualidade = "0" if opcoes.formato in SEM_PERDA else opcoes.qualidade.removesuffix("k")
    return [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", opcoes.formato,
        "--audio-quality", qualidade,
        *comuns,
        url,
    ]


def titulo_do_resultado(stdout):
    """Nome do arquivo gerado, sem extensão, a partir da última linha impressa."""
    linhas = [l.strip() for l in stdout.splitlines() if l.strip()]
    if not linhas:
        return ""
    return os.path.splitext(os.path.basename(linhas[-1]))[0]


def erro_do_resultado(stderr):
    """A última linha do stderr, que é onde o yt-dlp põe o motivo da falha."""
    linhas = [l.strip() for l in stderr.splitlines() if l.strip()]
    return linhas[-1] if linhas else "Erro desconhecido"


def urls_do_texto(texto):
    """Uma URL por linha; linhas vazias e repetidas são ignoradas, na ordem."""
    vistas, urls = set(), []
    for linha in texto.splitlines():
        url = linha.strip()
        if url and url not in vistas:
            vistas.add(url)
            urls.append(url)
    return urls
