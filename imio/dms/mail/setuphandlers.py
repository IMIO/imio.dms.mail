# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2013 by CommunesPlone, Imio
#
# GNU General Public License (GPL)
#

__author__ = """Gauthier BASTIEN <gbastien@commune.sambreville.be>, Stephan GEULETTE
<stephan.geulette@uvcw.be>"""
__docformat__ = 'plaintext'

import datetime
import logging
import os
import random
import string
from itertools import cycle
from Acquisition import aq_base
from zope.component import queryUtility, getMultiAdapter, getUtility
from zope.i18n.interfaces import ITranslationDomain
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobFile
#from plone.portlets.constants import CONTEXT_CATEGORY
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY, ORGANIZATIONS_REGISTRY
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue, receptionDateDefaultValue
from collective.dms.mailcontent.dmsmail import internalReferenceOutgoingMailDefaultValue, mailDateDefaultValue
from dexterity.localroles.utils import add_fti_configuration
logger = logging.getLogger('imio.dms.mail: setuphandlers')


def _(msgid, context, domain='imio.dms.mail'):
    translation_domain = queryUtility(ITranslationDomain, domain)
    return translation_domain.translate(msgid, context=context.getSite().REQUEST)


def postInstall(context):
    """Called as at the end of the setup process. """
    # the right place for your custom code

    if not context.readDataFile("imiodmsmail_marker.txt"):
        return
    site = context.getSite()

    # we adapt default portal
    adaptDefaultPortal(context)

    # we configure rolefields
    configure_rolefields(context)

    # we create the basic folders
    if not hasattr(aq_base(site), 'incoming-mail'):
        folderid = site.invokeFactory("Folder", id='incoming-mail', title=_(u"Incoming mail", context))
        newFolder = getattr(site, folderid)
        #blacklistPortletCategory(context, newFolder, CONTEXT_CATEGORY, u"plone.leftcolumn")
        createTopicView(newFolder, 'dmsincomingmail', _(u'all_incoming_mails', context))
        createStateTopics(context, newFolder, 'dmsincomingmail')
        newFolder.setConstrainTypesMode(1)
        newFolder.setLocallyAllowedTypes(['dmsincomingmail'])
        newFolder.setImmediatelyAddableTypes(['dmsincomingmail'])
        site.portal_workflow.doActionFor(newFolder, "show_internally")
        logger.info('incoming-mail folder created')
    if not hasattr(aq_base(site), 'outgoing-mail'):
        folderid = site.invokeFactory("Folder", id='outgoing-mail', title=_(u"Outgoing mail", context))
        newFolder = getattr(site, folderid)
        #blacklistPortletCategory(context, newFolder, CONTEXT_CATEGORY, u"plone.leftcolumn")
        createTopicView(newFolder, 'dmsoutgoingmail', _('Outgoing mail', context))
        newFolder.setConstrainTypesMode(1)
        newFolder.setLocallyAllowedTypes(['dmsoutgoingmail'])
        newFolder.setImmediatelyAddableTypes(['dmsoutgoingmail'])
        logger.info('outgoing-mail folder created')


def blacklistPortletCategory(context, object, category, utilityname):
    """
        block portlets on object for the corresponding category
    """
    from plone.portlets.interfaces import IPortletManager, ILocalPortletAssignmentManager
    # Get the proper portlet manager
    manager = queryUtility(IPortletManager, name=utilityname)
    # Get the current blacklist for the location
    blacklist = getMultiAdapter((object, manager), ILocalPortletAssignmentManager)
    # Turn off the manager
    blacklist.setBlacklistStatus(category, True)


def createTopicView(folder, ptype, title):
    """
        create a topic as default page
    """
    if not 'all_incoming_mails' in folder:
        folder.invokeFactory("Topic", id='all_incoming_mails', title=title)
        topic = getattr(folder, 'all_incoming_mails')
        topic.setCustomView(True)
#        topic.setCustomViewFields(('Title', 'internal_reference_number', 'review_state', 'CreationDate', 'Creator'))
        topic.setCustomViewFields(('Title', 'review_state', 'CreationDate', 'Creator'))
        topic.setSortCriterion('created', True)
        # add portal_type criterion
        crit = topic.addCriterion('portal_type', 'ATSimpleStringCriterion')
        crit.setValue(ptype)
        # set the topic as folder's default page
        folder.setDefaultPage('all_incoming_mails')
        folder.portal_workflow.doActionFor(topic, "show_internally")


