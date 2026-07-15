def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "counters: asserts eval_count patterns (R10/R20/R23/R24/R27); "
        "excluded from the self-test — the naive reference does not model "
        "counters")
