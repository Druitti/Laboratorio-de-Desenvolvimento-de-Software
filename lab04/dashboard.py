"""Dashboard do Lab04 (Streamlit). Execute: ``streamlit run lab04/dashboard.py``."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from scipy import stats

# `streamlit run lab04/dashboard.py` põe lab04/ no sys.path, não a raiz do repo.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab04.null_dist import mannwhitney_null, split_groups, welch_null  # noqa: E402
from lab04.plots import fig_g1, fig_g2, fig_g3, fig_g4, fig_power_complement  # noqa: E402
from lab04.power import needed_n_text  # noqa: E402
from lab04.real_data import analyze_real_groups  # noqa: E402
from lab04.simulation import compare_groups, read_real_samples, simulate_groups  # noqa: E402

DEFAULT_CSV = ROOT / "lab04" / "data" / "real_prs.csv"
DATA_SOURCE = (
    "PRs mergeados de autores humanos, criados no 1º semestre de 2026, nos 500 repositórios públicos com mais "
    "estrelas, coletados pela API GraphQL do GitHub. Cada PR vem de um repositório diferente, sorteado com "
    "semente fixa (método e limitações em `docs/lab04/cenario-dados.md`)."
)
DASHBOARD_LINK = "[http://localhost:8501](http://localhost:8501)"
REPO_LINK = (
    "[repositório](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/tree/main/lab04) · "
    "[GitHub Projects](https://github.com/users/Druitti/projects/5)"
)
METHOD_LINK = "[método e fontes](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/blob/main/docs/lab04/cenario-dados.md)"

QUESTION = (
    "Em repositórios open source populares que usam bots de revisão em parte dos PRs, o tempo até o merge "
    "difere entre PRs revisados por um bot e PRs sem essa revisão?"
)
H0 = "O tempo até o merge dos PRs é o mesmo com e sem bot de revisão."
H1 = "O tempo até o merge dos PRs difere entre os PRs com e sem bot de revisão (teste bilateral)."


@st.cache_data(show_spinner=False)
def load_real(path: str) -> dict[str, list[float]]:
    return read_real_samples(path)


@st.cache_data(show_spinner=False)
def load_robustness(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def simulate(real: dict[str, list[float]], n: int, seed: int, alpha: float):
    simulated = simulate_groups(real, n_per_group=n, seed=seed)
    return simulated, compare_groups(simulated, alpha=alpha)


@st.cache_data(show_spinner="Permutando para obter U sob H0…")
def null_distributions(simulated: dict[str, np.ndarray], alpha: float, seed: int):
    _, first, second = split_groups(simulated)
    return welch_null(first, second, alpha=alpha), mannwhitney_null(first, second, alpha=alpha, seed=seed)


def describe(values) -> str:
    v = np.asarray(list(values), dtype=float)
    mean, median = float(v.mean()), float(np.median(v))
    skew = float(stats.skew(v, bias=False)) if v.std() > 0 else 0.0
    return f"mediana {median:.1f} h, média {mean:.1f} h, assimetria {skew:.1f}, máximo {v.max():.1f} h"


TEST_NAMES = {"welch": "Welch", "mann_whitney": "Mann-Whitney"}


def _type_i_verdict(rate: float, alpha: float, repetitions: int) -> str:
    """Compara a taxa com α considerando o erro de simulação (IC de 95%)."""
    margin = 1.96 * (max(rate * (1 - rate), 0.0) / repetitions) ** 0.5
    if rate + margin < alpha:
        return "conservador (abaixo de α)"
    if rate - margin > alpha:
        return "liberal (acima de α)"
    return "compatível com α"


def type_i_text(report: dict) -> str:
    """Texto do G3: quão perto de α cada teste ficou em cada situação."""
    alpha, reps = float(report["alpha"]), int(report["repetitions"])
    labels = {"lognormal_reference": "na lognormal de referência", "outlier_contamination": "com outliers"}
    parts = []
    for test_key, name in TEST_NAMES.items():
        pieces = []
        for key, label in labels.items():
            rate = float(report["scenarios"][key]["q1_type_i"][test_key])
            pieces.append(f"{rate:.1%} {label}, {_type_i_verdict(rate, alpha, reps)}")
        parts.append(f"{name}: " + "; ".join(pieces))
    return (
        f"O gráfico mostra a proporção de rejeições de H₀ quando ela é verdadeira ({reps:,} repetições por situação); "
        f"a linha tracejada marca α = {alpha:.0%} e as barras de erro, o IC de 95% da simulação. "
        + ". ".join(parts)
        + ". Um teste cuja taxa fica abaixo de α rejeita menos do que deveria, o que protege contra falsos positivos "
        "mas custa poder; o que se desvia de α é o teste que não está calibrado para esses dados assimétricos."
    )


def power_text(report: dict) -> str:
    """Texto do G4: qual teste detecta melhor o efeito e se a vantagem muda de lado."""
    scenarios = report["scenarios"]
    labels = {"lognormal_reference": "na lognormal", "outlier_contamination": "com outliers"}
    effects = [float(e) for e in report["effects_log_shift"]]
    last, ratio = len(effects) - 1, math.exp(effects[-1])
    pieces, leaders = [], set()
    for key, label in labels.items():
        point = scenarios[key]["q2"][last]["rejection_proportion"]
        pieces.append(f"{label}: Welch {point['welch']:.1%} e Mann-Whitney {point['mann_whitney']:.1%}")
        for q2 in scenarios[key]["q2"][1:]:
            rates = q2["rejection_proportion"]
            leaders.add("mann_whitney" if rates["mann_whitney"] > rates["welch"] else "welch")
    if len(leaders) == 1:
        winner = TEST_NAMES[next(iter(leaders))]
        change = f"A vantagem do {winner} vale em todos os efeitos simulados e nas duas situações; ela não muda de lado."
    else:
        change = "A vantagem muda de lado conforme o efeito e a situação; compare as curvas ponto a ponto."
    gap = max(
        abs(float(ref["rejection_proportion"][t]) - float(out["rejection_proportion"][t]))
        for ref, out in zip(scenarios["lognormal_reference"]["q2"], scenarios["outlier_contamination"]["q2"])
        for t in TEST_NAMES
    )
    best = max(
        float(q2["rejection_proportion"][t]) for key in labels for q2 in scenarios[key]["q2"] for t in TEST_NAMES
    )
    outliers = (
        "As curvas contínuas (lognormal) e tracejadas (outliers) quase coincidem, então os outliers simulados "
        "alteraram pouco o poder de ambos"
        if gap < 0.03
        else f"Os outliers simulados mudaram o poder em até {gap * 100:.1f} pontos percentuais"
    )
    low_power = (
        f"; nenhum teste passou de {best:.0%} de poder, longe dos 80% usuais, "
        "com n por grupo pequeno e dados muito variáveis"
        if best < 0.8
        else ""
    )
    return (
        f"O gráfico mostra a proporção de rejeições de H₀ quando o 2º grupo tem mediana até {ratio:.1f}× maior. "
        f"No maior efeito simulado, {'; '.join(pieces)}. {change} {outliers}{low_power}."
    )


def _q1_rates(report: dict, test_key: str) -> list[float]:
    return [float(row["rejection_proportion"][test_key]) for row in report["q1_type_i"]]


def q1_by_n_text(report: dict) -> str:
    """Texto da Q1 por tamanho amostral (#64)."""
    alpha, reps = float(report["alpha"]), int(report["repetitions"])
    sizes = [int(n) for n in report["sample_sizes"]]
    parts = []
    for key, name in TEST_NAMES.items():
        rates = _q1_rates(report, key)
        verdicts = " ou ".join(sorted({_type_i_verdict(r, alpha, reps) for r in rates}))
        parts.append(f"{name} de {min(rates):.1%} a {max(rates):.1%}, {verdicts}")
    welch = _q1_rates(report, "welch")
    trend = (
        " O Welch se aproxima de α conforme n cresce, porque a média amostral fica mais próxima da normal, "
        "mas segue abaixo de α em todos os tamanhos avaliados."
        if welch[-1] > welch[0] and max(welch) < alpha
        else ""
    )
    return (
        f"Repetindo Q1 com {sizes[0]} a {sizes[-1]} PRs por grupo ({reps:,} repetições em cada tamanho), "
        f"o erro tipo I ficou: {'; '.join(parts)}.{trend}"
    )


def _observed_row(report: dict, n: int) -> dict:
    rows = report["observed_effect"]["power"]
    return min(rows, key=lambda row: abs(int(row["n_per_group"]) - n))


def _welch_ties_up_to(report: dict) -> float | None:
    sigmas = [
        float(row["sigma_log_hours"])
        for row in report["skewness_sensitivity"]["rows"]
        if row["power"]["welch"] >= row["power"]["mann_whitney"]
    ]
    return max(sigmas) if sigmas else None


def power_complement_text(report: dict, n_real: int) -> str:
    """Texto do complemento de G4: tamanho amostral e assimetria."""
    observed = report["observed_effect"]
    row = _observed_row(report, n_real)["rejection_proportion"]
    skew = report["skewness_sensitivity"]["rows"]
    mw = [float(r["power"]["mann_whitney"]) for r in skew]
    welch = [float(r["power"]["welch"]) for r in skew]
    tie = _welch_ties_up_to(report)
    sigma_real = float(report["real_data_fit"]["sigma_log_hours"])
    crossover = (
        f"O Welch só empata ou supera o Mann-Whitney com σ de log até {tie:g}; os dados reais têm σ = {sigma_real:.2f}."
        if tie is not None
        else "O Mann-Whitney tem mais poder em todas as assimetrias avaliadas."
    )
    return (
        "À esquerda, o poder para um efeito do tamanho do observado nos dados reais (médias geométricas "
        f"{observed['geometric_mean_ratio']:.2f}× maiores em um grupo): com {_observed_row(report, n_real)['n_per_group']} "
        f"PRs por grupo, Welch {row['welch']:.1%} e Mann-Whitney {row['mann_whitney']:.1%}, e 80% de poder exigiria "
        f"{needed_n_text(report, 'mann_whitney')} PRs por grupo no Mann-Whitney e {needed_n_text(report, 'welch')} no Welch "
        "(a grade de n vai de " + f"{report['sample_sizes'][0]} a {report['sample_sizes'][-1]}). "
        f"À direita, só a assimetria muda: o poder do Mann-Whitney fica entre {min(mw):.0%} e {max(mw):.0%}, "
        f"porque os postos não mudam com a escala, enquanto o do Welch cai de {welch[0]:.0%} para {welch[-1]:.0%}. "
        + crossover
    )


def real_table(analysis: dict) -> list[dict]:
    """Tabela da seção 6: estatística, p-valor, tamanho do efeito e conclusão de cada teste."""
    welch, mw = analysis["welch"], analysis["mann_whitney"]
    first, second = analysis["groups"]
    low, high = welch["ci_hours"]
    level = 1 - float(analysis["alpha"])
    return [
        {
            "Teste": "t de Welch",
            "Estatística": f"t = {welch['statistic']:.2f} (gl = {welch['df']:.1f})",
            "p-valor": f"{welch['p_value']:.3f}",
            "Tamanho do efeito": (
                f"diferença de médias {welch['mean_difference_hours']:+.1f} h (IC {level:.0%}: {low:+.1f} a "
                f"{high:+.1f} h); g de Hedges = {welch['hedges_g']:.2f}"
            ),
            "Conclusão": welch["conclusion"],
        },
        {
            "Teste": "Mann-Whitney",
            "Estatística": f"U = {mw['statistic']:.0f}",
            "p-valor": f"{mw['p_value']:.3f}",
            "Tamanho do efeito": (
                f"P({first} > {second}) = {mw['probability_of_superiority']:.2f}; correlação bisserial de postos "
                f"= {mw['rank_biserial']:.2f}; Hodges–Lehmann = {mw['hodges_lehmann_hours']:+.1f} h"
            ),
            "Conclusão": mw["conclusion"],
        },
    ]


def real_data_text(analysis: dict, real: dict[str, list[float]], q1q2: dict | None) -> str:
    """Texto da seção 6: concordância, importância prática e poder."""
    welch, mw = analysis["welch"], analysis["mann_whitney"]
    alpha = float(analysis["alpha"])
    first, second = analysis["groups"]
    n_first, n_second = len(real[first]), len(real[second])
    agree = (welch["p_value"] < alpha) == (mw["p_value"] < alpha)
    medians = " e ".join(f"{float(np.median(real[g])):.1f} h" for g in (first, second))
    text = (
        f"A tabela aplica os dois testes aos {n_first} + {n_second} PRs coletados, com α = {alpha:.0%}; diferenças "
        f"positivas indicam `{first}` mais lento. {'Os dois testes chegam à mesma conclusão' if agree else 'Os testes discordam'}"
        f" (Welch p = {welch['p_value']:.3f}; Mann-Whitney p = {mw['p_value']:.3f}). Os efeitos são pequenos: "
        f"g de Hedges {welch['hedges_g']:.2f}, um PR de `{first}` supera um de `{second}` em "
        f"{mw['probability_of_superiority']:.0%} dos pares (50% seria nenhuma diferença), e a diferença típica "
        f"(Hodges–Lehmann) é de {mw['hodges_lehmann_hours']:+.1f} h, frente a medianas de {medians}."
    )
    if q1q2 is not None:
        row = _observed_row(q1q2, n_first)
        rates = row["rejection_proportion"]
        text += (
            f" Com {row['n_per_group']} PRs por grupo, o poder para detectar uma diferença do tamanho da observada é "
            f"de só {rates['mann_whitney']:.0%} no Mann-Whitney e {rates['welch']:.0%} no Welch (Q2): não rejeitar "
            "H₀ não mostra que o bot não tem efeito, e sim que a amostra é pequena para detectá-lo."
        )
    return text


def conclusion_text(q1q2: dict | None, robustness: dict | None, n_real: int) -> str:
    """Seção 7: expectativa × resultado, recomendação, quando ela mudaria e limitação principal."""
    lines = [
        "**Esperado antes de simular** (registrado em [cenário e dados]"
        "(https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/blob/main/docs/lab04/cenario-dados.md)):"
        " Mann-Whitney perto de 5% de erro tipo I, Welch possivelmente abaixo disso, e Mann-Whitney com mais poder,"
        " porque com σ de log acima de 2 os valores extremos dominam a média."
    ]
    if q1q2 is None:
        lines.append("Os resultados de Q1/Q2 não foram encontrados; execute `python -m lab04` para completar esta seção.")
        return "\n\n".join(lines)
    alpha, reps = float(q1q2["alpha"]), int(q1q2["repetitions"])
    welch_q1, mw_q1 = _q1_rates(q1q2, "welch"), _q1_rates(q1q2, "mann_whitney")
    powered = [row for row in q1q2["q2_power"] if row["effect_log_shift"] > 0]
    mw_always = all(row["rejection_proportion"]["mann_whitney"] > row["rejection_proportion"]["welch"] for row in powered)
    strongest = max(
        (row for row in powered if row["n_per_group"] == _observed_row(q1q2, n_real)["n_per_group"]),
        key=lambda row: row["effect_log_shift"],
    )
    found = (
        f"**Encontrado:** em Q1, o Welch ficou entre {min(welch_q1):.1%} e {max(welch_q1):.1%} e o Mann-Whitney entre "
        f"{min(mw_q1):.1%} e {max(mw_q1):.1%} de erro tipo I. Em Q2, com {strongest['n_per_group']} PRs por grupo e "
        f"medianas {strongest['median_ratio']:.2f}× maiores, o poder foi {strongest['rejection_proportion']['welch']:.1%} "
        f"no Welch e {strongest['rejection_proportion']['mann_whitney']:.1%} no Mann-Whitney"
        + (", que teve mais poder em todos os efeitos e tamanhos amostrais." if mw_always else ".")
    )
    if robustness is not None:
        out = robustness["scenarios"]["outlier_contamination"]["q1_type_i"]
        found += (
            f" Com outliers (Q3), o erro tipo I foi {float(out['welch']):.1%} no Welch e "
            f"{float(out['mann_whitney']):.1%} no Mann-Whitney, sem mudar o quadro."
        )
    lines.append(found)
    confirmed = (
        mw_always
        and all(_type_i_verdict(r, alpha, reps) == "compatível com α" for r in mw_q1)
        and max(welch_q1) < alpha
    )
    lines.append(
        "**A simulação confirmou a expectativa:** o Welch é conservador com esta cauda e, por isso, perde poder; "
        "o Mann-Whitney mantém o erro tipo I perto de α e detecta mais."
        if confirmed
        else "**A simulação confirmou a expectativa só em parte;** veja as seções 4 e 5."
    )
    lines.append(
        "**Recomendação:** usar Mann-Whitney como teste principal para comparar o tempo até o merge com e sem bot, "
        "e o Welch apenas como complemento quando a pergunta for sobre a média, ligada à espera total acumulada."
    )
    tie = _welch_ties_up_to(q1q2)
    lines.append(
        "**Quando a escolha mudaria:** "
        + (f"com tempos quase simétricos (σ de log até {tie:g}), o Welch empata ou supera o Mann-Whitney; " if tie else "")
        + "também se a decisão depender da média em horas, que só o Welch compara. Grupos com formatos diferentes "
        "não foram simulados e poderiam afastar o erro tipo I do Mann-Whitney de α."
    )
    row = _observed_row(q1q2, n_real)
    lines.append(
        f"**Principal limitação:** com {row['n_per_group']} PRs por grupo, o poder para um efeito do tamanho do "
        f"observado é de {row['rejection_proportion']['mann_whitney']:.0%} no Mann-Whitney; seriam necessários "
        f"{needed_n_text(q1q2, 'mann_whitney')} PRs por grupo para 80%. Além disso, os dados são observacionais: o uso do "
        "bot pode depender do próprio PR, então a comparação não mostra causalidade."
    )
    return "\n\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="Lab04 — Testes de hipótese", layout="wide")
    st.title("Testes de hipótese por dentro: Welch × Mann-Whitney")
    st.markdown(
        f"**Dashboard:** {DASHBOARD_LINK} · **Repositório / GitHub Projects:** {REPO_LINK} · **Método:** {METHOD_LINK}"
    )

    with st.sidebar:
        st.header("Parâmetros")
        csv_path = st.text_input("CSV de dados reais (group,value em horas)", str(DEFAULT_CSV))
        q3_path = st.text_input("Resultados Q3 (JSON)", str(ROOT / "lab04" / "data" / "q3_robustness.json"))
        q1q2_path = st.text_input(
            "Resultados Q1/Q2 por tamanho amostral (JSON)", str(ROOT / "lab04" / "data" / "q1_q2.json")
        )
        n = st.number_input("Observações simuladas por grupo", 2, 2000, 30)
        seed = st.number_input("Semente", 0, 10_000_000, 42)
        alpha = st.select_slider("Nível de significância α", [0.01, 0.05, 0.10], value=0.05)

    try:
        real = load_real(csv_path)
        simulated, result = simulate(real, int(n), int(seed), float(alpha))
    except (OSError, ValueError) as exc:
        st.error(f"Não foi possível carregar os dados: {exc}")
        st.stop()

    # A origem descrita só vale para a amostra da #61; outro CSV da barra lateral não a herda.
    source = f"{DATA_SOURCE} " if Path(csv_path).resolve() == DEFAULT_CSV.resolve() else ""
    groups = sorted(real)
    st.header("1. Cenário")
    st.markdown(
        f"**Pergunta:** {QUESTION}\n\n**H₀:** {H0}\n\n**H₁:** {H1}\n\n"
        f"**Dados reais:** {len(real[groups[0]])} observações em `{groups[0]}` e "
        f"{len(real[groups[1]])} em `{groups[1]}` (tempo até o merge, em horas), lidos de `{csv_path}`. {source}"
        "Testes comparados: t de Welch (médias) × Mann-Whitney (postos)."
    )

    st.header("2. Os dados")
    st.plotly_chart(fig_g1(real, simulated), width="stretch", theme=None)
    st.markdown(
        "O gráfico mostra, com os mesmos intervalos, o tempo até o merge de cada grupo nos dados reais "
        "e nos simulados. O eixo de horas está em escala logarítmica para que a cauda direita não comprima "
        "os PRs mais rápidos em um único intervalo. "
        + " ".join(f"Em `{g}` (real): {describe(real[g])}." for g in groups)
        + " Tempos positivos com cauda à direita (assimetria > 0) motivam a lognormal: cada grupo "
        "simulado usa a média e o desvio-padrão dos logaritmos do respectivo grupo real, "
        f"com semente {int(seed)}."
    )

    st.header("3. Como os testes funcionam")
    welch, mw = null_distributions(simulated, float(alpha), int(seed))
    st.plotly_chart(fig_g2(welch, mw, alpha=float(alpha)), width="stretch", theme=None)
    tests = result["tests"]
    st.markdown(
        f"O t de Welch compara médias e, sob H₀, a estatística t segue uma t de Student com "
        f"{welch.df:.1f} graus de liberdade; o Mann-Whitney compara postos e a distribuição de U sob H₀ "
        f"vem de {len(mw.u_null):,} permutações dos grupos. As regiões sombreadas nas duas caudas "
        f"(α = {alpha:.0%}) são onde H₀ é rejeitada. No exemplo simulado, t = {welch.t_obs:.2f} "
        f"(p = {welch.p_value:.3f}) e U = {mw.u_obs:.0f} (p = {mw.p_value:.3f} pela permutação; "
        f"{tests['mann_whitney']['p_value']:.3f} pela aproximação normal). "
        "O p-valor é a probabilidade, supondo H₀ verdadeira, de uma estatística tão extrema quanto a "
        "observada; não é a probabilidade de H₀ ser verdadeira. "
        f"Welch: {tests['welch']['interpretation']}. Mann-Whitney: {tests['mann_whitney']['interpretation']}."
    )

    st.header("4. Erro tipo I")
    robustness = None
    try:
        robustness = load_robustness(q3_path)
        scenarios = robustness["scenarios"]
        st.plotly_chart(fig_g3(robustness), width="stretch", theme=None)
        st.markdown(type_i_text(robustness))
        with st.expander("Ver tabela de Q1"):
            st.table([
                {
                    "Condição": label,
                    "Welch": f"{scenarios[key]['q1_type_i']['welch']:.1%}",
                    "Mann–Whitney": f"{scenarios[key]['q1_type_i']['mann_whitney']:.1%}",
                    "Alfa esperado": f"{robustness['alpha']:.0%}",
                }
                for key, label in (("lognormal_reference", "Referência lognormal"), ("outlier_contamination", "Com outliers"))
            ])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        robustness = None
        st.warning(f"Resultados de Q3 ainda não foram gerados ({exc}). Execute `python -m lab04`.")

    q1q2, complement = None, None
    try:
        q1q2 = load_robustness(q1q2_path)
        complement = fig_power_complement(q1q2)
        st.markdown(q1_by_n_text(q1q2))
        with st.expander("Ver erro tipo I por tamanho amostral (Q1)"):
            st.table([
                {
                    "PRs por grupo": row["n_per_group"],
                    "Welch": f"{row['rejection_proportion']['welch']:.1%}",
                    "Mann–Whitney": f"{row['rejection_proportion']['mann_whitney']:.1%}",
                }
                for row in q1q2["q1_type_i"]
            ])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        q1q2, complement = None, None
        st.warning(f"Resultados de Q1/Q2 por tamanho amostral ainda não foram gerados ({exc}). Execute `python -m lab04`.")

    st.header("5. Poder")
    if robustness is not None:
        st.plotly_chart(fig_g4(robustness), width="stretch", theme=None)
        st.markdown(power_text(robustness))
        with st.expander("Ver tabela de poder (Q2 e Q3)"):
            power_rows = []
            for ref_point, out_point in zip(scenarios["lognormal_reference"]["q2"], scenarios["outlier_contamination"]["q2"]):
                ref, out = ref_point["rejection_proportion"], out_point["rejection_proportion"]
                power_rows.append({
                    "Efeito log": f"{ref_point['effect_log_shift']:.2f}",
                    "Razão das medianas": f"{ref_point['second_group_median_ratio']:.2f}×",
                    "Welch referência": f"{ref['welch']:.1%}",
                    "MW referência": f"{ref['mann_whitney']:.1%}",
                    "Welch outliers": f"{out['welch']:.1%}",
                    "MW outliers": f"{out['mann_whitney']:.1%}",
                })
            st.dataframe(power_rows, hide_index=True, width="stretch")
    if complement is not None:
        st.plotly_chart(complement, width="stretch", theme=None)
        st.markdown(power_complement_text(q1q2, len(real[groups[0]])))
        with st.expander("Ver poder por tamanho amostral e por assimetria (Q2)"):
            st.dataframe([
                {
                    "PRs por grupo": row["n_per_group"],
                    "Efeito log": f"{row['effect_log_shift']:.2f}",
                    "Razão das medianas": f"{row['median_ratio']:.2f}×",
                    "Welch": f"{row['rejection_proportion']['welch']:.1%}",
                    "Mann–Whitney": f"{row['rejection_proportion']['mann_whitney']:.1%}",
                }
                for row in q1q2["q2_power"]
            ], hide_index=True, width="stretch")
            st.dataframe([
                {
                    "σ de log": f"{row['sigma_log_hours']:.2f}" + (" (dados reais)" if row["is_real_fit"] else ""),
                    "Erro tipo I Welch": f"{row['type_i']['welch']:.1%}",
                    "Erro tipo I MW": f"{row['type_i']['mann_whitney']:.1%}",
                    "Poder Welch": f"{row['power']['welch']:.1%}",
                    "Poder MW": f"{row['power']['mann_whitney']:.1%}",
                }
                for row in q1q2["skewness_sensitivity"]["rows"]
            ], hide_index=True, width="stretch")
    if robustness is not None:
        st.subheader("Limitações de Q1–Q3")
        st.markdown(
            "\n".join(
                f"- {item}"
                for item in [*robustness.get("limitations", []), *(q1q2 or {}).get("limitations", [])]
            )
            + f"\n- Resultados reproduzíveis com `python -m lab04 --seed {robustness['seed']} "
            f"--n-per-group {robustness['n_per_group']} --repetitions {robustness['repetitions']}` "
            "(semente fixa; mesmos dados, mesmos números)."
        )
    st.header("6. Dados reais")
    analysis = analyze_real_groups(real, alpha=float(alpha))
    st.table(real_table(analysis))
    st.markdown(real_data_text(analysis, real, q1q2))
    st.header("7. Conclusão")
    st.markdown(conclusion_text(q1q2, robustness, len(real[groups[0]])))


main()
