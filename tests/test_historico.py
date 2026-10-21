from mp3_downloader import historico


def test_salva_e_carrega(tmp_path):
    caminho = tmp_path / "sub" / "historico.json"
    entradas = [{"url": "https://youtu.be/a", "title": "Ação", "status": "ok"}]
    historico.salvar(entradas, caminho)
    assert historico.carregar(caminho) == entradas
    assert not caminho.with_suffix(".tmp").exists()


def test_arquivo_ausente_ou_corrompido_vira_lista_vazia(tmp_path):
    assert historico.carregar(tmp_path / "nao-existe.json") == []
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{ isto não é json", encoding="utf-8")
    assert historico.carregar(ruim) == []


def test_fica_fora_do_repositorio(monkeypatch, tmp_path):
    # O histórico já foi parar no git por ficar ao lado do código.
    monkeypatch.setattr(historico.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert historico.arquivo_historico() == tmp_path / "mp3-downloader" / "historico.json"
