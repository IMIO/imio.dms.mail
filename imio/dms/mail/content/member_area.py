# -*- coding: utf-8 -*-
from imio.dms.mail.interfaces import IMemberAreaFolder
from plone.dexterity.content import Container
from zope.interface import implements


class MemberArea(Container):
    """
        MemberArea class
    """
    implements(IMemberAreaFolder)
