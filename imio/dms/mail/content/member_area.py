# -*- coding: utf-8 -*-
from imio.dms.mail.interfaces import IMemberAreaFolder
from plone.dexterity.content import Container
from zope.interface import implementer


@implementer(IMemberAreaFolder)
class MemberArea(Container):
    """
    MemberArea class
    """

