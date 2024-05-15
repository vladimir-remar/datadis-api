
from setuptools import find_packages, setup


MAIN_REQUIREMENTS = [
    "requests",
    "backoff",
]

TEST_REQUIREMENTS = [
    "requests-mock~=1.9.3",
    "pytest~=6.2",
    "pytest-mock~=3.6.1",
]

setup(
    name="datadis",
    description="Datadis API Inplementation.",
    author="Vladimir",
    author_email="vladimir.remar@gmail.com",
    packages=find_packages(),
    install_requires=MAIN_REQUIREMENTS,
    package_data={"": ["*.json", "*.yaml", "schemas/*.json", "schemas/shared/*.json"]},
    extras_require={
        "tests": TEST_REQUIREMENTS,
    },
)
