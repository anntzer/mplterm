from setuptools import setup, find_namespace_packages


setup(
    name="mplterm",
    description="a terminal backend for Matplotlib",
    long_description=open("README.rst", encoding="utf-8").read(),
    long_description_content_type="text/x-rst",
    author="Antony Lee",
    author_email="",
    url="https://github.com/anntzer/mplterm",
    license="zlib",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Matplotlib",
        "License :: OSI Approved :: zlib/libpng License",
        "Programming Language :: Python :: 3",
    ],
    packages=find_namespace_packages("lib"),
    package_dir={"": "lib"},
    python_requires=">=3.8",
    setup_requires=["setuptools_scm>=3.3"],  # fallback_version support.
    use_scm_version=lambda: {
        "version_scheme": "post-release",
        "local_scheme": "node-and-date",
        "fallback_version": "0+unknown",
    },
    install_requires=[
        "matplotlib>=3.0",
    ],
)
