from zope.component import getMultiAdapter
from zope.interface import implements
from plone.app.portlets.portlets import base
from plone.memoize import forever
from zope.app.component.hooks import getSite
from plone.portlets.interfaces import IPortletDataProvider
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from .. import _


class IMainDmsMailPortlet(IPortletDataProvider):
    """
        Principal portlet for DmsMail containing actions, ...
    """


class Assignment(base.Assignment):
    implements(IMainDmsMailPortlet)

    def __init__(self):
        pass

    @property
    def title(self):
        return _(u"Main DmsMail Portlet")


@forever.memoize
def getIncomingMailFolder():
    portal = getSite()
    return portal['incoming-mail']


@forever.memoize
def getIncomingMailAddUrl():
    return '%s/%s' % (getIncomingMailFolder().absolute_url(), '++add++dmsincomingmail')


class Renderer(base.Renderer):
    _template = ViewPageTemplateFile('portlet_maindmsmail.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.anonymous = portal_state.anonymous()
        self.member = portal_state.member()

    @property
    def available(self):
        """
          Defines if the portlet is available in the context
        """
        return not self.anonymous and self.context.portal_type not in ('directory',)

    def render(self):
        return self._template()

    def canAddIncomingMail(self):
        if self.member.has_permission('collective.dms.mailcontent: Add Incoming Mail',
                                      getIncomingMailFolder()):
            return True
        return False

    def canAddMainFile(self):
        if self.context.portal_type == 'dmsincomingmail' and \
                self.member.has_permission('Add portal content', self.context):
            return True
        return False

    def canAddSomething(self):
        if self.canAddIncomingMail() or self.canAddMainFile():
            return True
        return False

    def getIncomingMailAddUrl(self):
        return getIncomingMailAddUrl()

    def getMainFileAddUrl(self):
        return '%s/%s' % (self.context.absolute_url(), '++add++dmsmainfile')


class AddForm(base.NullAddForm):

    def create(self):
        return Assignment()
