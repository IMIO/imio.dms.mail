# -*- coding: utf-8 -*-
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.i18n import translate
from z3c.table.column import Column, LinkColumn
from Products.CMFPlone.utils import safe_unicode
from collective.dms.basecontent.browser.column import IconColumn
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.task import _ as _task
from imio.dms.mail import _

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


class GenerationColumn(LinkColumn, IconColumn):
    header = ""
    weight = 25  # before author = 30
    iconName = "++resource++imio.dms.mail/mailing.gif"

    def getLinkURL(self, item):
        """Setup link url."""
        url = item.getURL()
        om_url = url.rsplit('/', 1)[0]
        # must use new view with title given and reference to mailing template
        return '%s/@@persistent-document-generation?template_uid=%s&output_format=odt' % (om_url, item.UID)

    def getLinkContent(self, item):
        return u"""<img title="%s" src="%s" />""" % (_(u"Mailing"), '%s/%s' % (self.table.portal_url, self.iconName))


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