def createStateTopics(context, folder, content_type):
    """
        create a topic for each contextual workflow state
    """
    default_states = ['created', 'proposed_to_manager', 'proposed_to_service_chief',
                      'proposed_to_agent', 'in_treatment', 'closed']
    for workflow in folder.portal_workflow.getWorkflowsFor(content_type):
        for value in workflow.states.values():
            if value.id not in default_states:
                default_states.append(value)
        for state in default_states:
            try:
                topic_id = "searchfor_%s" % state
                if not hasattr(folder, topic_id):
                    folder.invokeFactory("Topic", id=topic_id, title=_(topic_id, context))
                    topic = folder[topic_id]
                    topic.setCustomView(True)
                    topic.setCustomViewFields(('Title', 'review_state', 'CreationDate', 'Creator'))
                    topic.setSortCriterion('created', True)
                    # add portal_type criterion
                    crit = topic.addCriterion('portal_type', 'ATSimpleStringCriterion')
                    crit.setValue(content_type)
                    # criterion of state
                    crit = topic.addCriterion(field='review_state', criterion_type='ATListCriterion')
                    crit.setValue(state)
                    #we limit the results by page
                    topic.setLimitNumber(True)
                    topic.setItemCount(30)
                    folder.portal_workflow.doActionFor(topic, "show_internally")
            except:
#                import traceback
#                traceback.print_exc()
                pass


def adaptDefaultPortal(context):
    """
       Adapt some properties of the portal
    """
    site = context.getSite()

    #deactivate tabs auto generation in navtree_properties
    #site.portal_properties.site_properties.disable_folder_sections = True
    #remove default created objects like events, news, ...
    for id in ('events', 'news', 'Members'):
        try:
            site.manage_delObjects(ids=[id, ])
            logger.info('%s folder deleted' % id)
        except AttributeError:
            continue

    #change the content of the front-page
    try:
        frontpage = getattr(site, 'front-page')
        frontpage.setTitle(_("front_page_title", context))
        frontpage.setDescription(_("front_page_descr", context))
        frontpage.setText(_("front_page_text", context), mimetype='text/html')
        #remove the presentation mode
        frontpage.setPresentation(False)
        frontpage.reindexObject()
        logger.info('front page adapted')
    except AttributeError:
        #the 'front-page' object does not exist...
        pass

    #reactivate old Topic
    site.portal_types.Topic.manage_changeProperties(global_allow=True)
    for action in site.portal_controlpanel.listActions():
        if action.id == 'portal_atct':
            action.visible = True

    #permissions
    #Removing owner to 'hide' sharing tab
    site.manage_permission('Sharing page: Delegate roles', ('Manager', 'Site Administrator'),
                           acquire=0)
    #Hiding layout menu
    site.manage_permission('Modify view template', ('Manager', 'Site Administrator'),
                           acquire=0)


def configure_rolefields(context):
    """
        Configure the rolefields on types
    """
    roles_config = {'localroleconfig': {
    }, 'treating_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': ['Contributor', 'Editor', 'Reviewer']},
        'proposed_to_agent': {'validateur': ['Contributor', 'Editor', 'Reviewer'],
                              'editeur': ['Contributor', 'Editor', 'Reviewer'],
                              'lecteur': ['Reader']},
        'in_treatment': {'validateur': ['Contributor', 'Editor', 'Reviewer'],
                         'editeur': ['Contributor', 'Editor', 'Reviewer'],
                         'lecteur': ['Reader']},
        'closed': {'validateur': ['Reviewer'],
                   'editeur': ['Reviewer'],
                   'lecteur': ['Reader']},
    }, 'recipient_groups': {
        #'created': {},
        #'proposed_to_manager': {},
        'proposed_to_service_chief': {'validateur': ['Reader']},
        'proposed_to_agent': {'validateur': ['Reader'],
                              'editeur': ['Reader'],
                              'lecteur': ['Reader']},
        'in_treatment': {'validateur': ['Reader'],
                         'editeur': ['Reader'],
                         'lecteur': ['Reader']},
        'closed': {'validateur': ['Reader'],
                   'editeur': ['Reader'],
                   'lecteur': ['Reader']},
    },
    }
    for keyname in roles_config:
        msg = add_fti_configuration('dmsincomingmail', roles_config[keyname], keyname=keyname)
        if msg:
            logger.warn(msg)


