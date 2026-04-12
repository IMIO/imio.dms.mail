# -*- coding: utf-8 -*-
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from plone import api

import logging


logger = logging.getLogger("imio.dms.mail")


class Migrate_To_3_1_2(Migrate_To_3_1):  # noqa

    def run(self):
        self.run_initialization()

        if self.is_in_part("b"):  # upgrade other products
            self.upgradeAll(omit=[u"imio.dms.mail:default"])

        if self.is_in_part("c"):  # migrate signer substitutes
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

        if self.is_in_part("g"):  # final steps
            # finished = True  # can be eventually returned and set by batched method
            if self.old_version != self.new_version:
                self.run_finalization()

        self.run_finish()


def migrate(context):
    Migrate_To_3_1_2(context).run()
