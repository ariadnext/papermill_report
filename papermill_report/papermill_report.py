"""Webservice API."""
import logging
import os
import typing as tp
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from jinja2 import Environment, ChoiceLoader, FileSystemLoader, PackageLoader
from tornado import ioloop, web
from tornado.log import access_log, app_log, gen_log
from traitlets import Dict, Int, List, Unicode, default
from traitlets.config.application import Application

from .handlers import TemplateHandler, TemplatesAPIHandler, TemplatesHandler
from .utils import update_git_repository

if os.environ.get("JUPYTERHUB_API_TOKEN"):
    from jupyterhub.services.auth import HubOAuthCallbackHandler
else:
    # Deactivate authentication
    class HubOAuthCallbackHandler:
        def get(self):
            pass


HERE = Path(__file__).parent


class PapermillReport(Application):

    name = Unicode("papermill-report")

    broken_reports_dir = Unicode(
        "/home/USERNAME/broken_reports",
        help="Folder containing the broken reports",
        config=True,
    )

    config_file = Unicode("papermill_report_config", help="Load this config file").tag(
        config=True
    )

    port = Int(8888, help="Port of the service", config=True)

    git_auth = Unicode(
        None,
        allow_none=True,
        help="Git authentication (username:password)",
        config=True,
    )

    notebook_dir = Unicode(
        "/home/USERNAME", help="Notebook server root directory", config=True
    )

    template_root_dir = Unicode(
        "/opt/papermill_report",
        help="Folder containing the notebook templates project on the server.",
        config=True,
    )

    template_dir = Unicode(
        ".",
        help="Folder containing the notebook templates relative to the `template_root_dir`.",
        config=True,
    )

    template_git_url = Unicode(
        None,
        allow_none=True,
        help="Git repository URL source of the notebook templates",
        config=True,
    )

    template_paths = List(
        trait=Unicode,
        default_value=None,
        allow_none=True,
        help="Paths to search for jinja templates, before using the default templates.",
        config=True,
    )

    api_prefix = Unicode(help="Papermill API prefix")

    @default("api_prefix")
    def _default_api_prefix(self):
        return os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/")

    @default("log_format")
    def _log_format_default(self):
        """override default log format to match Jupyter log"""
        return "[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d] %(message)s"

    aliases = Dict({"config": "PapermillReport.config_file"})

    flags = Dict(
        {"debug": ({"PapermillReport": {"log_level": 10}}, "Set loglevel to DEBUG")}
    )

    @property
    def git_url(self) -> tp.Optional[str]:
        """Returns the report Git repository URL.

        It will include authentication information if available.
        It will return None if no Git repository is defined.

        Returns:
            str or None: Git repository URL
        """
        if self.template_git_url is None:
            return None
        elif self.git_auth is not None:
            url = urlsplit(self.template_git_url)
            # Add auth to netloc
            new_url = list(url)
            new_url[1] = "@".join((self.git_auth, new_url[1]))
            return urlunsplit(new_url)
        else:
            return self.template_git_url

    def _init_logging(self):
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dispatches log messages to a log
        # and all of its ancestors until propagate is set to False.
        # self.log.propagate = False

        for log in app_log, access_log, gen_log:
            # consistent log output name (NotebookApp instead of tornado.access, etc.)
            log.name = self.log.name

        logger = logging.getLogger("tornado")
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)

    def initialize(self, argv=None):
        """Initialize the settings and logger."""
        self.parse_command_line(argv)
        if self.config_file:
            self.load_config_file(self.config_file)

        self._init_logging()

    def make_app(self) -> web.Application:
        """Create the tornado web application.

        Returns:
            The tornado web application.
        """
        static_path = str(HERE / "static")
        static_url_prefix = self.api_prefix + "static/"

        loaders = []
        if self.template_paths:
            loaders.append(FileSystemLoader(self.template_paths))
        loaders.append(PackageLoader("papermill_report"))

        application = web.Application(
            [
                (self.api_prefix, TemplatesHandler),
                (self.api_prefix + "api/templates/", TemplatesAPIHandler),
                (self.api_prefix + r"(?P<template_path>.+\.ipynb)", TemplateHandler),
                (self.api_prefix + "oauth_callback", HubOAuthCallbackHandler),
            ],
            broken_path=self.broken_reports_dir,
            notebook_dir=self.notebook_dir,
            report_root_path=self.template_root_dir,
            report_path=self.template_dir,
            report_git_url=self.git_url,
            log=self.log,
            template_path=str(HERE / "templates"),
            static_path=static_path,
            static_url_prefix=static_url_prefix,
            jinja2_env=Environment(
                loader=ChoiceLoader(loaders), trim_blocks=True, lstrip_blocks=True,
            ),
            cookie_secret=os.urandom(32),
        )
        application.listen(self.port)
        return application

    def start(self):
        """Start the server."""
        _ = self.make_app()
        self.log.info(f"Papermill service listening on port {self.port}")
        self.log.info("Press Ctrl+C to stop")
        # Schedule repository update (or creation) at startup
        ioloop.IOLoop.current().spawn_callback(
            update_git_repository,
            self.template_root_dir,
            self.template_dir,
            self.git_url,
        )
        ioloop.IOLoop.current().start()


def main():
    service = PapermillReport()
    service.initialize()
    service.start()


if __name__ == "__main__":
    main()