def configureBatchImport(context):
    """
        Add batch import configuration
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    logger.info('Configure batch import')
    registry = getUtility(IRegistry)
    import imio.dms.mail as imiodmsmail
    productpath = imiodmsmail.__path__[0]

    if not registry.get('collective.dms.batchimport.batchimport.ISettings.fs_root_directory'):
        registry['collective.dms.batchimport.batchimport.ISettings.fs_root_directory'] = \
            os.path.join(productpath, u'batchimport/toprocess')
    if not registry.get('collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory'):
        registry['collective.dms.batchimport.batchimport.ISettings.processed_fs_root_directory'] = \
            os.path.join(productpath, u'batchimport/toprocess')
    if not registry.get('collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping'):
        registry['collective.dms.batchimport.batchimport.ISettings.code_to_type_mapping'] = \
            [{'code': u'in', 'portal_type': u'dmsincomingmail'}]


def configureImioDmsMail(context):
    """
        Add french test imio dms mail configuration
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    logger.info('Configure imio dms mail')
    registry = getUtility(IRegistry)

    if not registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'):
        registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.mail_types'] = [
            {'mt_value': u'Courrier', 'mt_title': u'Courrier', 'mt_active': True},
            {'mt_value': u'Facture', 'mt_title': u'Facture', 'mt_active': True},
            {'mt_value': u'Retour recommandé', 'mt_title': u'Retour recommandé', 'mt_active': True},
        ]


