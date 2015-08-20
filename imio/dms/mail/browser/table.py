# -*- coding: utf-8 -*-
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.i18n import translate
from z3c.table.column import Column
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from collective.eeafaceted.z3ctable.columns import VocabularyColumn, MemberIdColumn
from imio.dashboard.browser.overrides import IDFacetedTableView
from imio.dms.mail import _

# collective.eeafaceted.z3ctable columns


class FolderFacetedTableView(IDFacetedTableView):
    """ Override of faceted-table-view for Folder (incomingmail) """

    def _manualColumnFor(self, colName):
        """Manage our own columns."""
        if colName == u'treating_groups':
            column = VocabularyColumn(self.context, self.request, self)
            column.vocabulary = u'collective.dms.basecontent.treating_groups'
        elif colName == u'assigned_user':
            column = MemberIdColumn(self.context, self.request, self)
            column.attrName = u'assigned_user'
        else:
            column = super(FolderFacetedTableView, self)._manualColumnFor(colName)

        return column

# z3c.table standard columns


class VersionsTitleColumn(VersionsTitleColumn):

    def getLinkTitle(self, item):
        obj = item.getObject()
        if not IScanFields.providedBy(obj):
            return
        scan_infos = [
            ('scan_id', item.scan_id or ''),
            ('scan_date', obj.scan_date and obj.toLocalizedTime(obj.scan_date, long_format=1) or ''),
#            ('scan_user', getattr(item, 'scan_user', '')),
        ]
        scan_infos = ["%s: %s" % (
            translate(name, domain='collective.dms.scanbehavior', context=item.REQUEST), value)
            for (name, value) in scan_infos]

        return 'title="%s"' % '\n'.join(scan_infos)


class AssignedGroupColumn(Column):

    """Column that displays assigned group."""

    header = _("Treating groups")
    weight = 30

    def renderCell(self, item):
        if not item.assigned_group:
            return ''
        factory = getUtility(IVocabularyFactory, 'collective.task.AssignedGroups')
        voc = factory(item)
        return voc.getTerm(item.assigned_group).title
