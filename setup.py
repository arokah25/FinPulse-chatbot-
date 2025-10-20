from setuptools import setup, find_packages

setup(
    name="finpulse",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pandas>=2.0.0",
        "google-generativeai>=0.1.0rc1",
        "langchain>=0.3.0",
        "gradio>=4.0.0"
    ],
    python_requires=">=3.8",
)
