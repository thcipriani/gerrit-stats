LOGFILE=$1

# A rebase is a patch
sed -i s/rebase/patch/ "$LOGFILE"

# CI stuff
sed -i s/verified-2/ciFail/ "$LOGFILE"
sed -i s/verified2/ciSuccess/ "$LOGFILE"
sed -i s/verified-1/ciFail/ "$LOGFILE"
sed -i s/verified1/ciSuccess/ "$LOGFILE"

sed -i s/submit1/merge/ "$LOGFILE"

# RequestChanges
sed -i s/codereview-1/requestChanges/ "$LOGFILE"
sed -i s/codereview-2/requestChanges/ "$LOGFILE"

# equivalent to merge
sed -i /codereview2/d "$LOGFILE"

# Meaningless, yeah, CR+1: meaningless!
sed -i /codereview1/d "$LOGFILE"
sed -i /verified0/d "$LOGFILE"
sed -i /codereview0/d "$LOGFILE"
