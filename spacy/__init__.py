# Stub spacy init to gracefully bypass spacy dependencies in production
nlp = None
USE_SPACY = False

def load(*args, **kwargs):
    raise ImportError("Stub spacy")
