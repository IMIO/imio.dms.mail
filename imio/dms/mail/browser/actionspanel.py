from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from imio.actionspanel.browser.views import ActionsPanelView
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet


class DmsIMActionsPanelView(ActionsPanelView):

    transitions = ['back_to_creation', 'back_to_manager', 'back_to_service_chief', 'back_to_agent', 'back_to_treatment',
                   'propose_to_manager', 'propose_to_service_chief', 'propose_to_agent', 'treat', 'close']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def __init__(self, context, request):
        super(DmsIMActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER += (
            'renderReplyButton',
            # 'renderCreateFromTemplateButton'
        )

    def mayReply(self):
        """
          Method that check if special 'reply' action has to be displayed.
        """
        return self.member.has_permission('Add portal content', self.context)

    def renderReplyButton(self):
        if self.mayReply():
            return ViewPageTemplateFile(
                "templates/actions_panel_reply.pt")(self)
        return ""

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order.get(x['id'], 99), self.tr_order.get(y['id'], 99)))

    def renderCreateFromTemplateButton(self):
        return ViewPageTemplateFile(
            "templates/actions_panel_create_from_template.pt")(self)


class DmsIMActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method for dms incoming mail
    """

    def renderViewlet(self):
        return self.context.restrictedTraverse("@@actions_panel")(useIcons=False, showOwnDelete=True,
                                                                  showAddContent=True, showActions=False)


class ContactActionsPanelView(ActionsPanelView):
    """
      This manage the view displaying actions on contact
    """
    def __init__(self, context, request):
        super(ContactActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = ['cut', 'copy', 'paste', 'delete']


class ContactActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method for contacts
    """

    def renderViewlet(self):
        return self.context.restrictedTraverse("@@actions_panel")(useIcons=False, showOwnDelete=False,
                                                                  showAddContent=True, showActions=True)


class DmsTaskActionsPanelView(ActionsPanelView):

    transitions = ['back_in_created', 'back_in_to_assign', 'back_in_to_do', 'back_in_progress', 'back_in_realized',
                   'do_to_assign', 'do_to_do', 'do_in_progress', 'do_realized', 'do_closed']
    tr_order = dict((val, i) for (i, val) in enumerate(transitions))

    def sortTransitions(self, lst):
        """ Sort transitions following transitions list order"""
        lst.sort(lambda x, y: cmp(self.tr_order[x['id']], self.tr_order[y['id']]))
