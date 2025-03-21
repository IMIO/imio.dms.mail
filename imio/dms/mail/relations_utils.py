# encoding: utf-8
from collections import defaultdict
from collective.relationhelpers.api import cleanup_intids
from collective.relationhelpers.api import get_field_and_schema_for_fieldname
from collective.relationhelpers.api import logger
from collective.relationhelpers.api import purge_relations
from collective.relationhelpers.api import RELATIONS_KEY
from collective.relationhelpers.api import store_relations
from imio.helpers.batching import batch_get_keys
from imio.helpers.batching import batch_globally_finished
from imio.helpers.batching import batch_handle_key
from imio.helpers.batching import batch_loop_else
from imio.helpers.batching import batch_skip_key
from imio.helpers.batching import can_delete_batch_files
from imio.helpers.catalog import get_intid
from imio.pyutils.batching import batch_delete_files
from imio.pyutils.system import dump_pickle
from imio.pyutils.system import load_pickle
from plone.app.linkintegrity.handlers import modifiedDexterity as modifiedContent
from plone.app.linkintegrity.handlers import referencedRelationship
from plone.app.relationfield.event import update_behavior_relations
from plone.app.uuid.utils import uuidToObject
from plone.dexterity.interfaces import IDexterityContent
from z3c.relationfield import event
from z3c.relationfield import Relation
from z3c.relationfield import RelationChoice
from z3c.relationfield import RelationList
from z3c.relationfield import RelationValue
from z3c.relationfield.event import updateRelations
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.intid import IIntIds

import os
import transaction


def transaction_commit(do_it):
    if do_it:
        transaction.commit()


def remove_duplicates(all_relations):
    unique_relations = []
    seen = set()
    seen_add = seen.add
    for i in all_relations:
        hashable = tuple(i.items())
        if hashable not in seen:
            unique_relations.append(i)
            seen_add(hashable)
        else:
            logger.info(u"Dropping duplicate: {}".format(hashable))

    if len(unique_relations) < len(all_relations):
        logger.info("Dropping {0} duplicates".format(len(all_relations) - len(unique_relations)))
        all_relations = unique_relations
    return all_relations


