# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from collective.contact.core.content.person import IPerson
from collective.z3cform.chosen.widget import AjaxChosenFieldWidget
from imio.dms.mail import _
from plone.autoform import directives
from plone.dexterity.schema import DexteritySchemaPolicy
from zope import schema


class IDmsPerson(IPerson):

    userid = schema.Choice(
        title=_(u'Plone user'),
        required=False,
        vocabulary=u'plone.app.vocabularies.Users',
    )

    #directives.widget('userid', AjaxChosenFieldWidget, populate_select=True)
    directives.read_permission(userid='imio.dms.mail.write_userid_field')
    directives.write_permission(userid='imio.dms.mail.write_userid_field')


class DmsPersonSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IDmsPerson, )
