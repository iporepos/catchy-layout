from losalamos.documents import DocumentTeX
from pathlib import Path


if __name__ == '__main__':

    print("Compiling documents...")
    mock_main = Path("./main.tex")

    document = DocumentTeX()
    document.load_data(mock_main)
    document.to_pdf(cleanup=True)

    print("OK")

