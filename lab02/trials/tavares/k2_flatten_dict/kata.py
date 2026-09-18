def flatten_dict(dicionario, chave_pai="", sep="."):
    itens = []
    for chave, valor in dicionario.items():
        nova_chave = f"{chave_pai}{sep}{chave}" if chave_pai else chave
        if isinstance(valor, dict):
            itens.extend(flatten_dict(valor, nova_chave, sep=sep).items())
        else:
            itens.append((nova_chave, valor))
    return dict(itens)