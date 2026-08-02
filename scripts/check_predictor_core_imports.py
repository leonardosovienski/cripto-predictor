import importlib.util


def main() -> int:
    installed = importlib.util.find_spec("predictor_core") is not None
    print("predictor_core package installed" if installed else "predictor_core package missing")
    return 0 if installed else 1


if __name__ == "__main__":
    raise SystemExit(main())
