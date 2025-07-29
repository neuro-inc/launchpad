from launchpad.apps.registry.shared.openwebui import (
    APP_NAME_OPEN_WEB_UI,
    OpenWebUIApp,
    OpenWebUIAppContext,
)

APPS = {
    APP_NAME_OPEN_WEB_UI: OpenWebUIApp,
}


APPS_CONTEXT = {
    APP_NAME_OPEN_WEB_UI: OpenWebUIAppContext,
}


T_App = OpenWebUIApp
