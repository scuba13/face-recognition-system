from setuptools import setup, find_packages

setup(
    name="linha",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "opencv-python>=4.8.0",
        "face-recognition>=1.3.0",
        "pymongo>=4.3.3",
        "numpy>=1.24.3",
        "backoff>=2.2.1"
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
        ]
    },
    python_requires=">=3.9",
) 