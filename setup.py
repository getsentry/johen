from setuptools import find_packages, setup


def get_requirements(file: str):
    with open(file) as fp:
        return [x.strip() for x in fp.read().split("\n") if not x.startswith("#")]


setup(
    name="johen",
    version=open("version").read().strip(),
    package_dir={"": "src"},
    package_data={"johen": ["py.typed"]},
    packages=find_packages(where="src"),
    install_requires=[],
    setup_requires=[],
    tests_require=get_requirements("test-requirements.txt"),
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pytest",
        "Topic :: Software Development :: Testing",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development",
    ],
    entry_points={"pytest11": ["johen = johen.pytest"]},
)
