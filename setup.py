from setuptools import setup, find_packages

setup(
    name="finpulse",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv",
        "pandas",
        "numpy",
        "tqdm",
        "google-generativeai",
        "langchain",
        "chromadb",
        "sentence-transformers",
        "matplotlib",
        "streamlit"
    ],
    python_requires=">=3.8",
)
