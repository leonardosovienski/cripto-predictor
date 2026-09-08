"""predictor-core.measurement.trials — Experiment Registry + Deflated Sharpe Ratio.

RECONCILIAÇÃO (2026-07-09): esta é a versão EVOLUÍDA, re-promovida do
previsao-cripto (analyzers/trials.py), que havia divergido da cópia original do
core — o pior tipo de drift: duas réguas de governança na mesma plataforma.
Ganhos sobre a v1: schema formal (`validate_trials`), governança de identidade
N+1 (mudar `params` de trial existente é ERRO, não update silencioso) e a trava
de controle positivo (criar trial NOVA exige atestado do harness — ver abaixo).

Governança contra data-snooping: cada configuração avaliada contra os dados
(ativo, horizonte, prompt, feature, fonte) é uma TENTATIVA. Avaliar N
configurações e reportar a melhor infla o Sharpe esperado por pura sorte —
E[max SR] cresce com N mesmo sem skill. O DSR (Bailey & López de Prado, 2014)
desconta isso: é o PSR calculado contra E[max SR | H0, N] em vez de zero.

O arquivo de tentativas é VERSIONADO de propósito: o desconto só é honesto se o
denominador (quantas tentativas houve) sobreviver ao esquecimento seletivo.

TRAVA DE PODER (harness ↔ registry): um NO-GO só é interpretável se o pipeline
provou que detectaria edge plantado (testing/harness). PRODUZIR UM VEREDITO
exige um ATESTADO — arquivo irmão `<trials>.harness_attestation.json`, emitido
por `testing.harness.attest_pipeline_power` — senão o registro está governando
vereditos de um juiz possivelmente cego. O atestado é arquivo, não flag em
memória, porque o harness roda na suíte de testes e o registro roda no
pipeline: processos distintos.

São DOIS os caminhos que produzem veredito, e ambos passam pela trava: criar
trial nova, e mudar `status`/`sharpe` de uma existente. Atualizar apenas
`notes` não produz veredito e segue livre.

Até 2026-09-05 o segundo caminho era isento, sob o argumento de que "a
maturação automática de resultados não pode depender do harness ter rodado na
mesma máquina". A auditoria adversarial (achado 3) mostrou o custo: com o mesmo
`name` e os mesmos `params`, uma trial `refutada` virava `comprovada` sem
controle positivo nenhum, e o estado anterior sumia sem rastro. O argumento da
maturação continua válido como incômodo — uma coorte que atualiza resultado
precisa de atestado vigente (validade de 7 dias) — mas conveniência de
atualização não pode ser mais forte que a prova de que o juiz enxerga.

APPEND-ONLY quanto a vereditos: substituir um veredito preserva o anterior em
`superseded`, com o instante da substituição. O registro deixa de poder
esquecer o que já afirmou.

Unidades: os `sharpe` registrados e o DSR operam POR-PERÍODO (a mesma unidade
que o PSR observa internamente), NÃO anualizada.

O caminho do arquivo é do DOMÍNIO: passe `path` explicitamente ou use o default
`./trials.json` no diretório de trabalho.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from statistics import NormalDist, variance
from typing import Any

from predictor_core.measurement.stats import probabilistic_sharpe_ratio

_EULER = 0.5772156649015329  # γ de Euler–Mascheroni
_DEFAULT_PATH = Path("trials.json")
_ALLOWED_EXTRA = {
    "features_used",
    "train_period",
    "test_period",
    "status",
    "rps_dixon",
    "rps_elo_baseline",
    "delta_rps_ci95",
    # Histórico append-only de vereditos substituídos. Escrito pelo registro,
    # nunca pelo chamador: mudar status/sharpe de uma trial existente preserva o
    # estado anterior aqui em vez de apagá-lo.
    "superseded",
}
_TRIAL_FIELDS = {"name", "registered_at", "params", "sharpe", "notes", "metric", *_ALLOWED_EXTRA}
_ATTESTATION_SCHEMA_VERSION = "pipeline-power/2"


def _parse_utc_z(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


class PowerAttestationMissingError(RuntimeError):
    """Tentativa de criar trial NOVA sem atestado de controle positivo.

    Rode `testing.harness.attest_pipeline_power(...)` — que exige que o SEU
    pipeline detecte edge sintético e rejeite ruído — para emitir o atestado
    irmão do trials.json. Sem essa prova, o registro governaria vereditos de
    um juiz que ninguém confirmou não ser cego."""


def attestation_path_for(trials_path: Path | str) -> Path:
    """Caminho canônico do atestado: irmão do trials.json."""
    p = Path(trials_path)
    return p.with_name(p.stem + ".harness_attestation.json")


def _load_attestation(att: Path) -> dict | None:
    """Lê um atestado legível; a validação de campos cabe ao registry."""
    if not att.exists():
        return None
    try:
        parsed = json.loads(att.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


# ---------- registro ----------


def load_trials(path: Path | str | None = None) -> list[dict]:
    p = Path(path or _DEFAULT_PATH)
    if not p.exists():
        return []
    try:
        parsed = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        # Auditoria hostil 2026-07-17: antes propagava JSONDecodeError cru,
        # sem caminho — inconsistente com kernel/obs.py e kernel/jsonl_store.py,
        # que sempre incluem o arquivo na mensagem desde df575a9.
        raise ValueError(f"{p}: trials.json corrompido — {exc}") from exc
    if not isinstance(parsed, list):
        # JSON válido (ex.: `null`) mas não é a lista esperada — sem esta
        # checagem, validate_trials(None) explodia com TypeError opaco,
        # sem relação nenhuma com a causa real (arquivo com conteúdo errado).
        raise ValueError(
            f"{p}: trials.json deve conter uma lista de tentativas "
            f"— encontrado {type(parsed).__name__}"
        )
    return parsed


def _pid_alive(pid: int) -> bool:
    """Best-effort: existe processo com este PID? Falha de leitura = "não sei",
    trata como vivo (nunca reclama antecipadamente por incerteza). Mesmo
    padrão de tools/operational_runner.py — duplicado aqui deliberadamente:
    predictor_core não deve depender de tools/ (camada operacional), mesmo
    para uma checagem pequena e estável como esta."""
    if pid <= 0:
        return True
    if sys.platform == "win32":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(
            0x1000, False, pid
        )  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return True


def _lock_owner_pid_dead(lock_path: Path) -> bool:
    """True somente quando o conteúdo do lock é legível, tem um pid, e esse
    pid está comprovadamente morto. Qualquer outra situação (ilegível, sem
    pid, vivo) é False — a política de idade abaixo continua sendo o
    fallback, nunca substituída."""
    try:
        content = json.loads(lock_path.read_text(encoding="ascii"))
        pid = content.get("pid")
    except (OSError, ValueError, AttributeError):
        return False
    if not isinstance(pid, int):
        return False
    return not _pid_alive(pid)


def _acquire_trials_lock(p: Path, *, timeout: float = 60.0, poll: float = 0.05) -> Path:
    """Lock de arquivo (O_CREAT|O_EXCL) em torno da seção crítica read-modify-
    write de register_trial. Sem isto, dois processos podiam ler o mesmo
    estado, cada um calcular sua própria trial nova, e a segunda escrita
    sobrescrevia a primeira EM SILÊNCIO — reproduzido na auditoria hostil
    2026-07-17: uma trial registrada desaparecia do arquivo final sem erro
    nem aviso algum, justamente o "esquecimento seletivo" que a governança
    N+1 do módulo existe para impedir. Advisory only (protege register_trial
    contra si mesmo em processos concorrentes, não contra edição manual do
    arquivo). Um lock cujo PID esteja comprovadamente vivo NUNCA é roubado: o
    timeout limita somente a espera do concorrente. Locks sem dono legível
    podem ser recuperados por idade como fallback conservador.

    Auditoria hostil 2026-07-17 (rodada predictor_core): a versão original só
    reclamava por IDADE (timeout default de 10s) — curto demais para dados
    científicos: um escritor legítimo mas lento (I/O de disco, pausa de GC)
    podia ter o lock "roubado" por outro processo, reabrindo exatamente a
    corrida que este lock existe para impedir. Agora o conteúdo do lock grava
    o PID do dono, e um PID comprovadamente morto é reclamado IMEDIATAMENTE.
    Um PID vivo prevalece sobre a idade; isso impede que I/O lento reabra a
    corrida que o lock existe para evitar."""
    lock_path = p.with_suffix(p.suffix + ".lock")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, json.dumps({"pid": os.getpid()}, sort_keys=True).encode("ascii"))
            os.close(fd)
            return lock_path
        except FileExistsError:
            if _lock_owner_pid_dead(lock_path):
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            # Se o lock declara um PID vivo (ou não conseguimos provar que está
            # morto), não o removemos por idade. `timeout` só decide quando o
            # concorrente desiste de esperar, nunca autoriza dois escritores.
            try:
                content = json.loads(lock_path.read_text(encoding="ascii"))
                owner_is_live = isinstance(content.get("pid"), int) and _pid_alive(content["pid"])
            except (OSError, ValueError, AttributeError):
                owner_is_live = False
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                continue  # lock sumiu entre o open e o stat: tenta de novo
            if not owner_is_live and age > timeout:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"não foi possível obter o lock de {p} (concorrendo com "
                    f"outro processo) em {timeout}s"
                )
            time.sleep(poll)


def _release_trials_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _find_non_finite_float(obj: object, path: str = "") -> str | None:
    """Percorre dict/list recursivamente; retorna o caminho (estilo `[.foo][2]`)
    do primeiro float NaN/Infinity encontrado, ou None se tudo for finito."""
    if isinstance(obj, float) and not isinstance(obj, bool) and not math.isfinite(obj):
        return path
    if isinstance(obj, dict):
        for key, value in obj.items():
            found = _find_non_finite_float(value, f"{path}[{key!r}]")
            if found is not None:
                return found
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            found = _find_non_finite_float(value, f"{path}[{i}]")
            if found is not None:
                return found
    return None


def validate_trials(trials: list[dict]) -> list[str]:
    """Schema formal do registro. Retorna a lista de violações (vazia = conforme).
    A suíte do consumidor deve falhar se o trials.json real não conformar — o
    registro só protege o DSR se todo campo do denominador for interpretável.

    Obrigatórios: name (str não-vazio, sem espaços — identidade), registered_at
    (ISO-8601 UTC 'Z'), params (dict NÃO-vazio — a configuração exata), sharpe
    (None ou número finito, unidade por-período), notes (str).
    Opcionais tipados: features_used (list[str]), train_period/test_period
    ([início, fim] ISO-8601; um dos dois lados pode ser None — limite aberto de
    uma coorte prospectiva ainda sem fim ou retrospectiva sem início definido —
    mas não os dois, que não declarariam período nenhum).
    """
    errs: list[str] = []
    seen: set[str] = set()
    for i, t in enumerate(trials):
        tag = f"trial[{i}]"
        if not isinstance(t, dict):
            errs.append(f"{tag}: trial deve ser objeto JSON, encontrado {type(t).__name__}")
            continue
        unknown = set(t) - _TRIAL_FIELDS
        if unknown:
            errs.append(f"{tag}: campos desconhecidos: {sorted(unknown)}")
        name = t.get("name")
        if not isinstance(name, str) or not name or " " in name:
            errs.append(f"{tag}: name inválido ({name!r}) — str não-vazia sem espaços")
        elif name in seen:
            errs.append(f"{tag}: name duplicado ({name!r}) — identidade precisa ser única")
        else:
            seen.add(name)
            tag = f"trial[{name}]"
        ra = t.get("registered_at", "")
        if _parse_utc_z(ra) is None:
            errs.append(f"{tag}: registered_at inválido ({ra!r}) — use ISO-8601 UTC 'Z'")
        params = t.get("params")
        if not isinstance(params, dict) or not params:
            errs.append(
                f"{tag}: params precisa ser dict NÃO-vazio (a configuração exata "
                "é o que permite ao DSR distinguir tentativas)"
            )
        elif (bad_path := _find_non_finite_float(params)) is not None:
            # Auditoria hostil 2026-07-17: sharpe já era validado com
            # math.isfinite, mas um float NaN/Infinity dentro de params
            # passava direto — json.dumps do Python grava esses valores como
            # os literais não-padrão `NaN`/`Infinity` (fora da RFC 8259), que
            # um parser JSON estrito (outra linguagem, jq, validador externo)
            # rejeita. O arquivo continuava relendo bem NO PRÓPRIO Python,
            # então o problema só aparecia ao integrar com qualquer
            # ferramenta que valide JSON de verdade.
            errs.append(
                f"{tag}: params{bad_path} é NaN/Infinity — não serializável "
                "em JSON portável (RFC 8259)"
            )
        sharpe = t.get("sharpe")
        if sharpe is not None and (
            isinstance(sharpe, bool)
            or not (isinstance(sharpe, (int, float)) and math.isfinite(sharpe))
        ):
            errs.append(f"{tag}: sharpe inválido ({sharpe!r}) — None ou número finito")
        if not isinstance(t.get("notes", ""), str):
            errs.append(f"{tag}: notes precisa ser str")
        metric = t.get("metric")
        if metric is not None and not (isinstance(metric, str) and metric):
            errs.append(f"{tag}: metric inválida ({metric!r}) — str não-vazia quando presente")
        for key in ("train_period", "test_period"):
            per = t.get(key)
            if per is not None:
                # Cada lado é str (fechado) ou None (aberto: coorte prospectiva
                # sem fim ainda, ou retrospectiva sem início definido) — mas os
                # dois None ao mesmo tempo não declaram período nenhum.
                shape_ok = (
                    isinstance(per, list)
                    and len(per) == 2
                    and all(x is None or isinstance(x, str) for x in per)
                )
                if not shape_ok or per == [None, None]:
                    errs.append(
                        f"{tag}: {key} inválido — [início, fim] ISO-8601, "
                        "um lado pode ser None (limite aberto) mas não os dois"
                    )
                elif any(x is not None and _parse_utc_z(x) is None for x in per):
                    errs.append(
                        f"{tag}: {key} inválido — limites fechados devem usar ISO-8601 UTC 'Z'"
                    )
        fu = t.get("features_used")
        if fu is not None and not (isinstance(fu, list) and all(isinstance(x, str) for x in fu)):
            errs.append(f"{tag}: features_used inválido — list[str]")
        sup = t.get("superseded")
        if sup is not None:
            if not isinstance(sup, list) or not all(isinstance(x, dict) for x in sup):
                errs.append(f"{tag}: superseded inválido — list[dict] de vereditos anteriores")
            else:
                for j, antigo in enumerate(sup):
                    if "superseded_at" not in antigo:
                        errs.append(
                            f"{tag}: superseded[{j}] sem superseded_at — um veredito "
                            "substituído precisa dizer QUANDO deixou de valer"
                        )
                    elif _parse_utc_z(antigo["superseded_at"]) is None:
                        errs.append(
                            f"{tag}: superseded[{j}].superseded_at inválido "
                            f"({antigo['superseded_at']!r}) — ISO-8601 UTC 'Z'"
                        )
    return errs


class MetricMismatchError(PowerAttestationMissingError):
    """A trial declara uma métrica diferente da atestada pelo harness — o
    controle positivo que passou não cobre o veredito que será emitido
    (ex.: harness atestado com Brier, trial avaliada por RPS)."""


def register_trial(
    name: str,
    *,
    params: dict,
    sharpe: float | None = None,
    notes: str = "",
    path: Path | str | None = None,
    now: str | None = None,
    power_attestation: Path | str | bool | None = None,
    metric: str | None = None,
    pipeline_fingerprint: str | None = None,
    **extra,
) -> list[dict]:
    """Registra (ou atualiza) uma tentativa. `name` é a identidade da CONFIGURAÇÃO.

    Governança de identidade: reexecutar a MESMA configuração atualiza a entrada
    (sharpe/notes, preservando o registered_at original); tentar "atualizar" uma
    trial existente com `params` DIFERENTES é ValueError — variação de
    configuração é tentativa NOVA (N+1), e escondê-la num update fabricaria
    significância que o DSR não desconta.

    Trava de poder: PRODUZIR VEREDITO exige o atestado do harness (arquivo
    irmão; ver docstring do módulo). São dois os caminhos que produzem veredito
    — criar trial nova, e mudar `status`/`sharpe` de uma existente. Atualizar
    apenas `notes` não é veredito e segue livre.
    `power_attestation`: None = procura o irmão; caminho = usa esse arquivo;
    False = bypass EXPLÍCITO (só para teste de mecânica do registro — nunca em
    pesquisa real).

    Append-only quanto a vereditos: substituir o veredito de uma trial preserva
    o estado anterior em `superseded`, com o instante da substituição. Sem isso,
    a mudança seria invisível para quem lê o registro depois — que é o que a
    auditoria adversarial 2026-09-05 (achado 3) explorou.

    Punição global: para trial NOVA protegida, `metric` e
    `pipeline_fingerprint` são obrigatórios e devem casar com o atestado ainda
    válido e emitido pela mesma versão do core.

    `now` injetável para teste determinístico. `extra` aceita os campos
    opcionais do schema (features_used, train_period, test_period). Valida o
    schema ANTES de gravar. Retorna a lista completa após a escrita.

    Concorrência (auditoria hostil 2026-07-17): a seção read-modify-write
    inteira roda sob um lock de arquivo (`_acquire_trials_lock`) — sem ele,
    dois processos podiam ler o mesmo estado e a segunda escrita apagava
    silenciosamente a tentativa que a primeira tinha acabado de registrar."""
    p = Path(path or _DEFAULT_PATH)
    lock_path = _acquire_trials_lock(p)
    try:
        return _register_trial_locked(
            name,
            params=params,
            sharpe=sharpe,
            notes=notes,
            path=p,
            now=now,
            power_attestation=power_attestation,
            metric=metric,
            pipeline_fingerprint=pipeline_fingerprint,
            **extra,
        )
    finally:
        _release_trials_lock(lock_path)


def _require_valid_attestation(
    name: str,
    *,
    trials_path: Path,
    power_attestation: Path | str | bool | None,
    metric: str | None,
    pipeline_fingerprint: str | None,
    motivo: str,
) -> None:
    """Exige atestado de poder válido, ou levanta. `motivo` entra nas mensagens.

    Usada nos DOIS caminhos que produzem um veredito: criar trial nova e mudar o
    veredito de uma existente. Auditoria adversarial 2026-09-05, achado 3: esta
    checagem vivia só no ramo de criação, e o caminho de atualização passava por
    fora dela.
    """
    att = (
        Path(power_attestation)
        if isinstance(power_attestation, (str, Path))
        else attestation_path_for(trials_path)
    )
    attestation = _load_attestation(att)
    required = {
        "schema_version",
        "passed_at",
        "expires_at",
        "core_version",
        "metric",
        "pipeline_fingerprint",
    }
    if (
        not attestation
        or attestation.get("schema_version") != _ATTESTATION_SCHEMA_VERSION
        or not required <= attestation.keys()
        or _parse_utc_z(attestation.get("passed_at")) is None
    ):
        raise PowerAttestationMissingError(
            f"{motivo} '{name}' sem atestado de controle positivo válido "
            f"({att}) — rode testing.harness.attest_pipeline_power antes de registrar."
        )
    try:
        expires_at = datetime.fromisoformat(attestation["expires_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise PowerAttestationMissingError(
            f"atestado inválido ({att}): expires_at ausente ou inválido"
        )
    if expires_at.tzinfo is None:
        raise PowerAttestationMissingError(
            f"atestado inválido ({att}): expires_at deve ter timezone"
        )
    if expires_at <= datetime.now(UTC):
        raise PowerAttestationMissingError(f"atestado expirado ({att}); reate o pipeline")
    current_core_version = version("predictor-core")
    if attestation["core_version"] != current_core_version:
        raise PowerAttestationMissingError(
            f"atestado ({att}) foi emitido para core {attestation['core_version']!r}, "
            f"mas o core atual é {current_core_version!r}; reate o pipeline"
        )
    if not isinstance(metric, str) or not metric:
        raise MetricMismatchError(
            f"{motivo} '{name}' deve declarar metric para casar com o atestado"
        )
    if attestation["metric"] != metric:
        raise MetricMismatchError(
            f"{motivo} '{name}' declara metric={metric!r} mas o atestado ({att}) "
            f"foi emitido com metric={attestation['metric']!r}"
        )
    if not isinstance(pipeline_fingerprint, str) or not pipeline_fingerprint:
        raise PowerAttestationMissingError(
            f"{motivo} '{name}' deve declarar pipeline_fingerprint do harness atestado"
        )
    if attestation["pipeline_fingerprint"] != pipeline_fingerprint:
        raise PowerAttestationMissingError(
            f"{motivo} '{name}' usa pipeline_fingerprint diferente do atestado ({att})"
        )


def _veredito_de(trial: Mapping[str, Any]) -> dict[str, Any]:
    """O que, numa entrada, constitui a AFIRMAÇÃO — e não o comentário."""
    return {"status": trial.get("status"), "sharpe": trial.get("sharpe")}


def _register_trial_locked(
    name: str,
    *,
    params: dict,
    sharpe: float | None,
    notes: str,
    path: Path,
    now: str | None,
    power_attestation: Path | str | bool | None,
    metric: str | None,
    pipeline_fingerprint: str | None,
    **extra,
) -> list[dict]:
    """Corpo de register_trial que roda DENTRO do lock — não chamar direto."""
    p = path
    bad_extra = set(extra) - _ALLOWED_EXTRA
    if bad_extra:
        raise ValueError(f"trial '{name}': campos extras não permitidos: {sorted(bad_extra)}")
    trials = load_trials(p)
    stamp = now or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "name": name,
        "registered_at": stamp,
        "params": params,
        "sharpe": sharpe,
        "notes": notes,
        **extra,
    }
    if metric is not None:
        entry["metric"] = metric
    for i, t in enumerate(trials):
        if t.get("name") == name:
            if t.get("params") != params:
                raise ValueError(
                    f"trial '{name}' já existe com params DIFERENTES — variação de "
                    "configuração é tentativa nova: registre com um name novo (N+1). "
                    f"registrado={t.get('params')!r} vs proposto={params!r}"
                )
            # A métrica é a RÉGUA do veredito — trocá-la num update é mudança de
            # tentativa tanto quanto mudar params (mesma governança N+1). Update
            # sem `metric` preserva a registrada (não a apaga em silêncio).
            registrada = t.get("metric")
            if metric is None:
                if registrada is not None:
                    entry["metric"] = registrada
            elif registrada is not None and metric != registrada:
                raise ValueError(
                    f"trial '{name}' já existe com metric={registrada!r} — avaliar a "
                    f"mesma configuração com outra régua ({metric!r}) é tentativa "
                    "nova: registre com um name novo (N+1)."
                )
            entry["registered_at"] = t.get("registered_at", stamp)
            # Auditoria adversarial 2026-09-05, achado 3: mudar o VEREDITO de uma
            # trial existente é produzir uma afirmação nova, e produzir afirmação
            # exige atestado de poder — exatamente como criar uma trial. Sem esta
            # trava, uma `refutada` virava `comprovada` sem controle positivo
            # nenhum, e o estado anterior desaparecia sem deixar rastro.
            anterior, atual = _veredito_de(t), _veredito_de(entry)
            if anterior != atual:
                if power_attestation is not False:
                    _require_valid_attestation(
                        name,
                        trials_path=p,
                        power_attestation=power_attestation,
                        metric=entry.get("metric"),
                        pipeline_fingerprint=pipeline_fingerprint,
                        motivo="mudança de veredito na trial",
                    )
                # O registro é append-only quanto a vereditos: o estado anterior
                # é preservado, não sobrescrito. Sem isso, a mudança seria
                # invisível para quem lê o registro depois.
                historico = list(t.get("superseded") or [])
                historico.append(
                    {**anterior, "registered_at": t.get("registered_at"), "superseded_at": stamp}
                )
                entry["superseded"] = historico
            elif t.get("superseded"):
                entry["superseded"] = list(t["superseded"])
            trials[i] = entry
            break
    else:
        if power_attestation is not False:
            _require_valid_attestation(
                name,
                trials_path=p,
                power_attestation=power_attestation,
                metric=metric,
                pipeline_fingerprint=pipeline_fingerprint,
                motivo="trial nova",
            )
        trials.append(entry)
    errs = validate_trials(trials)
    if errs:
        # Auditoria hostil 2026-07-17: quando o arquivo já tinha uma entrada
        # LEGADA malformada (edição manual, schema antigo), validate_trials
        # roda sobre a lista inteira e bloqueia até o registro de uma trial
        # nova perfeitamente válida — sem deixar claro que a causa é OUTRA
        # entrada, não a que se está tentando registrar agora.
        own_tag_failed = any(e.startswith(f"trial[{name}]:") for e in errs)
        prefix = (
            "registro violaria o schema de trials — a trial que você está "
            f"registrando ('{name}') está OK; o problema é em outra entrada já "
            "presente no arquivo: "
            if not own_tag_failed
            else "registro violaria o schema de trials: "
        )
        raise ValueError(prefix + "; ".join(errs))
    # Escrita atômica (tmp + replace): crash no meio do write não pode corromper
    # o registro inteiro — o denominador do DSR é a memória da governança.
    try:
        serialized = json.dumps(trials, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except TypeError as exc:
        # Auditoria hostil 2026-07-17: um valor não-serializável em params
        # (datetime, instância de classe custom) vazava como TypeError cru
        # do json, sem apontar o name da trial nem o caminho do arquivo —
        # opaco para depurar em produção, inconsistente com o resto do
        # módulo (load_trials sempre inclui o caminho desde df575a9).
        raise ValueError(
            f"trial '{name}': params/metadata contém um valor não serializável em "
            f"JSON ({exc}) — use apenas tipos JSON nativos (str/int/float/bool/None/"
            f"list/dict) em params"
        ) from exc
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(serialized, encoding="utf-8")
    tmp.replace(p)
    return trials


# ---------- Deflated Sharpe Ratio ----------


def expected_max_sharpe(n_trials: int, var_trials_sr: float) -> float:
    """E[max SR] sob H0 (nenhuma tentativa tem skill) para N tentativas.

    Aproximação de máximo de gaussianas (López de Prado 2014):
    sqrt(V[SR]) * ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))). Com 1 tentativa ou
    variância nula entre tentativas, não há seleção → benchmark 0."""
    if n_trials <= 1 or var_trials_sr <= 0:
        return 0.0
    nd = NormalDist()
    z1 = nd.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = nd.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trials_sr) * ((1.0 - _EULER) * z1 + _EULER * z2)


class DeflationNotEstimableError(RuntimeError):
    """`V[SR]` não é estimável — o DSR seria PSR puro, sem desconto algum.

    `E[max SR]` é `sqrt(V[SR])` vezes um fator que cresce com N. Com menos de
    duas tentativas trazendo sharpe numérico não há `V[SR]` para estimar, o
    fator é multiplicado por zero, e o "Deflated" Sharpe degenera exatamente no
    PSR com benchmark zero — enquanto continua reportando `n_trials`.

    Auditoria adversarial 2026-09-05, achado 2.
    """


def deflated_sharpe_ratio(returns: list, trial_sharpes: list, *, strict: bool = False) -> dict:
    """DSR = PSR(returns, SR0), SR0 = E[max SR] dado o nº de tentativas registradas.

    `trial_sharpes`: SRs por-período das tentativas (None/±inf são tolerados —
    contam no N, ficam fora da variância). `dsr` é P(SR verdadeiro > máximo
    esperado por sorte).

    O desconto tem DOIS insumos, e só um deles é o N: `E[max SR]` é
    `sqrt(V[SR])` vezes um fator que cresce com N. `V[SR]` é estimado APENAS
    com as tentativas que registraram sharpe numérico. Quando poucas registram,
    a variância sai de uma subamostra pequena e possivelmente não
    representativa, e o desconto fica mais fraco do que o N sugere; quando menos
    de duas registram, o desconto some por completo e o resultado é PSR puro.

    Por isso o retorno carrega o próprio diagnóstico, e não só o número:

      dsr, sr0, n_trials     — como antes (valores inalterados)
      n_sharpes              — quantas tentativas entraram em V[SR]
      sr0_estimable          — False quando V[SR] não pôde ser estimado
      deflation_applied      — False quando sr0 == 0, isto é, sem desconto
      sharpe_coverage        — n_sharpes / n_trials, 0.0 com registro vazio

    `strict=True` levanta DeflationNotEstimableError em vez de devolver um
    número que parece descontado e não está. Use em gate de promoção; o default
    permanece permissivo para não alterar chamadas existentes.

    Auditoria adversarial 2026-09-05, achado 2: antes desta versão a degeneração
    era silenciosa — quem lia o resultado via `n_trials` e não via que ele não
    tinha sido usado.
    """
    n = len(trial_sharpes)
    finite = [s for s in trial_sharpes if s is not None and math.isfinite(s)]
    estimable = len(finite) >= 2
    var = variance(finite) if estimable else 0.0
    sr0 = expected_max_sharpe(n, var)
    if strict and not estimable:
        raise DeflationNotEstimableError(
            f"V[SR] não estimável: {len(finite)} de {n} tentativas registraram sharpe "
            "numérico (mínimo 2). O DSR seria PSR com benchmark zero — sem desconto "
            "por número de tentativas. Registre o sharpe das tentativas, ou marque "
            "explicitamente as que não têm métrica comparável."
        )
    return {
        "dsr": probabilistic_sharpe_ratio(returns, benchmark_sharpe=sr0),
        "sr0": sr0,
        "n_trials": n,
        "n_sharpes": len(finite),
        "sr0_estimable": estimable,
        "deflation_applied": sr0 > 0.0,
        "sharpe_coverage": (len(finite) / n) if n else 0.0,
    }


# ---------- fachada orientada a objeto (interface do core) ----------


class TrialRegistry:
    """Fachada fina sobre o arquivo de tentativas — a interface pública do contrato.

    registry = TrialRegistry("trials.json")
    registry.register("v3-fr90", params={...}, sharpe=-0.002)
    registry.validate()                           # [] = schema conforme
    verdict = registry.deflated_sharpe(returns)   # desconta por todas as tentativas
    """

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or _DEFAULT_PATH)

    def register(
        self,
        name: str,
        *,
        params: dict,
        sharpe: float | None = None,
        notes: str = "",
        now: str | None = None,
        power_attestation: Path | str | bool | None = None,
        metric: str | None = None,
        pipeline_fingerprint: str | None = None,
        **extra,
    ) -> list[dict]:
        return register_trial(
            name,
            params=params,
            sharpe=sharpe,
            notes=notes,
            path=self.path,
            now=now,
            power_attestation=power_attestation,
            metric=metric,
            pipeline_fingerprint=pipeline_fingerprint,
            **extra,
        )

    def load(self) -> list[dict]:
        return load_trials(self.path)

    def validate(self) -> list[str]:
        return validate_trials(self.load())

    def sharpes(self) -> list:
        return [t.get("sharpe") for t in self.load()]

    def deflated_sharpe(self, returns: list, *, strict: bool = False) -> dict:
        """DSR de `returns` descontado por TODAS as tentativas registradas no arquivo.

        `strict=True` recusa devolver número quando o desconto não é estimável —
        ver `deflated_sharpe_ratio`."""
        return deflated_sharpe_ratio(returns, self.sharpes(), strict=strict)
