from setuptools import find_packages, setup

__version__ = '0.0.1'


setup(
    name='ltssched',
    version=__version__,
    description='Long task scheduler',
    long_description='Library for run FSM on external/scheduled events',
    long_description_content_type='text/plain',
    url="https://github.com/antipooh/ltsched",
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    author='Oleg Komkov',
    install_requires=[],
    extras_require={
    },
    author_email='okomkov@gmail.com',
)
