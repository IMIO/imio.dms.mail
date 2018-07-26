from collective.task import _ as _t
from imio.dms.mail import DOC_ASSIGNED_USER_FUNCTIONS
from imio.dms.mail.utils import voc_selected_org_suffix_users
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.browser.edit import DefaultEditForm
from Products.CMFPlone.utils import base_hasattr
# from z3c.form.interfaces import HIDDEN_MODE

import copy


def filter_task_assigned_users(group):
    """
        Filter assigned_user in dms incoming mail
    """
    return voc_selected_org_suffix_users(group, DOC_ASSIGNED_USER_FUNCTIONS)


def TaskUpdateWidgets(self):
    # Override default vocabulary
    self.widgets['ITask.assigned_group'].field = copy.copy(self.widgets['ITask.assigned_group'].field)
    self.widgets['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
    self.widgets['ITask.assigned_group'].field.slave_fields[0]['initial_trigger'] = True
    # Set assigned_group as required
    self.widgets['ITask.assigned_group'].required = True
    self.widgets['ITask.enquirer'].required = True
    # Hide enquirer
    #self.widgets['ITask.enquirer'].mode = HIDDEN_MODE


class TaskEdit(DefaultEditForm):
    """
      Edit view override of update
    """
    def updateWidgets(self):
        super(TaskEdit, self).updateWidgets()
        TaskUpdateWidgets(self)
        if not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'to_assign':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = \
                _t(u'You must select an assigned user before continuing !')


class CustomAddForm(DefaultAddForm):

    portal_type = 'task'

    def updateWidgets(self):
        super(CustomAddForm, self).updateWidgets()
        TaskUpdateWidgets(self)
        # Set parent assigned group as default value
        if base_hasattr(self.context, 'treating_groups') and self.context.treating_groups:
            self.widgets['ITask.assigned_group'].value = self.context.treating_groups
            self.widgets['ITask.enquirer'].value = self.context.treating_groups
        elif base_hasattr(self.context, 'assigned_group') and self.context.assigned_group:
            self.widgets['ITask.assigned_group'].value = self.context.assigned_group
            self.widgets['ITask.enquirer'].value = self.context.assigned_group


class Add(DefaultAddView):
    """
        Add form redefinition to customize fields.
    """
    form = CustomAddForm

#    def update(self):
#        self.form_instance.updateFields()
#        super(Add, self).update()