def configureContactPloneGroup(context):
    """
        Add french test contact plonegroup configuration
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    logger.info('Configure contact plonegroup')
    registry = getUtility(IRegistry)
    site = context.getSite()
    if not registry.get(FUNCTIONS_REGISTRY):
        registry[FUNCTIONS_REGISTRY] = [
            {'fct_title': u'Encodeur', 'fct_id': u'encodeur'},
            {'fct_title': u'Lecteur', 'fct_id': u'lecteur'},
            {'fct_title': u'Éditeur', 'fct_id': u'editeur'},
            {'fct_title': u'Validateur', 'fct_id': u'validateur'},
        ]
    if not registry.get(ORGANIZATIONS_REGISTRY):
        contacts = site['contacts']
        own_orga = contacts['plonegroup-organization']
        departments = own_orga.listFolderContents(contentFilter={'portal_type': 'organization'})
        services0 = own_orga[departments[0].id].listFolderContents(contentFilter={'portal_type': 'organization'})
        services2 = own_orga[departments[2].id].listFolderContents(contentFilter={'portal_type': 'organization'})
        registry[ORGANIZATIONS_REGISTRY] = [
            services0[0].UID(),
            services0[1].UID(),
            departments[1].UID(),
            services2[0].UID(),
        ]
        # Add users to created groups
        site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_validateur" % services0[0].UID())
        site.acl_users.source_groups.addPrincipalToGroup('agent', "%s_editeur" % services0[0].UID())
        site.acl_users.source_groups.addPrincipalToGroup('lecteur', "%s_lecteur" % services0[0].UID())


def addTestDirectory(context):
    """
        Add french test data: directory
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding test directory')
    if hasattr(site, 'contacts'):
        logger.warn('Nothing done: directory contacts already exists. You must first delete it to reimport!')
        return

    # Directory creation
    position_types = [{'name': u'Secrétaire', 'token': 'secretaire'},
                      {'name': u'Employé', 'token': 'employe'},
                      {'name': u'Président', 'token': 'president'},
                      {'name': u'Secrétaire général', 'token': 'secretaire-gen'},
                      {'name': u'Receveur', 'token': 'receveur'},
                      ]

    organization_types = [{'name': u'Commune', 'token': 'commune'},
                          {'name': u'CPAS', 'token': 'cpas'},
                          {'name': u'SA', 'token': 'sa'},
                          ]

    organization_levels = [{'name': u'Département', 'token': 'department'},
                           {'name': u'Service', 'token': 'service'},
                           ]

    params = {'title': "Contacts",
              'position_types': position_types,
              'organization_types': organization_types,
              'organization_levels': organization_levels,
              }
    site.invokeFactory('directory', 'contacts', **params)
    contacts = site['contacts']
    site.portal_workflow.doActionFor(contacts, "show_internally")
    #blacklistPortletCategory(context, contacts, CONTEXT_CATEGORY, u"plone.leftcolumn")

    # Organisations creation (in directory)
    params = {'title': u"Ma Commune",
              'organization_type': u'commune',
              'zip_code': u'0010',
              'city': u'Ma ville',
              'street': u'Rue de la Commune',
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'macommune', **params)
    macommune = contacts['macommune']

    params = {'title': u"Service Urbanisme",
              'organization_type': u'service',
              'zip_code': u'0011',
              'city': u'Ma ville2',
              'street': u"Rue de l'urbanisme",
              'number': u'12',
              }
    macommune.invokeFactory('organization', 'service-urba', **params)
    serviceurba = macommune['service-urba']

    params = {'title': u"Mon CPAS",
              'organization_type': u'cpas',
              'zip_code': u'0010',
              'city': u'Ma ville',
              'street': u'Rue du CPAS',
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'moncpas', **params)
    moncpas = contacts['moncpas']

    params = {'title': u"Electrabel",
              'organization_type': u'sa',
              'zip_code': u'0020',
              'city': u'E-ville',
              'street': u"Rue de la l'électron",
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'electrabel', **params)
    electrabel = contacts['electrabel']

    # Positions creation (in organisations)
    params = {'title': u"Président",
              'position_type': u'president',
              }
    moncpas.invokeFactory('position', 'president', **params)

    params = {'title': u"Secrétaire du CPAS",
              'position_type': u'secretaire-gen',
              }
    moncpas.invokeFactory('position', 'secretaire-cpas', **params)

    params = {'title': u"Receveur",
              'position_type': u'receveur',
              }
    moncpas.invokeFactory('position', 'receveur', **params)

    params = {'title': u"Agent",
              'position_type': u'employe',
              }
    moncpas.invokeFactory('position', 'agent', **params)

    params = {'title': u"Bourgmestre",
              'position_type': u'president',
              }
    macommune.invokeFactory('position', 'bourgmestre', **params)

    params = {'title': u"Secrétaire communal",
              'position_type': u'secretaire-gen',
              }
    macommune.invokeFactory('position', 'secretaire-com', **params)

    params = {'title': u"Receveur",
              'position_type': u'receveur',
              }
    macommune.invokeFactory('position', 'receveur', **params)

    params = {'title': u"Agent",
              'position_type': u'employe',
              }
    macommune.invokeFactory('position', 'agent', **params)
    serviceurba.invokeFactory('position', 'agent', **params)

    params = {'title': u"Employé",
              'position_type': u'employe',
              }
    electrabel.invokeFactory('position', 'employe', **params)

    # Persons creation (in directory)
    params = {'lastname': u'Gère',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1961, 11, 22),
              'email': u'jean.gere@moncpas.be',
              'phone': u'012/345.678',
              'additional_address_details': u'Bâtiment D',
              }
    contacts.invokeFactory('person', 'jeangere', **params)
    jeangere = contacts['jeangere']

    params = {'lastname': u'Permis',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1971, 11, 22),
              'email': u'jean.permis@maville.be',
              'phone': u'012/345.678',
              }
    contacts.invokeFactory('person', 'jeanpermis', **params)
    jeanpermis = contacts['jeanpermis']

    params = {'lastname': u'Courant',
              'firstname': u'Jean',
              'gender': u'M',
              'person_title': u'Monsieur',
              'birthday': datetime.date(1981, 11, 22),
              'email': u'jean.courant@electrabel.be',
              'phone': u'012/345.678',
              }
    contacts.invokeFactory('person', 'jeancourant', **params)
    jeancourant = contacts['jeancourant']

    # Held positions creation (in persons)
    intids = getUtility(IIntIds)

    # link to a defined position
    pdc = moncpas['president']
    params = {'start_date': datetime.date(2001, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(pdc)),
              }
    jeangere.invokeFactory('held_position', 'pdc', **params)

    pop = macommune['agent']
    params = {'start_date': datetime.date(2003, 5, 25),
              'end_date': datetime.date(2008, 5, 25),
              'position': RelationValue(intids.getId(pop)),
              }
    jeanpermis.invokeFactory('held_position', 'pop', **params)
    urba = serviceurba['agent']
    params = {'start_date': datetime.date(2008, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(urba)),
              }
    jeanpermis.invokeFactory('held_position', 'urba', **params)

    # link to an organisation
    params = {'start_date': datetime.date(2005, 5, 25),
              'end_date': datetime.date(2100, 1, 1),
              'position': RelationValue(intids.getId(electrabel)),
              }
    jeancourant.invokeFactory('held_position', 'electrabel', **params)


