from imio.actionspanel.browser.viewlets import ActionsPanelViewlet
from imio.actionspanel.browser.views import ActionsPanelView
from plone import api
from plone.memoize import ram
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter


def actionspanelview_cachekey(method,
                              self,
                              useIcons=True,
                              showOwnDelete=False,
                              showActions=False,
                              showAddContent=False,
                              **kwargs):
    """ cachekey method using only modified params. Must be adapted if changes !!
        We will add the following informations:
        * context
        * modification date
        * review state
        * current user
        * user groups
    """
    user = self.request['AUTHENTICATED_USER']
    return (useIcons, showOwnDelete, showActions, showAddContent,
            self.context, user.getId(), self.context.modified(), api.content.get_state(self.context, default=None),
            sorted(user.getGroups()))


class DmsIMActionsPanelView(ActionsPanelView):

    transitions = ['back_to_creation', 'back_to_pre_manager', 'back_to_manager', 'back_to_service_chief',
                   'back_to_agent', 'back_to_treatment', 'propose_to_pre_manager', 'propose_to_manager',
                   'propose_to_service_chief', 'propose_to_agent', 'treat', 'close']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsIMActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER += (
            'renderReplyButton',
        )
        self.ACCEPTABLE_ACTIONS = ['delete']
        self.ogm = api.portal.get()['outgoing-mail']

    def mayReply(self):
        """
          Method that check if special 'reply' action has to be displayed.
        """
        return self.member.has_permission('Add portal content', self.ogm)

    def renderReplyButton(self):
        if self.mayReply():
            return ViewPageTemplateFile(
                "templates/actions_panel_reply.pt")(self)
        return ""

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order.get(x['id'], 99), self.tr_order.get(y['id'], 99)))

    @ram.cache(actionspanelview_cachekey)
    def __call__(self,
                 useIcons=True,
                 #showTransitions=True,
                 #appendTypeNameToTransitionLabel=False,
                 #showEdit=True,
                 #showExtEdit=False,
                 showOwnDelete=False,
                 showActions=False,
                 showAddContent=False,
                 #showHistory=False,
                 #showHistoryLastEventHasComments=True,
                 #showArrows=False,
                 #arrowsPortalTypeAware=False,
                 **kwargs):
        return super(DmsIMActionsPanelView, self).__call__(
            useIcons=useIcons,
            #showTransitions=showTransitions,
            #appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
            #showEdit=showEdit,
            #showExtEdit=showExtEdit,
            showOwnDelete=showOwnDelete,
            showActions=showActions,
            showAddContent=showAddContent,
            #showHistory=showHistory,
            #showHistoryLastEventHasComments=showHistoryLastEventHasComments,
            #showArrows=showArrows,
            #arrowsPortalTypeAware=arrowsPortalTypeAware,
            **kwargs)


class DmsActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method for dms document
    """

    def renderViewlet(self):
        view = getMultiAdapter((self.context, self.request), name='actions_panel')
        return view(useIcons=False, showExtEdit=False, showOwnDelete=False, showAddContent=True, showActions=True)


class DmsOMActionsPanelView(ActionsPanelView):

    transitions = ['back_to_agent', 'back_to_creation', 'back_to_service_chief', 'back_to_print', 'back_to_be_signed',
                   'back_to_scanned', 'propose_to_service_chief', 'set_to_print', 'propose_to_be_signed',
                   'mark_as_sent', 'set_scanned']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsOMActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        #self.ACCEPTABLE_ACTIONS = ['copy', 'paste', 'delete']
        self.ACCEPTABLE_ACTIONS = ['delete']
        self.SECTIONS_TO_RENDER += (
            'renderCreateFromTemplateButton',
        )

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order[x['id']], self.tr_order[y['id']]))

    def mayCreateFromTemplate(self):
        """
          Method that check if special 'create from template' action has to be displayed.
        """
        if not self.isInFacetedNavigation() and self.member.has_permission('Add portal content', self.context):
            return True
        return False

    def renderCreateFromTemplateButton(self):
        if self.mayCreateFromTemplate():
            return ViewPageTemplateFile(
                "templates/actions_panel_create_from_template.pt")(self)
        return ''

    @ram.cache(actionspanelview_cachekey)
    def __call__(self,
                 useIcons=True,
                 #showTransitions=True,
                 #appendTypeNameToTransitionLabel=False,
                 #showEdit=True,
                 #showExtEdit=False,
                 showOwnDelete=False,
                 showActions=False,
                 showAddContent=False,
                 #showHistory=False,
                 #showHistoryLastEventHasComments=True,
                 #showArrows=False,
                 #arrowsPortalTypeAware=False,
                 **kwargs):
        return super(DmsOMActionsPanelView, self).__call__(
            useIcons=useIcons,
            #showTransitions=showTransitions,
            #appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
            #showEdit=showEdit,
            #showExtEdit=showExtEdit,
            showOwnDelete=showOwnDelete,
            showActions=showActions,
            showAddContent=showAddContent,
            #showHistory=showHistory,
            #showHistoryLastEventHasComments=showHistoryLastEventHasComments,
            #showArrows=showArrows,
            #arrowsPortalTypeAware=arrowsPortalTypeAware,
            **kwargs)


class DmsTaskActionsPanelView(ActionsPanelView):

    transitions = ['back_in_created', 'back_in_to_assign', 'back_in_to_do', 'back_in_progress', 'back_in_realized',
                   'do_to_assign', 'do_to_do', 'do_in_progress', 'do_realized', 'do_closed']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsTaskActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = ['copy', 'cut', 'paste', 'delete']

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order[x['id']], self.tr_order[y['id']]))

    @ram.cache(actionspanelview_cachekey)
    def __call__(self,
                 useIcons=True,
                 #showTransitions=True,
                 #appendTypeNameToTransitionLabel=False,
                 #showEdit=True,
                 #showExtEdit=False,
                 showOwnDelete=False,
                 showActions=False,
                 showAddContent=False,
                 #showHistory=False,
                 #showHistoryLastEventHasComments=True,
                 #showArrows=False,
                 #arrowsPortalTypeAware=False,
                 **kwargs):
        return super(DmsTaskActionsPanelView, self).__call__(
            useIcons=useIcons,
            #showTransitions=showTransitions,
            #appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
            #showEdit=showEdit,
            #showExtEdit=showExtEdit,
            showOwnDelete=showOwnDelete,
            showActions=showActions,
            showAddContent=showAddContent,
            #showHistory=showHistory,
            #showHistoryLastEventHasComments=showHistoryLastEventHasComments,
            #showArrows=showArrows,
            #arrowsPortalTypeAware=arrowsPortalTypeAware,
            **kwargs)


class BasicActionsPanelView(ActionsPanelView):
    """
      This manage the view displaying actions on contact
    """
    def __init__(self, context, request):
        super(BasicActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = ['cut', 'copy', 'paste', 'delete', 'rename']


class ContactActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method for contacts
    """

    def renderViewlet(self):
        view = getMultiAdapter((self.context, self.request), name='actions_panel')
        return view(useIcons=False, showExtEdit=False, showOwnDelete=False, showAddContent=True, showActions=True)


class ActionsPanelViewletAllButTransitions(ActionsPanelViewlet):
    """
        Override render method for IActionsPanelFolder
    """

    def renderViewlet(self):
        view = getMultiAdapter((self.context, self.request), name='actions_panel')
        return view(useIcons=False, showExtEdit=False, showTransitions=False, showOwnDelete=False, showAddContent=True,
                    showActions=True)


class ActionsPanelViewletAllButOwnDelete(ActionsPanelViewlet):
    """
        Override render method for IActionsPanelFolder
    """

    def renderViewlet(self):
        view = getMultiAdapter((self.context, self.request), name='actions_panel')
        return view(useIcons=False, showExtEdit=False, showTransitions=True, showOwnDelete=False, showAddContent=True,
                    showActions=True)


class ActionsPanelViewletAdd(ActionsPanelViewlet):
    """
        Override render method
    """

    def renderViewlet(self):
        view = getMultiAdapter((self.context, self.request), name='actions_panel')
        return view(useIcons=False, showExtEdit=False, showTransitions=False, showOwnDelete=False, showAddContent=True,
                    showActions=False)