def restore_relations(portal, batch_value):
    """Restore relations from a annotation on the portal. Copied from collective.relationhelpers.api"""
    all_relations = IAnnotations(portal)[RELATIONS_KEY]
    # [{'to_uuid': '6a2e3ae6762e46e0a9b1b06585874964', 'from_attribute': 'recipients',
    # 'from_uuid': '04548ec46a9b4a899cd4ab7416d47639'}]
    ar_len = len(all_relations)
    logger.info("Loaded {0} relations to restore".format(ar_len))
    update_linkintegrity = set()
    modified_items = set()
    modified_relation_lists = defaultdict(list)
    load_pickle("modified_relation_lists.pkl", modified_relation_lists)
    intids = getUtility(IIntIds)
    batch_keys, config = batch_get_keys("restored_relations.pkl", ar_len,
                                        add_files=[os.path.abspath("modified_relation_lists.pkl")])
    for item in all_relations:
        hashable = tuple(item.items())
        if batch_skip_key(hashable, batch_keys, config):
            continue
        # logger.info(u'Restored {} of {} relations...'.format(index, len(all_relations)))
        source_obj = uuidToObject(item["from_uuid"])
        target_obj = uuidToObject(item["to_uuid"])

        if not source_obj:
            logger.info(u"{} source is missing".format(item["from_uuid"]))
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        if not target_obj:
            logger.info(u"{} target is missing".format(item["to_uuid"]))
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        if not IDexterityContent.providedBy(source_obj):
            logger.info(u"{} source is no dexterity content".format(source_obj.portal_type))
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        if not IDexterityContent.providedBy(target_obj):
            logger.info(u"{} target is no dexterity content".format(target_obj.portal_type))
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        from_attribute = item["from_attribute"]
        to_id = get_intid(target_obj, intids)

        if from_attribute == referencedRelationship:
            # Ignore linkintegrity for now. We'll rebuilt it at the end!
            update_linkintegrity.add(item["from_uuid"])
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        # if from_attribute == ITERATE_RELATION_NAME:
        #     # Iterate relations are not set as values of fields
        #     relation = StagingRelationValue(to_id)
        #     event._setRelation(source_obj, ITERATE_RELATION_NAME, relation)
        #     continue

        field_and_schema = get_field_and_schema_for_fieldname(from_attribute, source_obj.portal_type)
        if field_and_schema is None:
            # the from_attribute is no field
            # we could either create a fresh relation or log the case
            logger.info(u"No field. Setting relation: {}".format(item))
            event._setRelation(source_obj, from_attribute, RelationValue(to_id))
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        field, schema = field_and_schema
        relation = RelationValue(to_id)

        if isinstance(field, RelationList):
            # logger.info(
            #     "Add relation to relationslist {} from {} to {}".format(
            #         from_attribute, source_obj.absolute_url(), target_obj.absolute_url()
            #     )
            # )
            if item["from_uuid"] in modified_relation_lists.get(from_attribute, []):
                # Do not purge relations
                existing_relations = getattr(source_obj, from_attribute, [])
            else:
                # First touch. Make sure we purge!
                existing_relations = []
            existing_relations.append(relation)
            setattr(source_obj, from_attribute, existing_relations)
            modified_items.add(item["from_uuid"])
            modified_relation_lists[from_attribute].append(item["from_uuid"])
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        elif isinstance(field, (Relation, RelationChoice)):
            # logger.info(
            #     "Add relation {} from {} to {}".format(
            #         from_attribute, source_obj.absolute_url(), target_obj.absolute_url()
            #     )
            # )
            setattr(source_obj, from_attribute, relation)
            modified_items.add(item["from_uuid"])
            if batch_handle_key(hashable, batch_keys, config):
                break
            continue

        else:
            # we should never end up here!
            logger.info(
                "Warning: Unexpected relation {} from {} to {}".format(
                    from_attribute, source_obj.absolute_url(), target_obj.absolute_url()
                )
            )
            if batch_handle_key(hashable, batch_keys, config):
                break
    else:
        batch_loop_else(batch_keys, config)

    update_linkintegrity = set(update_linkintegrity)
    logger.info("Updating linkintegrity for {} items".format(len(update_linkintegrity)))
    for uuid in sorted(update_linkintegrity):
        modifiedContent(uuidToObject(uuid), None)
    transaction_commit(config["bn"] and config["ll"] > config["bn"])
    logger.info("Updating relations for {} items".format(len(modified_items)))
    for uuid in sorted(modified_items):
        obj = uuidToObject(uuid)
        # updateRelations from z3c.relationfield does not properly update relations in behaviors
        # that are registered with a marker-interface.
        # update_behavior_relations (from plone.app.relationfield) does that but does not update
        # those in the main schema. Duh!
        updateRelations(obj, None)
        update_behavior_relations(obj, None)
    transaction_commit(config["bn"] and config["ll"] > config["bn"])

    if batch_keys:  # with batching
        dump_pickle("modified_relation_lists.pkl", modified_relation_lists)
    if can_delete_batch_files(batch_keys, config):
        batch_delete_files(batch_keys, config, rename=True)
    return batch_keys, config


def rebuild_relations(portal, flush_and_rebuild_intids=False):
    annot = IAnnotations(portal)
    batch_value = int(os.getenv("BATCH", "0"))
    if RELATIONS_KEY not in annot:
        store_relations()
        commit = batch_value and len(annot[RELATIONS_KEY]) > batch_value
        purge_relations()
        transaction_commit(commit)
        # if flush_and_rebuild_intids:
        #     flush_intids()
        #     rebuild_intids()
        # else:
        cleanup_intids()
        transaction_commit(commit)
        annot[RELATIONS_KEY] = remove_duplicates(annot[RELATIONS_KEY])
        transaction_commit(commit)

    batch_keys, config = restore_relations(portal, batch_value)
    finished = batch_globally_finished(batch_keys, config)

    if finished and RELATIONS_KEY in IAnnotations(portal):
        del IAnnotations(portal)[RELATIONS_KEY]

    return finished
