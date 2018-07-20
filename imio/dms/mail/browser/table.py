# -*- coding: utf-8 -*-
from collective.dms.basecontent.browser.column import IconColumn
from collective.dms.basecontent.browser.listing import VersionsTable
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task import _ as _task
from imio.dms.mail import _
from imio.dms.mail.setuphandlers import _ as _t
from Products.CMFPlone.utils import safe_unicode
from z3c.table.column import Column
from z3c.table.column import LinkColumn
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory


# z3c.table standard columns


class IMVersionsTitleColumn(VersionsTitleColumn):

    def getLinkTitle(self, item):
        obj = item.getObject()
        if not IScanFields.providedBy(obj):
            return
        scan_infos = [
            ('scan_id', item.scan_id or ''),
            ('scan_date', obj.scan_date and obj.toLocalizedTime(obj.scan_date, long_format=1) or ''),
            ('Version', obj.version or ''),
        ]
        scan_infos = ["%s: %s" % (
            translate(name, domain='collective.dms.scanbehavior', context=item.REQUEST), value)
            for (name, value) in scan_infos]

        return 'title="%s"' % '\n'.join(scan_infos)

    def getLinkContent(self, item):
        iconName = "++resource++imio.dms.mail/itemIsSignedYes.png"
        content = super(VersionsTitleColumn, self).getLinkContent(item)
        if item.signed:
            return u"""%s <img title="%s" src="%s" />""" % (
                content,
                translate(u"Signed version", domain='collective.dms.basecontent', context=item.REQUEST),
                '%s/%s' % (self.table.portal_url, iconName))
        else:
            return content


'''
Choose to add icon at end of filename
class OMSignedColumn(Column):

    weight = 25  # before author = 30

    def renderCell(self, item):
        iconName = "++resource++imio.dms.mail/itemIsSignedYes.png"
        if item.signed:
            return u"""<img title="%s" src="%s" />""" % (
                translate(u"Signed version", domain='collective.dms.basecontent', context=item.REQUEST),
                '%s/%s' % (self.table.portal_url, iconName))
        else:
            return ""
'''


class GenerationColumn(LinkColumn, IconColumn):
    header = ""
    weight = 12  # before label = 15
    iconName = "++resource++imio.dms.mail/mailing.gif"

    def getLinkURL(self, item):
        """Setup link url."""
        url = item.getURL()
        om_url = url.rsplit('/', 1)[0]
        # must use new view with title given and reference to mailing template
        return '%s/@@mailing-loop-persistent-document-generation?document_uid=%s' % (om_url, item.UID)

    def getLinkContent(self, item):
        return u"""<img title="%s" src="%s" />""" % (_t(u"Mailing"), '%s/%s' % (self.table.portal_url, self.iconName))

    def has_mailing(self, item):
        obj = item.getObject()
        annot = IAnnotations(obj)
        if 'documentgenerator' in annot and annot['documentgenerator']['need_mailing']:
            return True
        return False

    def renderCell(self, item):
        if not self.has_mailing(item):
            return ''
        return super(GenerationColumn, self).renderCell(item)


class EnquirerColumn(Column):

    """Column that displays enquirer group."""

    header = _task("Enquirer")
    weight = 30

    def renderCell(self, item):
        if not item.enquirer:
            return ''
        factory = getUtility(IVocabularyFactory, 'collective.task.Enquirer')
        voc = factory(item)
        return safe_unicode(voc.getTerm(item.enquirer).title)


class AssignedGroupColumn(Column):

    """Column that displays assigned group."""

    header = _("Treating groups")
    weight = 30

    def renderCell(self, item):
        if not item.assigned_group:
            return ''
        factory = getUtility(IVocabularyFactory, 'collective.task.AssignedGroups')
        voc = factory(item)
        return safe_unicode(voc.getTerm(item.assigned_group).title)


class OMVersionsTable(VersionsTable):
    pass
