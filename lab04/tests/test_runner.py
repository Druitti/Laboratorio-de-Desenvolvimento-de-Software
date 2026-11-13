from types import SimpleNamespace

from lab04 import __main__ as runner


def test_entrypoint_validates_generates_outputs_and_starts_dashboard(monkeypatch):
    modules = []
    commands = []
    monkeypatch.setattr(runner, "_run_module", lambda module, *args: modules.append((module, args)))
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, **kwargs: commands.append((command, kwargs)) or SimpleNamespace(returncode=0),
    )

    assert runner.main(["--seed", "7", "--n-per-group", "40", "--repetitions", "1200"]) == 0
    assert [module for module, _ in modules] == ["lab04.real_data", "lab04.simulation", "lab04.power", "lab04.robustness"]
    assert "7" in modules[1][1] and "40" in modules[1][1]
    assert "1200" in modules[2][1] and "7" in modules[2][1]
    assert "1200" in modules[3][1]
    assert commands[0][0][1:4] == ["-m", "streamlit", "run"]
