from pathlib import Path
p = Path(__file__).parent / 'cripto-v1.2/scripts/attest_harness.py'
s = p.read_text(encoding='utf8').replace('import sys\n', 'import sys\nimport tempfile\n')
a = s.index('    # Cada juiz grava o SEU atestado')
b = s.index('    return 0', a)
block = s[a:b]
block = block.replace('attestation_path=PHASE1_ATTESTATION_PATH,', 'attestation_path=staged_phase1,\n        repo=ROOT,')
block = block.replace('attestation_path=attestation_path_for(TRIALS_PATH),', 'attestation_path=staged_v3,\n        repo=ROOT,')
block = block.replace('    print(f"atestado da Fase 1 gravado em {PHASE1_ATTESTATION_PATH} ({rec_phase1[\'passed_at\']})")\n', '')
block = block.replace('    print(\n        f"controle positivo PASSOU — atestado gravado em "\n        f"{attestation_path_for(TRIALS_PATH)} ({rec_v3[\'passed_at\']})"\n    )\n', '')
s = s[:a] + '''    # Core 3.2 recusa árvore suja. O primeiro arquivo canônico alterado
    # sujaria o repo e impediria atestar o segundo juiz. Os dois controles
    # rodam em staging externo contra a mesma árvore limpa; só então publicamos.
    with tempfile.TemporaryDirectory(prefix="cripto-attest-") as directory:
        staged_phase1 = Path(directory) / "phase1.json"
        staged_v3 = Path(directory) / "v3.json"
''' + ''.join('    ' + line if line.strip() else line for line in block.splitlines(keepends=True)) + '''        PHASE1_ATTESTATION_PATH.write_bytes(staged_phase1.read_bytes())
        attestation_path_for(TRIALS_PATH).write_bytes(staged_v3.read_bytes())
    print(f"atestados emitidos: Fase 1 {rec_phase1['passed_at']}; V3 {rec_v3['passed_at']}")
''' + s[b:]
p.write_text(s, encoding='utf8')
