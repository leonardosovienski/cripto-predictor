"""Reserved adapter_paths of the crypto research contract (C24.1).

Stage B (integration) may add envelope/transport adapters here. Rules enforced by
tests/conformance/test_import_closure.py:
  1. nothing reachable from an entrypoint of the domain imports this package;
  2. nothing outside this package imports from it;
  3. adapters call the domain only through GarimpoInvestimentos.research_runner.Circuit
     (the adapter_api), the same path as the `cripto-research` entrypoint.
Stage A ships this package empty on purpose.
"""
