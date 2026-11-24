#!/bin/sh
set -eu

git clone --depth 1 --branch "$THEME_REVISION" -- "$THEME_REPOSITORY" /tmp/repo
mkdir -p /opt/keycloak/themes/apolo
cp -R "/tmp/repo/$THEME_PATH/." /opt/keycloak/themes/apolo/
chown -R 1000:0 /opt/keycloak/themes