def addTestMails(context):
    """
        Add french test data: mails
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding test mails')
    import imio.dms.mail as imiodmsmail
    filespath = "%s/batchimport/toprocess/incoming-mail" % imiodmsmail.__path__[0]
    files = [unicode(name) for name in os.listdir(filespath)
             if os.path.splitext(name)[1][1:] in ('pdf', 'doc', 'jpg')]
    files_cycle = cycle(files)

    intids = getUtility(IIntIds)

    class dummy(object):
        def __init__(self, context, request):
            self.context = context
            self.request = request

    contacts = site['contacts']
    senders = [
        RelationValue(intids.getId(contacts['electrabel'])),  # sender is the organisation
        RelationValue(intids.getId(contacts['jeancourant'])),  # sender is a person
        RelationValue(intids.getId(contacts['jeancourant']['electrabel'])),  # sender is a person of electrabel
        RelationValue(intids.getId(contacts['jeanpermis']['urba'])),  # sender is a person with a position
    ]
    # incoming mails
    ifld = site['incoming-mail']
    data = dummy(site, site.REQUEST)
    j = 0
    for i in range(1, 10):
        if not 'courrier%d' % i in ifld:
            params = {'title': 'Courrier %d' % i,
                      'mail_type': 'courrier',
                      'internal_reference_no': internalReferenceIncomingMailDefaultValue(data),
                      'reception_date': receptionDateDefaultValue(data),
                      'sender': senders[j],
                      }
            ifld.invokeFactory('dmsincomingmail', id='courrier%d' % i, **params)
            mail = ifld['courrier%d' % i]
            if i % 4:
                j += 1
            else:
                j = 0
            filename = files_cycle.next()
            with open("%s/%s" % (filespath, filename), 'rb') as fo:
                file_object = NamedBlobFile(fo.read(), filename=filename)
                createContentInContainer(mail, 'dmsmainfile', title='', file=file_object)

    # outgoing mails
    ofld = site['outgoing-mail']
    for i in range(1, 10):
        if not 'reponse%d' % i in ofld:
            inmail = ifld['courrier%d' % i]
            params = {'title': 'Réponse %d' % i,
                      'internal_reference_no': internalReferenceOutgoingMailDefaultValue(data),
                      'mail_date': mailDateDefaultValue(data),
                      #temporary in comment because it doesn't pass in test and case probably errors when deleting site
                      #'in_reply_to': [RelationValue(intids.getId(inmail))],
                      'recipients': [inmail.sender],
                      }
            ofld.invokeFactory('dmsoutgoingmail', id='reponse%d' % i, **params)


def addTestUsersAndGroups(context):
    """
        Add french test data: users and groups
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()

    # creating users
    is_mountpoint = len(site.absolute_url_path().split('/')) > 2

    def generatePassword(length):
        return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(length))

    users = {
        ('scanner', u'Scanner'): ['Batch importer'],
        ('encodeur', u'Jean Encodeur'): [],
        ('dirg', u'Maxime DG'): ['General Manager'],
        ('chef', u'Michel Chef'): [],
        ('agent', u'Fred Agent'): [],
        ('lecteur', u'Jef Lecteur'): [],
    }
    password = 'Dmsmail69!'
    if is_mountpoint:
        password = site.portal_registration.generatePassword()

    for uid, fullname in users.keys():
        try:
            member = site.portal_registration.addMember(id=uid, password=password,
                                                        roles=['Member'] + users[(uid, fullname)])
            member.setMemberProperties({'fullname': fullname, 'email': 'test@macommune.be'})
        except ValueError, exc:
            if str(exc).startswith('The login name you selected is already in use'):
                continue
            logger("Error creating user '%s': %s" % (uid, exc))

    if api.group.get('encodeurs') is None:
        api.group.create('encodeurs', 'Encodeurs courrier')
        site['incoming-mail'].manage_addLocalRoles('encodeurs', ['Contributor', 'Reader'])
        site['contacts'].manage_addLocalRoles('encodeurs', ['Contributor', 'Editor', 'Reader'])
