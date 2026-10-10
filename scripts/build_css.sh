#!/usr/bin/env sh
# Build the production stylesheet that replaces the Tailwind Play CDN.
# base.html serves app/static/css/tailwind.css when it exists at startup and
# falls back to the CDN otherwise. Re-run after template changes, then restart.
#
# Dev: `./scripts/build_css.sh --watch` keeps the file current, so dev renders
# exactly like production. The CDN fallback injects Tailwind after custom.css /
# public.css, which flips the cascade (e.g. preflight line-heights win there).
set -eu
cd "$(dirname "$0")/.."
node deploy/assets/node_modules/tailwindcss/lib/cli.js -c tailwind.config.js \
  -i app/static/css/tailwind.input.css \
  -o app/static/css/tailwind.css --minify "$@"
