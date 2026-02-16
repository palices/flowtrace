"""Sample that triggers an error inside a nested call (not at the entry point).

Run with:
    python flowtrace.py -s samples/error/error_internal_sample.py -o fwt_error_internal.json
"""


def load_config():
    # Pretend we read a config; missing threshold on purpose
    return {"mode": "fast"}


def validate_config(cfg: dict):
    if "threshold" not in cfg:
        raise KeyError("Config missing 'threshold'")
    if cfg["threshold"] <= 0:
        raise ValueError("threshold must be positive")
    return cfg


def run_pipeline():
    cfg = load_config()
    valid_cfg = validate_config(cfg)  # raises KeyError here
    return {"status": "ok", "config": valid_cfg}


if __name__ == "__main__":
    result = run_pipeline()
    print(result)
