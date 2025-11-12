#!/bin/bash
# i18ndude should be available in current $PATH (eg by running
# ``export PATH=$PATH:$BUILDOUT_DIR/bin`` when i18ndude is located in your buildout's bin directory)
#
# For every language you want to translate into you need a
# locales/[language]/LC_MESSAGES/collective.messagesviewlet.po
# (e.g. locales/de/LC_MESSAGES/collective.messagesviewlet.po)

echo "This script is deprecated, please use mk_sync_locales.sh instead."
exit 0

CATALOGNAME=imio.dms.mail

i18ndude rebuild-pot --pot generated_tmp.pot --create $CATALOGNAME ../
# remove bad generated msgid: "plone"
sed -n '/^msgid "plone"/{N;s/.*//;x;d;};x;p;${x;p;}' generated_tmp.pot |uniq |sed '1d' > generated.pot
rm generated_tmp.pot

i18ndude sync --pot $CATALOGNAME.pot */LC_MESSAGES/$CATALOGNAME.po
