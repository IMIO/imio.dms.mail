# -*- coding: utf-8 -*-
"""Custom columns."""
from collective.eeafaceted.z3ctable.columns import DateColumn, MemberIdColumn, VocabularyColumn


class TreatingGroupsColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedGroupColumn(VocabularyColumn):

    vocabulary = u'collective.dms.basecontent.treating_groups'


class AssignedUserColumn(MemberIdColumn):

    attrName = u'assigned_user'


class DueDateColumn(DateColumn):

    attrName = u'due_date'
