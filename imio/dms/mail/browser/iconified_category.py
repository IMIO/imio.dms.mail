# -*- coding: utf-8 -*-
"""
    collective.iconifiedcategory overrided views
"""
from collective.iconifiedcategory import utils
from collective.iconifiedcategory.browser.actionview import ApprovedChangeView as BaseApprovedChangeView
from collective.iconifiedcategory.browser.tabview import ApprovedColumn as BaseApprovedColumn
from imio.dms.mail.utils import add_file_to_approval
from imio.dms.mail.utils import approve_file
from imio.dms.mail.utils import can_approve
from imio.dms.mail.utils import get_approval_annot
from imio.dms.mail.utils import is_file_approved
from imio.dms.mail.utils import logger  # noqa F401
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
        av = self.get_action_view(content)
        # import ipdb; ipdb.set_trace()
        if self.is_deactivated(content):
            return " deactivated"
        if av.p_state == "to_approve":
            if can_approve(self.a_a, av.userid, av.uid):
                if self.a_a["files"][content.UID][self.a_a["approval"]]["status"] == "a":
                    return " active editable"
        if content["approved"]:  # all approved
            return " globally-approved"
        elif is_file_approved(self.a_a, content.UID, globally=False):
            return " partially-approved"
        return ""

    def get_url(self, content):
        av = self.get_action_view(content)
        if av.p_state == "to_approve" and not can_approve(self.a_a, av.userid, av.uid):
            return "#"
        if av.p_state in ("to_be_signed", "signed", "sent"):
            return "#"
        return '{url}/@@{action}'.format(
            url=content.getURL(),
            action=self.get_action_view_name(content),
        )


class ApprovedChangeView(BaseApprovedChangeView):

    def __init__(self, context, request):
        super(ApprovedChangeView, self).__init__(context, request)
        self.parent = self.context.__parent__
        self.p_state = api.content.get_state(self.parent)
        self.a_a = get_approval_annot(self.parent)
        self.reload = False
        self.user_id = None
        self.uid = self.context.UID()

    @property
    def userid(self):
        if self.user_id is None:
            self.user_id = api.user.get_current().getId()
        return self.user_id

    def _get_next_values(self, old_values):
        """ """
        values = {}
        status = 0
        logger.info("Before annot change: %s", self.a_a)
        logger.info("Before values change: %s", old_values)
        if self.p_state not in ("to_approve", "to_be_signed", "signed", "sent"):
            # before to_approve state, we can only enable or disable to_approve
            if old_values['to_approve'] is False:
                values['to_approve'] = True
                values['approved'] = False
                status = 0
                add_file_to_approval(self.a_a, self.uid)
            else:
                values['to_approve'] = False
                values['approved'] = False
                status = -1
                remove_file_from_approval(self.a_a, self.uid)
            self.reload = False
        elif self.p_state == "to_approve":
            # in to_approve state, an approver can only approve or not
            # when not an approver, we must show another icon
            if can_approve(self.a_a, self.userid, self.uid):
                if self.a_a["files"][self.uid][self.a_a["approval"]]["status"] == "a":
                    status = 0
                    # TODO TO BE HANDLED
                else:
                    ret, self.reload = approve_file(self.a_a, self.parent, self.context, self.userid, values=values)
                    status = int(ret)
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
        logger.info("After annot change: %s, ", self.a_a)
        logger.info("After values change: %s, %s", status, values)
        return status, values

    def _may_set_values(self, values, ):
        if self.p_state in ("to_be_signed", "signed", "sent"):
            return False
        return super(ApprovedChangeView, self)._may_set_values(values)

    def set_values(self, values):
        # import ipdb; ipdb.set_trace()
        old_values = self.get_current_values()
        status, values = self._get_next_values(old_values)
        super(BaseApprovedChangeView, self).set_values(values)
        return status, utils.approved_message(self.context)

    def __call__(self):
        # TODO ajouter un comparatif de date afin de voir si on agit bien sur qlq chose à jour...
        json_resp = super(ApprovedChangeView, self).__call__()
        if self.reload and json_resp.rstrip().endswith("}"):
            # logger.info("RELOAD TRUE")
            json_resp = json_resp.rstrip()[:-1] + ',"reload": true}'
        return json_resp