#        site['incoming-mail'].reindexObjectSecurity()
        api.group.add_user(groupname='encodeurs', username='scanner')
        api.group.add_user(groupname='encodeurs', username='encodeur')


def addOwnOrganization(context):
    """
        Add french test data: own organization
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()
    contacts = site['contacts']

    if hasattr(contacts, 'plonegroup-organization'):
        logger.warn('Nothing done: plonegroup-organization already exists. You must first delete it to reimport!')
        return

    # Organisations creation (in directory)
    params = {'title': u"Mon organisation",
              'organization_type': u'commune',
              'zip_code': u'0010',
              'city': u'Ma ville',
              'street': u'Rue de la commune',
              'number': u'1',
              }
    contacts.invokeFactory('organization', 'plonegroup-organization', **params)
    own_orga = contacts['plonegroup-organization']

    # Departments and services creation
    sublevels = [
        (u'Département Jeunesse', [u'Cité de l\'Enfance', u'AMO Ancrages', u'MCAE Cité P\'tit',
                                   u'MCAE Bébé Lune', u'Crèche de Mons ', u'Crèche de Jemappes',
                                   u'Crèche Nid Douillet', u'SAEC']),
        (u'Département Égalité des chances', []),
        (u'Département GRH', [u'Personnel', u'Traitements']),
        (u'Département du Patrimoine', [u'Technique', u'Technique administratif', u'Patrimoine']),
        (u'Département du DG', [u'Cabinet du DG', u'Cellule Marchés Publics', u'IPP', u'FRCE']),
        (u'Département du Président', [u'Cabinet du Président']),
        (u'Département des Aînés', [u'BMB', u'MRS Havré', u'Acasa']),
        (u'Département Social', [u'Aide générale', u'Service personnes âgées', u'Service social administratif', u'SIP',
                                 u'Guidance / Médiation', u'VIF', u'Logement', u'EFT', u'Service juridique']),
        (u'Département informatique', []),
        (u'Département des Finances', [u'Gestion Financière', u'Cellule Financière', u'Directeur financier',
                                       u'Homes Extérieurs', u'Avances et Récupérations', u'Assurances']),
    ]
    idnormalizer = queryUtility(IIDNormalizer)
    for (department, services) in sublevels:
        id = own_orga.invokeFactory('organization', idnormalizer.normalize(department),
                                    **{'title': department, 'organization_type': u'department'})
        dep = own_orga[id]
        for service in services:
            dep.invokeFactory('organization', idnormalizer.normalize(service),
                              **{'title': service, 'organization_type': u'service'})


def configureDocumentViewer(context):
    """
        Set the settings of document viewer product
    """
    from collective.documentviewer.settings import GlobalSettings
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()
    gsettings = GlobalSettings(site)
    gsettings.storage_location = os.path.join(os.getcwd(), 'var', 'dv_files')
    gsettings.storage_type = 'Blob'
    gsettings.pdf_image_format = 'jpg'
    if 'excel' not in gsettings.auto_layout_file_types:
        gsettings.auto_layout_file_types += ('excel', 'image')
    gsettings.show_search = True


def refreshCatalog(context):
    """
        Reindex catalog
    """
    if not context.readDataFile("imiodmsmail_data_marker.txt"):
        return
    site = context.getSite()
    site.portal_catalog.refreshCatalog()
