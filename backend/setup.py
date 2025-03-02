from setuptools import setup, find_packages

setup(
    name="backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.8",
        "uvicorn>=0.34.0",
        "sqlalchemy>=2.0.38",
        "alembic>=1.14.1",
        "psycopg2-binary>=2.9.10",
        "pydantic>=2.10.6",
        "pydantic-settings>=2.7.1",
    ],
) 