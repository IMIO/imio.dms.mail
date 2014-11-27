# -*- coding: utf-8 -*-
from zope.i18n import translate
from collective.dms.basecontent.browser.listing import VersionsTitleColumn


class VersionsTitleColumn(VersionsTitleColumn):

    def getLinkTitle(self, item):
        scan_infos = [
            ('scan_id', getattr(item, 'scan_id', '')),
            ('scan_date', item.toLocalizedTime(getattr(item, 'scan_date'), long_format=1)),
#            ('scan_user', getattr(item, 'scan_user', '')),
        ]
        scan_infos = ["%s: %s" % (
            translate(name, domain='collective.dms.scanbehavior', context=item.REQUEST), value)
            for (name, value) in scan_infos]

        return 'title="%s"' % '\n'.join(scan_infos)
