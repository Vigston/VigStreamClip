import openai
from pathlib import Path

def load_api_key_from_file() -> str:
    # 現在のスクリプトの一つ上のディレクトリの assets/openai_key.txt を参照
    key_path = Path(__file__).resolve().parent.parent / "assets" / "openai_key.txt"
    with open(key_path, "r", encoding="utf-8") as f:
        return f.readline().strip()

openai.api_key = load_api_key_from_file()

for model in openai.models.list():
    print(model.id)