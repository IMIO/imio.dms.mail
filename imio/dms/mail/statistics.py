from itertools import combinations

import pandas as pd
from Products.CMFCore.utils import getToolByName
from imio.dms.mail import _
from plone import api


def time_between(review_history, state_one=None, state_two=None, transition=None, multiple_steps_allowed=False):
    """
    Calculates time between 2 lines of an object's review history, in days.
    Available filters are state_one, state_two and transition.
    Only pairs of consecutive lines are considered, unless multiple_steps_allowed is True.
    Returns a float, or None if no matches are found.
    """
    if not any([state_one, state_two, transition]):
        raise TypeError("At least one filtering parameter must be set.")
    if len(review_history) < 2:
        return None

    if multiple_steps_allowed:
        possible_combinations = combinations(review_history, 2)
    else:
        possible_combinations = [(review_history[i], review_history[i+1]) for i in range(len(review_history)-1)]

    for history_state_one, history_state_two in possible_combinations:
        if transition and history_state_two['action'] != transition:
            continue
        if state_one and history_state_one['review_state'] != state_one:
            continue
        if state_two and history_state_two['review_state'] != state_two:
            continue
        return history_state_two['time'] - history_state_one['time']

    return None


class StatisticsGenerator:
    """
    Builds a pandas DataFrame from raw catalog data,
    which is then pivoted and returned as csv.
    """

    counting_column = 'path'
    averaged_columns = [
        'time_after_proposed_to_manager',
        'time_after_proposed_to_service_chief',
        'time_after_proposed_to_agent',
        'time_between_proposed_to_agent_and_closed',
        'time_after_created',
        'time_after_to_be_signed',
    ]

    def __init__(self):
        self._df = None

    @property
    def df(self):
        if self._df is None:
            self._df = self.build_df()
        return self._df

    def build_df(self):
        mails = []
        treating_groups_names = {}

        catalog = api.portal.get_tool('portal_catalog')
        for brain in catalog(portal_type=[
            'dmsincomingmail',
            'dmsoutgoingmail',
            'dmsincoming_email',
            'dmsoutgoing_email'
        ]):

            treating_group_uid = brain.treating_groups
            treating_group = treating_groups_names.setdefault(
                treating_group_uid,
                api.content.find(UID=treating_group_uid)[0].Title,
            )

            mail = {
                'path': brain.getPath(),
                'portal_type': brain.portal_type,
                'user': brain.Creator,
                'treating_group': treating_group,
                'year': brain.created.year(),
                'month': brain.created.month(),
                'weekday': brain.created.dow(),
            }

            context = brain.getObject()
            workflow = getToolByName(context, 'portal_workflow')
            workflow_id = workflow.getChainFor(context)[0]
            review_history = workflow.getInfoFor(context, 'review_history')
            timings = {}

            if workflow_id == 'incomingmail_workflow':
                timings['time_after_proposed_to_manager'] = time_between(review_history,
                                                                         state_one='proposed_to_manager')
                timings['time_after_proposed_to_service_chief'] = time_between(review_history,
                                                                               state_one='proposed_to_service_chief')
                timings['time_after_proposed_to_agent'] = time_between(review_history,
                                                                       state_one='proposed_to_agent')
                timings['time_between_proposed_to_agent_and_closed'] = time_between(review_history,
                                                                                    state_one='proposed_to_agent',
                                                                                    state_two='closed',
                                                                                    multiple_steps_allowed=True)
                timings['time_after_created'] = None
                timings['time_after_to_be_signed'] = None
            elif workflow_id == 'outgoingmail_workflow':
                timings['time_after_proposed_to_manager'] = None
                timings['time_after_proposed_to_service_chief'] = time_between(review_history,
                                                                               state_one='proposed_to_service_chief')
                timings['time_after_proposed_to_agent'] = None
                timings['time_between_proposed_to_agent_and_closed'] = None
                timings['time_after_created'] = time_between(review_history,
                                                             state_one='created')
                timings['time_after_to_be_signed'] = time_between(review_history,
                                                                  state_one='to_be_signed')

            mail.update(timings)
            mails.append(mail)

        df = pd.DataFrame(mails)
        return df

    @property
    def count_portal_type_year(self):
        if self.df.empty:
            return ''
        pv = self.df.pivot_table(values=self.counting_column, index=['portal_type', 'year'], aggfunc=len,
                                 fill_value=0.0)
        return pv.rename(columns={self.counting_column: "count"}).to_csv()

    @property
    def count_portal_type_month(self):
        if self.df.empty:
            return ''
        pv = self.df.pivot_table(values=self.counting_column, index=['portal_type', 'month'], aggfunc=len,
                                 fill_value=0.0)
        return pv.rename(columns={self.counting_column: "count"}).to_csv()

    @property
    def count_portal_type_month_treating_group(self):
        if self.df.empty:
            return ''
        pv = self.df.pivot_table(values=self.counting_column, index=['portal_type', 'month', 'treating_group'],
                                 aggfunc=len, fill_value=0.0)
        return pv.rename(columns={self.counting_column: "count"}).to_csv()

    @property
    def count_portal_type_month_user(self):
        if self.df.empty:
            return ''
        pv = self.df.pivot_table(values=self.counting_column, index=['portal_type', 'month', 'user'], aggfunc=len,
                                 fill_value=0.0)
        return pv.rename(columns={self.counting_column: "count"}).to_csv()

    @property
    def average_time_by_portal_type_month_user(self):
        if self.df.empty or not self.df[self.averaged_columns].any().any():
            return ''
        pv = self.df.pivot_table(values=self.averaged_columns, index=['portal_type', 'month', 'user'])
        return pv.to_csv()

    @property
    def average_time_by_portal_type_month_treating_group(self):
        if self.df.empty or not self.df[self.averaged_columns].any().any():
            return ''
        pv = self.df.pivot_table(values=self.averaged_columns, index=['portal_type', 'month', 'treating_group'])
        return pv.to_csv()


visualizations_config = [
    {
        'id': 'count_portal_type_year',
        'title': _(u'count by portal type, by year'),
        'property': 'count_portal_type_year',
    },
    {
        'id': 'count_portal_type_month',
        'title': _(u'count by portal type, by month'),
        'property': 'count_portal_type_month',
    },
    {
        'id': 'count_portal_type_month_treating_group',
        'title': _(u'count by portal type, by month, by treating group'),
        'property': 'count_portal_type_month_treating_group',
    },
    {
        'id': 'count_portal_type_month_user',
        'title': _(u'count by portal type, by month, by user'),
        'property': 'count_portal_type_month_user',
    },
    {
        'id': 'average_time_by_portal_type_month_user',
        'title': _(u'average time by portal type, by month, by user'),
        'property': 'average_time_by_portal_type_month_user',
    },
    {
        'id': 'average_time_by_portal_type_month_treating_group',
        'title': _(u'average time by portal type, by month, by treating group'),
        'property': 'average_time_by_portal_type_month_treating_group',
    }
]
