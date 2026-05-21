# Stub spacy CLI runner to bypass the 'python -m spacy download' build command on Render
import sys

if __name__ == "__main__":
    print("Stub spacy download command bypassed successfully!")
    sys.exit(0)
