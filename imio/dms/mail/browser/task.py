import copy

from z3c.form.interfaces import HIDDEN_MODE

from plone import api
from plone.dexterity.browser.add import DefaultAddView, DefaultAddForm
from plone.dexterity.browser.edit import DefaultEditForm

from Products.CMFPlone.utils import base_hasattr

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
        # Override default vocabulary
        self.widgets['ITask.assigned_group'].field = copy.copy(self.widgets['ITask.assigned_group'].field)
        self.widgets['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
        self.widgets['ITask.assigned_group'].field.slave_fields[0]['initial_trigger'] = True
        # Set assigned_group as required
        self.widgets['ITask.assigned_group'].required = True
        # Hide enquirer
        self.widgets['ITask.enquirer'].mode = HIDDEN_MODE


class CustomAddForm(DefaultAddForm):

    portal_type = 'task'

    def updateWidgets(self):
        super(CustomAddForm, self).updateWidgets()
        # Override default vocabulary
        self.widgets['ITask.assigned_group'].field = copy.copy(self.widgets['ITask.assigned_group'].field)
        self.widgets['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
        self.widgets['ITask.assigned_group'].field.slave_fields[0]['initial_trigger'] = True
        self.widgets['ITask.assigned_group'].required = True
        # Set parent assigned group as default value
        if base_hasattr(self.context, 'treating_groups'):
            self.widgets['ITask.assigned_group'].value = self.context.treating_groups
        elif base_hasattr(self.context, 'assigned_group'):
            self.widgets['ITask.assigned_group'].value = self.context.assigned_group
        # Set current user as enquirer and hide it
        userid = api.user.get_current().getId()
        if userid != 'admin':
            self.widgets['ITask.enquirer'].value = userid
        self.widgets['ITask.enquirer'].mode = HIDDEN_MODE


class Add(DefaultAddView):
    """
        Add form redefinition to customize fields.
    """
    form = CustomAddForm

#    def update(self):
#        self.form_instance.updateFields()
#        super(Add, self).update()
