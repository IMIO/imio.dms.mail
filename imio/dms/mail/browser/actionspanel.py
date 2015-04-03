from imio.actionspanel.browser.views import ActionsPanelView
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet


class DmsIMActionsPanelView(ActionsPanelView):
    """
      This manage the view displaying actions on context
    """
    def __init__(self, context, request):
        super(ActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        self.ACCEPTABLE_ACTIONS = []


class ActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method
    """

    def renderViewlet(self):
        return self.context.restrictedTraverse("@@actions_panel")(useIcons=False, showOwnDelete=False,
                                                                  showActions=False)
