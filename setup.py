from setuptools import setup, find_packages

setup(
    name='potatotime',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
        # e.g., 'numpy', 'requests'
    ],
    entry_points={
        'console_scripts': [
            # Define command-line scripts if needed
            # 'your_command=your_module:main_function'
        ],
    },
)