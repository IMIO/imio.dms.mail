from z3c.form.interfaces import HIDDEN_MODE

from plone import api
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.browser.add import DefaultAddView

from ..utils import voc_selected_org_suffix_users


def filter_task_assigned_users(group):
    """
        Filter assigned_user in dms incoming mail
    """
    return voc_selected_org_suffix_users(group, ['editeur', 'validateur'])


class TaskEdit(DefaultEditForm):
    """
      Edit view override of update
    """
    def updateWidgets(self):
        super(TaskEdit, self).updateWidgets()
        self.fields['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
        self.fields['ITask.assigned_group'].field.slave_fields[0]['initial_trigger'] = True
        self.fields['ITask.assigned_group'].field.required = True
        self.widgets['ITask.enquirer'].mode = HIDDEN_MODE


class Add(DefaultAddView):
    """
        Add form redefinition to customize fields.
    """
    portal_type = 'task'

    def update(self):
        self.form_instance.updateFields()
        self.form_instance.fields['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
        self.form_instance.fields['ITask.assigned_group'].field.slave_fields[0]['initial_trigger'] = True
        self.form_instance.fields['ITask.assigned_group'].field.required = True
        userid = api.user.get_current().getId()
        if userid != 'admin':
            self.form_instance.fields['ITask.enquirer'].field.default = userid
        self.form_instance.fields['ITask.enquirer'].mode = HIDDEN_MODE
        super(Add, self).update()
