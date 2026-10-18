#!/bin/sh
# Rootless Ubuntu 22.04 userland via bubblewrap (fake root in a user namespace). usage: run.sh CMD...
R="${ROOTFS:-$(dirname "$(readlink -f "$0")")/rootfs}"  # extract ubuntu-base-22.04.5-base-amd64.tar.gz here
exec bwrap --bind "$R" / --dev /dev --proc /proc --tmpfs /tmp --ro-bind /etc/resolv.conf /etc/resolv.conf \
  --unshare-user --uid 0 --gid 0 --unshare-pid --die-with-parent \
  --setenv PATH /usr/sbin:/usr/bin:/sbin:/bin --setenv HOME /root --setenv DEBIAN_FRONTEND noninteractive \
  ${WORK:+--bind "$WORK" /work} "$@"
