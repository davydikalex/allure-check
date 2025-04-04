from setuptools import setup, find_packages

setup(
    name='allure_check',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'allure_check = allure_check:main',
        ],
    },
)