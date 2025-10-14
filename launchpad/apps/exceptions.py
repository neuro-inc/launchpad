from uuid import UUID


class AppServiceError(Exception): ...


class AppNotInstalledError(AppServiceError): ...


class AppUnhealthyError(AppServiceError):
    def __init__(self, app_id: UUID):
        self.app_id = app_id


class AppTemplateNotFound(AppServiceError): ...


class AppMissingUrlError(AppServiceError): ...
