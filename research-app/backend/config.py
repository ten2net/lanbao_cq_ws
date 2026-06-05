import os

HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://192.168.15.131:8642")
YAML_PATH = os.getenv("YAML_PATH", "/app/data/prompts.yaml")
