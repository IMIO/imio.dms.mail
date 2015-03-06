from imio.actionspanel.browser.views import ActionsPanelView
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet


class ActionsPanelView(ActionsPanelView):
    """
      This manage the view displaying actions on context
    """
    def __init__(self, context, request):
        super(ActionsPanelView, self).__init__(context, request)
        # portal_actions.object_buttons action ids to keep
        # if you define some here, only these actions will be kept
        self.ACCEPTABLE_ACTIONS = (
            'test',
        )


class ActionsPanelViewlet(ActionsPanelViewlet):
    """
        Override render method
    """

    def renderViewlet(self):
        return self.context.restrictedTraverse("@@actions_panel")(useIcons=False, showOwnDelete=False,
                                                                  showActions=False, showHistory=True)
