from collective.documentgenerator.browser.actionspanel import ConfigurablePODTemplateActionsPanelView
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet
from imio.actionspanel.browser.views import ActionsPanelView
from imio.dms.mail.dmsmail import filter_dmsincomingmail_assigned_users
from plone import api
from plone.memoize import ram
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


def actionspanelview_cachekey(method,
                              self,
                              useIcons=True,
                              showEdit=True,
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
    return (useIcons, showOwnDelete, showActions, showAddContent, showEdit,
            self.context, user.getId(), self.context.modified(), api.content.get_state(self.context, default=None),
            sorted(user.getGroups()))


class DmsIMActionsPanelView(ActionsPanelView):

    transitions = ['back_to_creation', 'back_to_pre_manager', 'back_to_manager', 'back_to_n_plus_5', 'back_to_n_plus_4',
                   'back_to_n_plus_3', 'back_to_n_plus_2', 'back_to_n_plus_1',
                   'back_to_agent', 'back_to_treatment', 'propose_to_pre_manager', 'propose_to_manager',
                   'propose_to_n_plus_5', 'propose_to_n_plus_4', 'propose_to_n_plus_3', 'propose_to_n_plus_2',
                   'propose_to_n_plus_1', 'propose_to_agent', 'treat', 'close']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsIMActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER += (
            'renderReplyButton',
            'renderAssignUser',
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

    def showAssignUser(self):
        return (bool(self.context.treating_groups) and self.member.has_permission('Modify portal content', self.context)
                and api.content.get_state(self.context, 'none') not in ('created', 'in_treatment', 'closed'))

    def renderAssignUser(self):
        """
          Render users that can be assigned.
        """
        if self.showAssignUser():
            return ViewPageTemplateFile("templates/actions_panel_assign_user.pt")(self)
        return ''

    def assignable_users(self):
        voc = filter_dmsincomingmail_assigned_users(self.context.treating_groups)
        return voc

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order.get(x['id'], 99), self.tr_order.get(y['id'], 99)))

    @ram.cache(actionspanelview_cachekey)
    def __call__(self,
                 useIcons=True,
                 #showTransitions=True,
                 #appendTypeNameToTransitionLabel=False,
                 showEdit=True,
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
            showEdit=showEdit,
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

    params = {
        'useIcons': False,
        'showEdit': True,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': True,
    }


class DmsOMActionsPanelView(ActionsPanelView):

    transitions = ['back_to_agent', 'back_to_creation', 'back_to_n_plus_1', 'back_to_print', 'back_to_be_signed',
                   'back_to_scanned', 'propose_to_n_plus_1', 'set_to_print', 'propose_to_be_signed',
                   'mark_as_sent', 'set_scanned']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsOMActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        # self.ACCEPTABLE_ACTIONS = ['copy', 'paste', 'delete']
        self.ACCEPTABLE_ACTIONS = ['delete']
        self.SECTIONS_TO_RENDER += (
            'render_create_from_template_button',
            'render_create_new_message',
            'render_send_email',
        )

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order[x['id']], self.tr_order[y['id']]))

    def may_create_from_template(self):
        """
          Method that check if special 'create from template' action has to be displayed.
        """
        if not self.isInFacetedNavigation() and self.member.has_permission('Add portal content', self.context):
            return True
        return False

    def render_create_from_template_button(self):
        if self.may_create_from_template():
            return ViewPageTemplateFile(
                "templates/actions_panel_create_from_template.pt")(self)
        return ''

    def may_create_new_message(self):
        if self.context.is_email() and not self.isInFacetedNavigation() and \
                self.member.has_permission('Modify portal content', self.context):
            return True
        return False

    def render_create_new_message(self):
        if self.may_create_new_message():
            return ViewPageTemplateFile("templates/actions_panel_create_new_message.pt")(self)
        return ''

    def may_send_email(self):
        if self.context.email_subject and not self.isInFacetedNavigation() and \
                self.member.has_permission('Modify portal content', self.context):
            return True
        return False

    def render_send_email(self):
        if self.may_send_email():
            return ViewPageTemplateFile("templates/actions_panel_send_email.pt")(self)
        return ''

    @ram.cache(actionspanelview_cachekey)
    def __call__(self,
                 useIcons=True,
                 #showTransitions=True,
                 #appendTypeNameToTransitionLabel=False,
                 showEdit=True,
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
            showEdit=showEdit,
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

    transitions = ['back_in_created', 'back_in_created2', 'back_in_to_assign', 'back_in_to_do', 'back_in_progress',
                   'back_in_realized', 'do_to_assign', 'do_to_do', 'do_in_progress', 'do_realized', 'do_closed']
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
                 showEdit=True,
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
            showEdit=showEdit,
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
        This manage the view displaying actions on contact, folder, some template, ...
    """
    def __init__(self, context, request):
        super(BasicActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = ['cut', 'copy', 'paste', 'delete', 'rename']


class OnlyAddActionsPanelView(ActionsPanelView):
    """This manage the view displaying actions on some folder."""

    def __init__(self, context, request):
        super(OnlyAddActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = ['paste']


class CPODTActionsPanelView(BasicActionsPanelView, ConfigurablePODTemplateActionsPanelView):
    """
        This manage the view on ConfigurablePODTemplate
    """


class ContactActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method for contacts
    """

    params = {
        'useIcons': False,
        'showEdit': True,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': True,
    }


class ActionsPanelViewletAllButTransitions(ActionsPanelViewlet):
    """
        Override render method for IActionsPanelFolder
    """

    params = {
        'useIcons': False,
        'showEdit': True,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': True,
        'showTransitions': False,
    }


class ActionsPanelViewletAllButOwnDelete(ActionsPanelViewlet):
    """
        Override render method for IActionsPanelFolder
    """

    params = {
        'useIcons': False,
        'showEdit': True,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': True,
    }


class ActionsPanelViewletOnlyAdd(ActionsPanelViewlet):
    """
        Override render method for IActionsPanelFolder
    """

    params = {
        'useIcons': False,
        'showEdit': False,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': True,  # filtered in view to keep paste
        'showTransitions': False,
    }


class ActionsPanelViewletAdd(ActionsPanelViewlet):
    """
        Override render method
    """

    params = {
        'useIcons': False,
        'showEdit': True,
        'showOwnDelete': False,
        'showAddContent': True,
        'showActions': False,
        'showTransitions': False,
    }
