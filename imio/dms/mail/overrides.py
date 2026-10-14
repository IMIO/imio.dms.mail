# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from collective.task.adapters import TaskContentAdapter
from imio.dms.mail.utils import get_dms_config
from plone import api


class DmsTaskContentAdapter(TaskContentAdapter):
    security = ClassSecurityInfo()

    security.declarePublic("can_do_transition")

    def can_do_transition(self, transition):
        """Check if assigned_user is set or if the test is required or if the user is admin.
        Used in guard expression for n+1 related task transitions
        """
        if self.context.assigned_group is None:
            # print "no tg: False"
            return False
        way_index = transition.startswith("back_in") and 1 or 0
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(["transitions_levels", "task"])
        if (
            self.context.assigned_group in transitions_levels[state]
            and transitions_levels[state][self.context.assigned_group][way_index] == transition
        ):
            # print "from state: True"
            return True
        return False


InitializeClass(DmsTaskContentAdapter)
