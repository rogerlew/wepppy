#!/bin/sh
# Sourced only by Redis entrypoint/CLI. Never trace or export the resolved value.
set +x
set +a
unset REDIS_PASSWORD_VALUE
redis_secret_file=${REDIS_PASSWORD_FILE:-/run/secrets/redis_password}
redis_secret_error() { echo 'Redis password file is missing, empty or invalid' >&2; exit 1; }
[ -r "$redis_secret_file" ] && [ -f "$redis_secret_file" ] || redis_secret_error
# Validate UTF-8 and reject NUL before shell substitution (which can drop NUL).
# od/awk exist in both the deployed Debian image and pinned Alpine canary image.
od -An -v -tu1 "$redis_secret_file" | LC_ALL=C awk '
function space(c) {
 return (c>=9 && c<=13) || (c>=28 && c<=32) || c==133 || c==160 || c==5760 ||         (c>=8192 && c<=8202) || c==8232 || c==8233 || c==8239 || c==8287 || c==12288
}
function accept(c) {
 if (c==0 || c==13) exit 1
 if (c==10) { terminator=1; return }
 if (terminator || (!count && space(c))) exit 1
 last=c; count++
}
BEGIN { remaining=0; lo=128; hi=191; count=0 }
{
 for (i=1; i<=NF; i++) {
  b=$i+0
  if (remaining) {
   if (b<lo || b>hi) exit 1
   cp=cp*64+b-128; remaining--; lo=128; hi=191
   if (!remaining) accept(cp)
  } else if (b<128) { accept(b) }
  else if (b>=194 && b<=223) { remaining=1; cp=b-192 }
  else if (b>=224 && b<=239) {
   remaining=2; cp=b-224; if (b==224) lo=160; if (b==237) hi=159
  } else if (b>=240 && b<=244) {
   remaining=3; cp=b-240; if (b==240) lo=144; if (b==244) hi=143
  } else { exit 1 }
 }
}
END { if (remaining || !count || space(last)) exit 1 }
' || redis_secret_error
REDIS_PASSWORD_VALUE=$(cat "$redis_secret_file") || redis_secret_error
[ -n "$REDIS_PASSWORD_VALUE" ] || redis_secret_error
# Preserve conventional LF terminators, removed by command substitution, but
# reject ambiguous framing and embedded record delimiters.
case "$REDIS_PASSWORD_VALUE" in
  [[:space:]]*|*[[:space:]]|*'
'*|*"$(printf '\r')"*) redis_secret_error ;;
esac
