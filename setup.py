from distutils.core import setup

setup(
    name='generator',
    version='0.1.0',
    author='Mika Hänninen',
    author_email='mika.hanninen@gmail.com',
    scripts=['rfgen.py'],
    download_url='https://github.com/robotframework/Generator/tarball/master',
    url='http://github.com/robotframework/Generator/',
    license='LICENSE.txt',
    description='Script which generates a test project containing test libraries, test suites and resources.',
    long_description=open('README.md').read(),
)