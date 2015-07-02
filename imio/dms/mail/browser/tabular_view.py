from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from plone import api
from Products.Five import BrowserView
from imio.dms.mail.setuphandlers import _


class TabularView(BrowserView):
    """
        View intended to render field content
    """

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.plone = getMultiAdapter((self.context, self.request), name=u'plone')
        self.pas_member = getMultiAdapter((self.context, self.request), name=u'pas_member')
        self.vocs = {'treating_groups': 'collective.dms.basecontent.treating_groups',
                     'recipient_groups': 'collective.dms.basecontent.recipient_groups',
                     'assigned_group': 'collective.task.AssignedGroups'}

    def from_vocabulary(self, item, value, utility):
        factory = getUtility(IVocabularyFactory, utility)
        voc = factory(item)
        if isinstance(value, list):
            ret = []
            for val in value:
                ret.append(voc.getTerm(val).title)
            return '<br />'.join(ret)
            #return '<ul><li>%s</li></ul>' % '</li><li>'.join(ret)
        return voc.getTerm(value).title

    def render_field(self, field, item):
        """
            render field differently
        """
        field_name = field[0]
        value = getattr(item, field_name)
        if hasattr(value, '__call__'):
            value = value()
        if not value:
            return ''
        if field_name == 'Title':
            if self.context.getId() == 'searchfor_created' and item.getObject().wl_isLocked():
                return '<img width="16" height="16" title="Locked" src="lock_icon.png"><a href="%s">%s</a>' % (
                    item.getURL(), value)
            try:
                state = api.content.get_state(obj=item)
            except ValueError:
                state = ''
            klass = ''
            if state:
                klass = 'state-%s' % state

            return '<a href="%s" class="%s">%s</a>' % (item.getURL(), klass, value)
        elif field_name == 'review_state':
            return _(value, domain='plone')
        elif field_name in ['Creator', 'assigned_user']:
            author = self.pas_member.info(value)
            return '<span>%s</span>' % (author['fullname'] or author['username'])
        elif field_name in ['treating_groups', 'recipient_groups', 'assigned_group']:
            return self.from_vocabulary(item, value, self.vocs[field_name])
        elif field_name in ['ModificationDate', 'CreationDate', 'EffectiveDate', 'ExpirationDate']:
            return '<span>%s</span>' % self.plone.toLocalizedTime(value, long_format=1)
        else:
            return value
