"""C4: the version the package reports is the version of the installed distribution."""

from importlib.metadata import version

import GarimpoInvestimentos


def test_package_version_matches_installed_distribution():
    assert GarimpoInvestimentos.__version__ == version("cripto-predictor")
