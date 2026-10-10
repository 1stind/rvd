#!/usr/bin/env bash
# Install only from an operator-reviewed checkout on the existing Tencent host.
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" = 0 ]
[ -f /etc/rvd/production.env ]
[ -f /etc/rvd/loadtest.env ]
[ -x /srv/rvd/venv/bin/python ]
if ! id rvd-build >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/rvd-build --shell /usr/sbin/nologin rvd-build
fi
runuser -u rvd-build -- test ! -r /etc/rvd/production.env
install -d -m 700 /var/lib/rvd-deploy
install -d -m 755 /usr/local/lib/rvd
install -m 644 deploy/auto_deploy.py /usr/local/lib/rvd/auto_deploy.py
install -m 644 deploy/rvd-auto-deploy.service deploy/rvd-auto-deploy.timer /etc/systemd/system/
# The retained manual release must still start after a failed automatic activation.
if [ ! -e /srv/rvd/current/.venv ]; then
  ln -s /srv/rvd/venv /srv/rvd/current/.venv
fi
install -m 644 deploy/rvd.service /etc/systemd/system/rvd.service
systemd-analyze verify /etc/systemd/system/rvd.service /etc/systemd/system/rvd-auto-deploy.service /etc/systemd/system/rvd-auto-deploy.timer
systemctl daemon-reload
systemctl enable --now rvd-auto-deploy.timer
