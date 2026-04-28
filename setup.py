import setuptools

setuptools.setup(
    name="plfluidics",
    version="0.1.0",
    author="Robert R. Puccinelli",
    author_email="robert.puccinelli@outlook.com",
    description="Microfluidic control utilities.",
    url="https://github.com/robertpuccinelli/microfluidic-software.git",
    python_requires='>=3.10',
    packages=setuptools.find_packages(exclude=["*.tests", "*.tests.*",
                                               "tests.*", "tests"]),
    package_data={'plfluidics':['server/configs/*', 
                                'server/scripts/*',
                                'server/templates/*']},
    include_package_data=True,
    install_requires=[
        'flask==3.1.1',
        'flask-socketio==5.5.1',
        'ftd2xx==1.3.8',
        'ft4222==1.12.0',
        'waitress==3.0.2',
        'eventlet==0.40.2',
    ],
    test_suite="tests",
)
