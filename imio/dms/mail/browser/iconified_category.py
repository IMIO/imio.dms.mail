# -*- coding: utf-8 -*-
"""
    collective.iconifiedcategory overrided views
"""
from collective.iconifiedcategory import utils
from collective.iconifiedcategory.browser.actionview import ApprovedChangeView as BaseApprovedChangeView
from collective.iconifiedcategory.browser.tabview import ApprovedColumn as BaseApprovedColumn
from imio.dms.mail.utils import add_file_to_approval
from imio.dms.mail.utils import get_approval_annot
from imio.dms.mail.utils import logger
from imio.dms.mail.utils import remove_file_from_approval
from plone import api


"""
{
    'approval': 1,
    'files': {'4115fb4c265647ca82d85285504973b8': {1: {'status': 'p'}, 2: {'status': 'w'}}},
    'numbers': {
        1: {'status': 'p', 'signer': ('dirg', 'stephan.geulette@imio.be', u'Maxime DG', u'Directeur G\xe9n\xe9ral'),
            'users': ['dirg']},
        2: {'status': 'w', 'signer': ('bourgmestre', 'stephan.geulette+s2@imio.be', u'Paul BM', u'Bourgmestre'),
            'users': ['bourgmestre', 'chef']}},
    'session_id': None,
    'users': {'bourgmestre': {'status': 'w', 'editor': False, 'name': u'Monsieur Paul BM', 'order': 2},
              'chef': {'status': 'w', 'editor': False, 'name': u'Monsieur Michel Chef', 'order': 2},
              'dirg': {'status': 'w', 'editor': True, 'name': u'Monsieur Maxime DG', 'order': 1}},
}
"""  # noqa


class ApprovedColumn(BaseApprovedColumn):

    the_object = True

    def __init__(self, context, request, table):
        super(ApprovedColumn, self).__init__(context, request, table)
        # self.context is the mail here
        self.a_a = get_approval_annot(self.context)

    # original method waiting to be modified
    def css_class(self, content):
        # av = self.get_action_view(content)
        # if av.p_state not in ("to_approve", "to_be_signed", "signed", "sent"):
        is_deactivated = self.is_deactivated(content)
        if not self._deactivated_is_useable() and is_deactivated:
            return ' deactivated'
        base_css = self.is_active(content) and ' active' or ''
        if is_deactivated:
            base_css = ' deactivated' + base_css
        if self.is_editable(content):
            return '{0} editable'.format(base_css)
        return base_css

    # def renderCell(self, content):
    #     link = u'<a href="{0}" class="iconified-action{1}" alt="{2}" title="{2}"></a>'
    #     av = self.get_action_view(content)
    #     if av.p_state not in ("to_approve", "to_be_signed", "signed", "sent"):
    #         return u'<span class="iconified-action deactivated" alt="N/A" title="N/A"></span>'
    #     return link.format(
    #         self.get_url(content),
    #         self.css_class(content),
    #         self.alt(content),
    #     )


class ApprovedChangeView(BaseApprovedChangeView):

    def __init__(self, context, request):
        super(ApprovedChangeView, self).__init__(context, request)
        self.parent = self.context.__parent__
        self.p_state = api.content.get_state(self.parent)
        self.a_a = get_approval_annot(self.parent)
        self.reload = False

    def _get_next_values(self, old_values):
        """ """
        values = {}
        # logger.info("Before annot change: %s", self.a_a)
        # logger.info("Before values change: %s", old_values)
        if self.p_state not in ("to_approve", "to_be_signed", "signed", "sent"):
            # before to_approve state, we can only enable or disable to_approve
            if old_values['to_approve'] is False:
                values['to_approve'] = True
                values['approved'] = False
                status = 0
                add_file_to_approval(self.a_a, self.context.UID())
            else:
                values['to_approve'] = False
                values['approved'] = False
                status = -1
                remove_file_from_approval(self.a_a, self.context.UID())
            self.reload = False
        elif self.p_state == "to_approve":
            pass
            # TO BE CONTINUED
        else:
            if old_values['to_approve'] is False:
                values['to_approve'] = True
                values['approved'] = False
                status = 0
            elif old_values['to_sign'] is True and old_values['signed'] is False:
                values['to_approve'] = True
                values['approved'] = True
                status = 1
            else:
                # old_values['to_sign'] is True and old_values['signed'] is True
                # disable to_sign and signed
                values['to_approve'] = False
                values['approved'] = False
                status = -1
        # logger.info("After annot change: %s, ", self.a_a)
        # logger.info("After values change: %s, %s", status, values)
        return status, values

    def set_values(self, values):
        old_values = self.get_current_values()
        status, values = self._get_next_values(old_values)
        super(BaseApprovedChangeView, self).set_values(values)
        return status, utils.approved_message(self.context)

    def __call__(self):
        json_resp = super(ApprovedChangeView, self).__call__()
        if self.reload and json_resp.rstrip().endswith("}"):
            # logger.info("RELOAD TRUE")
            json_resp = json_resp.rstrip()[:-1] + ',"reload": true}'
        return json_resp
