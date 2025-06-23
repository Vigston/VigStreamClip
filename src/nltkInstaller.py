import nltk
from nltk.data import find

def ensure_nltk_resources():
    nltk_data_path = "C:/Users/Amaou/AppData/Roaming/nltk_data"
    nltk.data.path.append(nltk_data_path)
    
    try:
        find("tokenizers/punkt")
        print("✅ punkt is already available.")
    except LookupError:
        print("⬇️ Downloading punkt...")
        nltk.download("punkt", download_dir=nltk_data_path)
        try:
            find("tokenizers/punkt")
            print("✅ punkt successfully downloaded.")
        except LookupError:
            raise RuntimeError("❌ Failed to load punkt even after download.")

# 呼び出し
ensure_nltk_resources()