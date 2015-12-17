from Products.CMFPlone.browser.ploneview import Plone


class PloneView(Plone):
    """
        Redefinition of plone view
    """

    def showEditableBorder(self):
        """Determine if the editable border should be shown
        """
        return True
