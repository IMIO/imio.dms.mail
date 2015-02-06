# -*- coding: utf-8 -*-
from zope.i18n import translate
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields


class VersionsTitleColumn(VersionsTitleColumn):

    def getLinkTitle(self, item):
        obj = item.getObject()
        if not IScanFields.providedBy(obj):
            return
        scan_infos = [
            ('scan_id', item.scan_id or ''),
            ('scan_date', obj.scan_date and item.toLocalizedTime(obj.scan_date, long_format=1) or ''),
#            ('scan_user', getattr(item, 'scan_user', '')),
        ]
        scan_infos = ["%s: %s" % (
            translate(name, domain='collective.dms.scanbehavior', context=item.REQUEST), value)
            for (name, value) in scan_infos]

        return 'title="%s"' % '\n'.join(scan_infos)
