from setuptools import setup

version = '0.1dev'

long_description = '\n\n'.join([
    open('README.rst').read(),
    open('CREDITS.rst').read(),
    open('CHANGES.rst').read(),
    ])

install_requires = [
    'Django',
    'django-extensions',
    'django-nose',
    'django-appconf',
    'lizard-map',
    'lizard-ui >= 4.0b5',
    'netCDF4',
    'recordtype',
    'pytz',
    ],

tests_require = [
    'nose',
    'coverage',
    'mock',
    ]

setup(name='lizard-ocean',
      version=version,
      description="Django app for showing png and netcdf ocean monitoring data",
      long_description=long_description,
      # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Programming Language :: Python',
                   'Framework :: Django',
                   ],
      keywords=[],
      author='Reinout van Rees',
      author_email='reinout.vanrees@nelen-schuurmans.nl',
      url='',
      license='GPL',
      packages=['lizard_ocean'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=tests_require,
      extras_require={'test': tests_require},
      entry_points={
          'console_scripts': [
          ],
      },
  )
