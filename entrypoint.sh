#!/bin/sh
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}

# When started as root, create the target user/group, fix /data ownership,
# then drop privileges and exec the application.
if [ "$(id -u)" = "0" ]; then
    # Ensure group with target GID exists
    if ! getent group "${PGID}" > /dev/null 2>&1; then
        groupadd -g "${PGID}" appgroup
    fi

    # Ensure user with target UID exists
    # 2>/dev/null suppresses "uid outside of UID_MIN/UID_MAX range" warning (e.g. Unraid nobody=99)
    if ! getent passwd "${PUID}" > /dev/null 2>&1; then
        useradd -u "${PUID}" -g "${PGID}" -M -s /sbin/nologin appuser 2>/dev/null
    fi

    # Fix ownership so the target user can write to /data
    chown -R "${PUID}:${PGID}" /data

    # Version-based /data cleanup: wipe on new version, skip on plain restart
    DEPLOY_MARKER="/data/.deployed_version"
    CURRENT_VERSION="${APP_VERSION:-dev}"

    if [ "$CURRENT_VERSION" != "dev" ]; then
        LAST_VERSION=""
        [ -f "$DEPLOY_MARKER" ] && LAST_VERSION=$(cat "$DEPLOY_MARKER")

        if [ "$CURRENT_VERSION" != "$LAST_VERSION" ]; then
            echo "[entrypoint] version changed: ${LAST_VERSION:-none} -> ${CURRENT_VERSION}, cleaning /data ..."
            find /data -mindepth 1 -delete
            echo "$CURRENT_VERSION" > "$DEPLOY_MARKER"
            echo "[entrypoint] /data cleaned."
        fi
    fi

    exec gosu "${PUID}:${PGID}" "$@"
else
    exec "$@"
fi
