#! -*- coding: utf-8 -*-

from setuptools import find_packages
from setuptools import setup


version = "3.0.dev0"

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
        "Framework :: Plone :: 4.3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="dms document management system",
    author="sgeulette",
    author_email="support-docs@imio.be",
    url="https://github.com/imio/imio.dms.mail",
    download_url="https://devpi.imio.be/root/imio/imio.dms.mail",
    license="GPL",
    packages=find_packages(exclude=["ez_setup"]),
    namespace_packages=["imio", "imio.dms"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "setuptools",
        "Plone",
        "Products.CPUtils",
        "Products.PasswordStrength",
        "collective.ckeditor",
        "collective.ckeditortemplates",
        "collective.classification.folder",
        "collective.collabora>=1.1.0.dev0",
        "collective.contact.core",
        "collective.contact.contactlist",
        "collective.contact.duplicated",
        "collective.contact.facetednav",
        "collective.contact.importexport",
        "collective.contact.plonegroup",
        "collective.dexteritytextindexer",
        "collective.dms.basecontent",
        "collective.dms.batchimport",
        "collective.dms.mailcontent",
        "collective.dms.scanbehavior",
        "collective.documentgenerator",
        "collective.externaleditor",
        "collective.fontawesome",
        "collective.iconifieddocumentactions",
        "collective.js.fancytree",
        "collective.js.tooltipster",
        "collective.messagesviewlet",
        "collective.portlet.actions",
        "collective.querynextprev",
        "collective.relationhelpers",
        #          'collective.schedulefield',
        "collective.task",
        "collective.wfadaptations",
        "collective.z3cform.select2",
        "communesplone.layout",
        "dexterity.localrolesfield",
        "ftw.labels",
        "imio.dashboard",
        "imio.dms.soap2pm",
        "imio.pm.wsclient>=2",
        "imio.fpaudit",
        "imio.helpers",
        "imio.migrator",
        "imio.zamqp.core",
        "natsort",
        "plone.app.dexterity[grok]",
        "plone.app.lockingbehavior",
        "plonetheme.imioapps",
        "Products.cron4plone",
        "Products.PluggableAuthService>=1.11.3",
        "z3c.unconfigure",
        # -*- Extra requirements: -*-
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            "plone.app.robotframework",
            "plone.mocktestcase",
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
