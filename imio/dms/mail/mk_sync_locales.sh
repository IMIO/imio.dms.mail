#!/bin/bash
#
# Shell script to manage locales, languages, .po files...
#
# Run this file in your product folder
# E.g. : in yourproduct.name/yourproduct/name
#

CATALOGNAME="imio.dms.mail"

# List of languages used for po initialization (no mandatory update for syncing)
# Ex LANGUAGES="en|English|en-au;en-ca;en-gb;en-us fr|French|fr-fr;fr-be;fr-ca nl|Dutch|nl-be;nl-nl"
LANGUAGES="en|English|en-au;en-ca;en-gb;en-us fr|French|fr-fr;fr-be;fr-ca"

# Create locales folder structure for languages
install -d locales

# Rebuild .pot
echo "Rebuilding locales/generated.pot"
i18ndude rebuild-pot --pot locales/generated_tmp.pot --create $CATALOGNAME .
# remove bad generated msgid: "plone"
sed -n '/^msgid "plone"/{N;s/.*//;x;d;};x;p;${x;p;}' locales/generated_tmp.pot |uniq |sed '1d' > locales/generated.pot
rm locales/generated_tmp.pot

#creating the first pot
if ! test -f locales/$CATALOGNAME.pot; then
    echo "Copying locales/generated.pot to locales/$CATALOGNAME.pot"
    cp locales/generated.pot locales/$CATALOGNAME.pot
fi

#merging new messages
if [ `svn diff locales/generated.pot |grep "^\+[^+]" |wc -l` -le "1" ]; then
    svn revert locales/generated.pot
else
    cp locales/$CATALOGNAME.pot locales/$CATALOGNAME_tmp.pot
    cp locales/generated.pot locales/$CATALOGNAME.pot
#    i18ndude merge --pot locales/$CATALOGNAME.pot --merge locales/generated.pot 2>/dev/null
    i18ndude merge --pot locales/$CATALOGNAME.pot --merge locales/$CATALOGNAME_tmp.pot 2>/dev/null
    rm locales/$CATALOGNAME_tmp.pot
fi

if ! test -f locales/plone.pot || [ "$1" == "rebuild-plone" ]; then
    echo "Rebuilding locales/plone.pot"
    i18ndude rebuild-pot --pot locales/plone.pot --create plone profiles/default/workflows/incomingmail_workflow/
fi

i18ndude merge --pot locales/plone.pot --merge locales/plone-manual.pot 2>/dev/null
if [ `svn diff locales/plone.pot |grep "^\+[^+]" |wc -l` -le "1" ]; then
    svn revert locales/plone.pot
fi

if ! test -f locales/collective.dms.basecontent.pot; then
    echo "Rebuilding locales/collective.dms.basecontent.pot"
    touch locales/collective.dms.basecontent.pot
fi

# Finding pot files
for pot in $(find locales -mindepth 1 -maxdepth 1 -type f -name "*.pot" ! -name generated.pot ! -name *-manual.pot ); do
    #finding pot basename as catalog
    catalog=`basename $pot .pot`
    echo "=> Found pot $pot"
    # First initialization of po files with base languages if po doesn't exist
    for language in $LANGUAGES; do
        arr=(`echo $language | cut -d "|"  --output-delimiter=" " -f 1-`)
        langcode=${arr[0]}
        install -d locales/$langcode/LC_MESSAGES

        PO=locales/$langcode/LC_MESSAGES/$catalog.po
        # Create po file if not exists and modify header
        if ! test -f $PO; then
            touch $PO
            echo " -> Syncing $PO"
            i18ndude sync --pot $pot $PO
            sed -i -e "/^\\\"Domain: DOMAIN/ s/DOMAIN/$catalog/" $PO
            sed -i -e "/^\\\"Language-Code: en/ s/en/$langcode/" $PO
            langname=${arr[1]}
            if [ -n "$langname" ]; then
                sed -i -e "/^\\\"Language-Name: English/ s/English/$langname/" $PO
            fi
            fallbackstr=${arr[2]}
            if [ -n "$fallbackstr" ]; then
                fallbacklist=`echo $fallbackstr | cut -d ";"  --output-delimiter=" " -f 1-`
                echo $fallbacklist
                sed -i -e "/^\\\"Language-Name:/ a\"X-is-fallback-for: $fallbacklist\\\n\"" $PO
            fi
        fi
    done
    # Sync po files
    for lang in $(find locales -mindepth 1 -maxdepth 1 -type d); do
        if test -d $lang/LC_MESSAGES; then
            PO=$lang/LC_MESSAGES/$catalog.po
            # Sync po file
            echo " -> Syncing $PO"
            i18ndude sync --pot $pot $PO

            # Compile .po to .mo
            MO=$lang/LC_MESSAGES/$catalog.mo
            #echo " -> Compiling $MO"
            #msgfmt -o $MO $lang/LC_MESSAGES/$catalog.po
        fi
    done
done