from setuptools import setup, find_packages

setup(
    name="mlflow-light-auth",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "mlflow.app": [
            "light-auth=light_auth:create_app",
        ],
    },
)
