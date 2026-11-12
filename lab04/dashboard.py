"""Dashboard do Lab04 (Streamlit). Execute: ``streamlit run lab04/dashboard.py``."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import streamlit as st
from scipy import stats

# `streamlit run lab04/dashboard.py` põe lab04/ no sys.path, não a raiz do repo.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab04.null_dist import mannwhitney_null, split_groups, welch_null  # noqa: E402
from lab04.plots import fig_g1, fig_g2  # noqa: E402
from lab04.simulation import compare_groups, read_real_samples, simulate_groups  # noqa: E402

DEFAULT_CSV = ROOT / "lab04" / "data" / "real_prs.csv"
DATA_SOURCE = (
    "PRs mergeados de autores humanos, criados no 1º semestre de 2026, nos 500 repositórios públicos com mais "
    "estrelas, coletados pela API GraphQL do GitHub. Cada PR vem de um repositório diferente, sorteado com "
    "semente fixa (método e limitações em `docs/lab04/cenario-dados.md`)."
)
DASHBOARD_LINK = "[http://localhost:8501](http://localhost:8501)"
REPO_LINK = (
    "[repositório](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software) · "
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
        f"(p = {tests['welch']['p_value']:.3f}) e U = {mw.u_obs:.0f} (p = {tests['mann_whitney']['p_value']:.3f}). "
        "O p-valor é a probabilidade, supondo H₀ verdadeira, de uma estatística tão extrema quanto a "
        "observada; não é a probabilidade de H₀ ser verdadeira. "
        f"Welch: {tests['welch']['interpretation']}. Mann-Whitney: {tests['mann_whitney']['interpretation']}."
    )

    st.header("4. Erro tipo I")
    robustness = None
    try:
        robustness = load_robustness(q3_path)
        scenarios = robustness["scenarios"]
        q1_rows = []
        for key, label in (("lognormal_reference", "Referência lognormal"), ("outlier_contamination", "Com outliers")):
            rates = scenarios[key]["q1_type_i"]
            q1_rows.append({
                "Condição": label,
                "Welch": f"{rates['welch']:.1%}",
                "Mann–Whitney": f"{rates['mann_whitney']:.1%}",
                "Alfa esperado": f"{robustness['alpha']:.0%}",
            })
        st.table(q1_rows)
        st.caption(
            f"Q1: {robustness['repetitions']:,} repetições por condição, "
            f"n={robustness['n_per_group']} por grupo, semente {robustness['seed']}. "
            "G3 — visualização por situação, com linha de 5% — está na #66."
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.warning(f"Resultados de Q3 ainda não foram gerados ({exc}). Execute `python -m lab04`.")

    st.header("5. Poder")
    if robustness is not None:
        ref_curve = scenarios["lognormal_reference"]["q2"]
        out_curve = scenarios["outlier_contamination"]["q2"]
        power_rows = []
        for ref_point, out_point in zip(ref_curve, out_curve):
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
        st.caption("Q2/Q3: poder em função do efeito simulado. G4 — curvas de poder — está na #66.")
        st.markdown(robustness["interpretation"])
    st.header("6. Dados reais")
    st.info("Tabela com estatística, p-valor, tamanho do efeito e conclusão: entrega final.")
    st.header("7. Conclusão")
    st.info("Expectativa × resultado e recomendação: entrega final.")


main()
