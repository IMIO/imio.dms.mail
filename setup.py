#! -*- coding: utf8 -*-

from setuptools import find_packages
from setuptools import setup


version = "4.0.0.dev0"

long_description = (
    open("README.rst").read() + "\n" + "Contributors\n"
    "============\n" + "\n" + open("CONTRIBUTORS.rst").read() + "\n" + open("CHANGES.rst").read() + "\n"
)

setup(
    name="imio.dms.mail",
    version=version,
    description="Imio dms mail",
    long_description=long_description,
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 6.2",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="dms document management system",
    author="sgeulette",
    author_email="support-docs@imio.be",
    url="https://github.com/imio/imio.dms.mail",
    download_url="https://devpi.imio.be/root/imio/imio.dms.mail",
    license="GPL",
    packages=find_packages(exclude=["ez_setup"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "setuptools",
        "Plone",
        "Products.CPUtils",
        "Products.PasswordStrength",
        "collective.classification.folder",
        "collective.contact.core",
        "collective.contact.contactlist",
        "collective.contact.duplicated",
        "collective.contact.facetednav",
        "collective.contact.importexport",
        "collective.contact.plonegroup",
        "collective.dms.basecontent",
        "collective.dms.batchimport",
        "collective.dms.mailcontent",
        "collective.dms.scanbehavior>1.3.1",
        "collective.documentgenerator",
        "collective.externaleditor",
        "collective.iconifiedcategory",
        "collective.js.fancytree",
        "collective.js.tooltipster",
        "collective.labels",
        "collective.messagesviewlet",
        "collective.querynextprev",
        "collective.relationhelpers",
        # "collective.schedulefield",
        "collective.task",
        "collective.wfadaptations",
        "communesplone.layout",
        "dexterity.localrolesfield",
        "imio.dashboard",
        "imio.pm.wsclient>=2",
        "imio.esign>=1.0.2",
        "imio.fpaudit",
        "imio.helpers[pdf]",
        "imio.migrator",
        "natsort",
        "plone.app.dexterity",
        "plone.app.lockingbehavior",
        "plonetheme.imioapps",
        "Products.PluggableAuthService>=1.11.3",
        "six",
        "z3c.unconfigure",
        # -*- Extra requirements: -*-
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            "plone.app.robotframework",
            "profilehooks",
            "plonetheme.imioapps",
        ]
    },
    entry_points="""
    # -*- Entry points: -*-

    [z3c.autoinclude.plugin]
    target = plone
    """,
)
