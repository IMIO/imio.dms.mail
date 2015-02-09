#! -*- coding: utf8 -*-

from setuptools import setup, find_packages

version = '0.3'

long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(name='imio.dms.mail',
      version=version,
      description="Imio dms mail",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.2",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.communesplone.org/svn/communesplone/imio.dms.mail',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['imio', 'imio.dms'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Plone',
          'Products.PasswordStrength > 0.3.1',
          'plone.app.dexterity[grok]',
          'collective.dms.basecontent',
          'collective.dms.mailcontent',
          'collective.dms.batchimport',
          'collective.contact.core',
          'collective.contact.plonegroup',
          'collective.task',
          'collective.externaleditor',
          'collective.dms.scanbehavior',
          'communesplone.layout',
          'dexterity.localrolesfield',
          'imio.helpers',
          'imio.migrator',
          'plonetheme.imioapps',
          # -*- Extra requirements: -*-
      ],
      extras_require={'test':
        ['plone.app.testing',
         'unittest2',
         'plone.app.robotframework',
         'plonetheme.imioapps',]},
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
