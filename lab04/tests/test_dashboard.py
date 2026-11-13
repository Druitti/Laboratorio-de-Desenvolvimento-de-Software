from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"
TIMEOUT_SECONDS = 180


def scenario_text(app):
    return next(block.value for block in app.markdown if "**Pergunta:**" in block.value)


@pytest.fixture
def app():
    return AppTest.from_file(str(DASHBOARD), default_timeout=TIMEOUT_SECONDS).run()


def test_dashboard_opens_with_the_real_sample(app):
    assert not app.exception
    assert not app.error
    assert not app.warning
    assert len(app.get("plotly_chart")) == 4  # G1 a G4
    scenario = scenario_text(app)
    assert "30 observações em `with_review_bot` e 30 em `without_review_bot`" in scenario
    assert "API GraphQL do GitHub" in scenario
    header_links = next(block.value for block in app.markdown if "**Dashboard:**" in block.value)
    assert "http://localhost:8501" in header_links
    assert "github.com/users/Druitti/projects/5" in header_links
    assert len(app.get("dataframe")) >= 1


def test_other_csv_does_not_inherit_the_origin_of_the_real_sample(app, tmp_path):
    path = tmp_path / "outro.csv"
    path.write_text("group,value\na,1\na,2\nb,3\nb,4\n", encoding="utf-8")
    app.text_input[0].set_value(str(path)).run()
    assert not app.exception
    assert "API GraphQL do GitHub" not in scenario_text(app)


def test_g3_and_g4_come_with_explanatory_text(app):
    texts = [block.value for block in app.markdown]
    type_i = next(t for t in texts if "proporção de rejeições de H₀ quando ela é verdadeira" in t)
    power = next(t for t in texts if "quando o 2º grupo tem mediana" in t)
    assert "Welch:" in type_i and "Mann-Whitney:" in type_i and "α = 5%" in type_i
    assert "vantagem" in power and "Welch" in power
    assert "#66" not in " ".join(c.value for c in app.caption)


def test_dashboard_warns_when_q3_results_are_missing(app, tmp_path):
    app.text_input[1].set_value(str(tmp_path / "nao_existe.json")).run()
    assert not app.exception
    assert any("Q3" in w.value for w in app.warning)
    assert len(app.get("plotly_chart")) == 2
