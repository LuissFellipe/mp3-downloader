import pytest

from mp3_downloader.downloader import (
    Opcoes, erro_do_resultado, montar_comando, titulo_do_resultado, urls_do_texto,
)

URL = "https://www.youtube.com/watch?v=exemplo"


def valor(cmd, opcao):
    return cmd[cmd.index(opcao) + 1]


def test_mp3_usa_o_bitrate_escolhido():
    cmd = montar_comando(URL, "/musicas", Opcoes("audio", "mp3", "192k"))
    assert cmd[0] == "yt-dlp" and cmd[-1] == URL
    assert "--extract-audio" in cmd
    assert valor(cmd, "--audio-format") == "mp3"
    assert valor(cmd, "--audio-quality") == "192"
    assert valor(cmd, "--output") == "/musicas/%(title)s.%(ext)s"


@pytest.mark.parametrize("formato", ["flac", "wav"])
def test_formato_sem_perda_ignora_o_bitrate(formato):
    cmd = montar_comando(URL, "/musicas", Opcoes("audio", formato, "96k"))
    assert valor(cmd, "--audio-quality") == "0"


def test_video_mp4_junta_video_e_audio_em_mp4():
    cmd = montar_comando(URL, "/videos", Opcoes("video (mp4)"))
    assert "--extract-audio" not in cmd
    assert valor(cmd, "--merge-output-format") == "mp4"
    assert valor(cmd, "--format").startswith("bestvideo[ext=mp4]")


def test_nunca_baixa_a_playlist_inteira():
    for opcoes in (Opcoes(), Opcoes("video (webm)")):
        assert "--no-playlist" in montar_comando(URL, "/x", opcoes)


@pytest.mark.parametrize("opcoes", [
    dict(tipo="podcast"), dict(formato="aac"), dict(qualidade="999k"),
])
def test_opcao_desconhecida_e_recusada(opcoes):
    with pytest.raises(ValueError):
        Opcoes(**opcoes)


def test_rotulo_do_historico():
    assert Opcoes("audio", "flac").rotulo == "flac"
    assert Opcoes("video (webm)").rotulo == "webm"


def test_titulo_sai_do_ultimo_caminho_impresso():
    stdout = "[aviso] qualquer coisa\n/musicas/Minha Faixa.mp3\n\n"
    assert titulo_do_resultado(stdout) == "Minha Faixa"
    assert titulo_do_resultado("") == ""


def test_erro_e_a_ultima_linha_do_stderr():
    assert erro_do_resultado("WARNING: x\nERROR: Video unavailable\n") == "ERROR: Video unavailable"
    assert erro_do_resultado("") == "Erro desconhecido"


def test_urls_ignoram_linhas_vazias_e_repetidas():
    texto = f"\n  {URL}  \n\nhttps://youtu.be/b\n{URL}\n"
    assert urls_do_texto(texto) == [URL, "https://youtu.be/b"]
