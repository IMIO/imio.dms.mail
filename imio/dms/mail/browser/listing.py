from plone.app.uuid.utils import uuidToObject
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from DateTime import DateTime


class ListingView(BrowserView):
    """
        View intended to list daily incoming mail for a mail type
    """

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.pc = getToolByName(context, 'portal_catalog')

    def findIncomingMails(self, mail_type='', start_date=''):
        """
            Request the catalog
            mail_type :
            start_date : string date at format YYYYMMDD
        """
        kw = {}
        kw['portal_type'] = ('dmsincomingmail',)
        #kw['review_state'] = ('published',)
        kw['created'] = {"query": [DateTime()-5, ], "range": "min"}
#        kw['modified'] = {"query": [DateTime()-5, ], "range": "min"}
#        kw['sort_on'] = 'created'
        results = {'1_no_group': {'mails': [], 'title': 'listing_no_group'}}
        if not start_date:
            start_date = DateTime().strftime('%Y%m%d')
        for brain in self.pc(kw):
            obj = brain.getObject()
            if mail_type and obj.mail_type.encode('utf8') != mail_type:
                continue
            if obj.reception_date.strftime('%Y%m%d') < start_date:
                continue
            if obj.treating_groups:
                for tg in obj.treating_groups:
                    if not tg in results:
                        results[tg] = {'mails': []}
                        title = tg
                        tgroup = uuidToObject(tg)
                        if tgroup is not None:
                            title = tgroup.get_full_title(separator=' - ', first_index=1)
                        results[tg]['title'] = title
                    results[tg]['mails'].append(obj)
            else:
                results['1_no_group']['mails'].append(obj)
        if not results['1_no_group']['mails']:
            del results['1_no_group']
        for service in results.keys():
            results[service]['mails'].sort(lambda x, y: cmp(x.internal_reference_no, y.internal_reference_no))
        return results
