# -*- coding: utf-8 -*-
from collective.wfadaptations.api import get_applied_adaptations
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from plone import api

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_2(Migrate_To_3_1):  # noqa

    def run(self):
        self.run_initialization()

        if self.is_in_part("b"):  # upgrade other products
            self.upgradeAll(omit=[u"imio.dms.mail:default"])

        if self.is_in_part("c"):
            # Migrate signer substitutes
            logger.info("Migrating omail_signer_rules dates to omail_signer_substitutes")
            self.runProfileSteps("imio.dms.mail", steps=["plone.app.registry"])
            rk_rules = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_rules"
            rk_subs = "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_signer_substitutes"
            existing_rules = api.portal.get_registry_record(rk_rules, default=[])
            if existing_rules and not any("valid_from" in rule for rule in existing_rules):
                logger.info("omail_signer_rules already migrated, skipping")
            else:
                substitutes = api.portal.get_registry_record(rk_subs, default=[])
                existing_pairs = {(s["absent_signer"], s["substitute_signer"]) for s in substitutes}
                cleaned_rules = []
                new_substitutes_count = 0
                for idx, rule in enumerate(existing_rules):
                    rule = dict(rule)
                    valid_from = rule.pop("valid_from", None)
                    valid_until = rule.pop("valid_until", None)
                    if valid_from or valid_until:
                        # Find the first undated rule after this one with same conditions
                        absent_signer = None
                        for candidate in existing_rules[idx + 1:]:
                            if (not candidate.get("valid_from") and not candidate.get("valid_until")
                                    and candidate["signer"] != rule["signer"]
                                    and candidate["number"] == rule["number"]
                                    and candidate["treating_groups"] == rule["treating_groups"]
                                    and candidate["mail_types"] == rule["mail_types"]
                                    and candidate["send_modes"] == rule["send_modes"]
                                    and candidate["tal_condition"] == rule["tal_condition"]):
                                absent_signer = candidate["signer"]
                                break
                        pair = (absent_signer, rule["signer"])
                        if pair not in existing_pairs:
                            substitutes.append({
                                "absent_signer": absent_signer,
                                "substitute_signer": rule["signer"],
                                "valid_from": valid_from,
                                "valid_until": valid_until,
                            })
                            existing_pairs.add(pair)
                            new_substitutes_count += 1
                    else:
                        cleaned_rules.append(rule)
                api.portal.set_registry_record(rk_rules, cleaned_rules)
                api.portal.set_registry_record(rk_subs, substitutes)
                logger.info("Created {} substitute stub(s) from signer rules".format(new_substitutes_count))

            # Changed permission after plone.restapi installation
            self.portal.manage_permission("plone.restapi: Use REST API", ("Member", ), acquire=0)

            # WFAs
            # can_be_handsigned was renamed can_be_signed
            wf = api.portal.get().portal_workflow["outgoingmail_workflow"]
            old_handsigned_guard = "python:object.wf_conditions().can_be_handsigned()"
            new_signed_guard = "python:object.wf_conditions().can_be_signed()"
            for tr_id in ("propose_to_be_signed", "back_to_be_signed"):
                if tr_id not in wf.transitions:
                    continue
                tr = wf.transitions[tr_id]
                if tr.guard.expr and tr.guard.expr.text == old_handsigned_guard:
                    logger.info("Updating {} guard from can_be_handsigned to can_be_signed".format(tr_id))
                    tr.setProperties(
                        title=tr.title,
                        new_state_id=tr.new_state_id,
                        trigger_type=tr.trigger_type,
                        script_name=tr.script_name,
                        actbox_name=tr.actbox_name,
                        actbox_url=tr.actbox_url,
                        actbox_icon=tr.actbox_icon,
                        actbox_category=tr.actbox_category,
                        props={"guard_permissions": "Review portal content", "guard_expr": new_signed_guard},
                    )
            # Update guard expression on set_to_print/back_to_print wfa
            applied_wfa_names = [dic["adaptation"] for dic in get_applied_adaptations()]
            to_print_applied = "imio.dms.mail.wfadaptations.OMToPrintAdaptation" in applied_wfa_names
            if to_print_applied:
                new_guard = "python:object.wf_conditions().can_set_to_print()"
                for tr_id in ("set_to_print", "back_to_print"):
                    if tr_id not in wf.transitions:
                        continue
                    tr = wf.transitions[tr_id]
                    if tr.guard.expr and tr.guard.expr.text == old_handsigned_guard:
                        logger.info("Updating {} guard from can_be_handsigned to can_set_to_print".format(tr_id))
                        tr.setProperties(
                            title=tr.title,
                            new_state_id=tr.new_state_id,
                            trigger_type=tr.trigger_type,
                            script_name=tr.script_name,
                            actbox_name=tr.actbox_name,
                            actbox_url=tr.actbox_url,
                            actbox_icon=tr.actbox_icon,
                            actbox_category=tr.actbox_category,
                            props={"guard_permissions": "Review portal content", "guard_expr": new_guard},
                        )

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()

        self.run_finish()


def migrate(context):
    Migrate_To_3_1_2(context).run()
