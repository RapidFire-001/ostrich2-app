from setuptools import setup

setup(
    name="ostrich2-app",
    version="0.1.0",
    description="Desktop and command line tools for the Moates Ostrich 2.0",
    packages=["ostrich2"],
    install_requires=["pyserial==3.5"],
    python_requires=">=3.12",
    scripts=["ostrich2.py"],
    author="Martin Strand",
    maintainer="Rapidfire",
    license="MIT",
    license_files=["LICENSE", "NOTICE.md", "provenance/upstream-setup.py.txt"],
    # Original author and public-domain declaration are preserved in
    # provenance/upstream-setup.py.txt. MIT applies to the new contributions;
    # NOTICE.md explains scope and does not relicense upstream/third-party work.
)
