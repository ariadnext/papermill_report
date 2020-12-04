import ast
import json
import logging
import os
import pwd
import re
import stat
import sys
import traceback as tb
import typing as tp
from datetime import datetime
from http.client import responses
from pathlib import Path
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

import papermill as pm
from jinja2 import Template
from tornado import web
from tornado.log import app_log

from .utils import _execute_command, update_git_repository

ANONYMOUS_USER = "anonymous_pm_report"

if os.environ.get("JUPYTERHUB_API_TOKEN"):
    from jupyterhub.services.auth import HubOAuthenticated
else:
    # Deactivate authentication
    class HubOAuthenticated:
        def get_current_user(self):
            return {"name": ANONYMOUS_USER}


def _serialize_exception(error: BaseException, message: str = "") -> dict:
    """Serialize an exception in sendable JSON.

    Args:
        error: Exception to serialize
        message: Error message

    Returns:
        Exception serialized
    """
    if isinstance(error, CalledProcessError):
        return {
            "code": error.returncode,
            "command": error.cmd,
            "message": message,
            "error": str(error.stderr),
        }
    else:
        return {
            "message": message,
            "error": str(error),
            "traceback": tb.format_tb(getattr(sys, "last_traceback", None)),
        }


class ReportHandler(HubOAuthenticated, web.RequestHandler):
    """Common base handler class for the reports."""

    @property
    def broken_path(self) -> str:
        """str: User broken report path."""
        username = self.get_current_user()["name"]
        return self.settings.get("broken_path").replace("USERNAME", username)

    @property
    def log(self) -> logging.Logger:
        """Logger: Application logger"""
        return self.settings.get("log", app_log)

    @property
    def notebook_dir(self) -> str:
        """str: User notebook directory."""
        username = self.get_current_user()["name"]
        return self.settings.get("notebook_dir").replace("USERNAME", username)

    @property
    def report_git_url(self) -> tp.Optional[str]:
        """str or None: Git repository URL."""
        return self.settings.get("report_git_url")

    @property
    def report_root_path(self) -> str:
        """str: Local report path."""
        return self.settings.get("report_root_path")

    @property
    def report_path(self) -> str:
        """str: Local report path."""
        return self.settings.get("report_path")

    def get_template(self, name: str) -> Template:
        """Return the jinja template object for a given name

        Args:
            name: Template name

        Returns:
            jinja2.Template object
        """
        return self.settings["jinja2_env"].get_template(name)

    def render_template(self, name: str, **kwargs) -> str:
        """Render the given template with the provided arguments

        Args:
            name: Template name
            **kwargs: Template arguments

        Returns:
            The generated template
        """
        template_ns = dict(base_url="/", static_url=self.static_url)
        template_ns.update(kwargs)
        template = self.get_template(name)
        return template.render(**template_ns)

    def static_url(self, path: str, include_host: bool = None, **kwargs: tp.Any) -> str:
        """Returns a static URL for the given relative static file path.

        This method requires you set the ``static_path`` setting in your
        application (which specifies the root directory of your static
        files).

        This method returns a versioned url (by default appending
        ``?v=<signature>``), which allows the static files to be
        cached indefinitely.  This can be disabled by passing
        ``include_version=False`` (in the default implementation;
        other static file implementations are not required to support
        this, but they may support other options).

        By default this method returns URLs relative to the current
        host, but if ``include_host`` is true the URL returned will be
        absolute.  If this handler has an ``include_host`` attribute,
        that value will be used as the default for all `static_url`
        calls that do not pass ``include_host`` as a keyword argument.

        """
        guess = super().static_url(path, include_host, **kwargs)
        static_path = self.settings.get("static_path")

        if not (Path(static_path) / path).exists():
            static_prefix = self.settings.get("static_url_prefix")
            guess = guess.replace(static_prefix, "/hub/static/", 1)

        return guess

    def write_error(
        self,
        status_code: int,
        message: str = "",
        traceback: str = "",
        exc_info: tp.Tuple = None,
        **kwargs,
    ):
        """render custom error pages

        Args:
            status_code: Error HTTP status code
            message: Error message
            traceback: Error traceback
            exc_info: Tuple[exception type, exception value, traceback]
        """
        status_message = responses.get(status_code, "Unknown HTTP Error")
        exception = "(unknown)"
        if exc_info:
            exception = exc_info[1]
            # get the custom message, if defined
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, "reason", "")
            if reason:
                status_message = reason

            traceback = tb.format_tb(exc_info[2])

        # build template namespace
        ns = dict(
            status_code=status_code,
            status_message=status_message,
            message=message,
            traceback=traceback,
        )

        self.set_header("Content-Type", "text/html")
        # render the template
        html = self.render_template("error.html", **ns)

        self.set_status(status_code)
        self.write(html)

    async def _get_templates(self) -> tp.List[tp.Dict]:
        """Get the templates list.

        A template object is defined as:

            @dataclass
            class Template():
                path: str
                parameters: List[Parameter]

        Returns:
            List[Template] List of templates

        Raises:
            CalledProcessError: If the git repository cannot be updated.
        """
        await update_git_repository(
            self.report_root_path, self.report_path, self.report_git_url
        )
        template_dir = Path(self.report_root_path) / self.report_path

        templates = []
        for report in template_dir.glob("**/*.ipynb"):
            parameters = {}
            try:
                parameters = pm.inspect_notebook(str(report))
            except BaseException:
                self.log.warning(
                    f"Unable to get the parameters for notebook '{report!s}'.",
                    exc_info=True,
                )
            templates.append(
                {
                    "path": str(report.relative_to(template_dir)),
                    # Convert to dict to avoid OrderedDict as parameter object
                    "parameters": [dict(v) for v in parameters.values()],
                }
            )

        return templates


class TemplatesHandler(ReportHandler):
    """Handle available Jupyter templates."""

    PARAMETER_NAME = re.compile(r"^root\[(?P<name>.*)\]$")

    @web.authenticated
    async def get(self):
        """Render a page allowing the user to pick a report to generate."""
        try:
            templates = await self._get_templates()
        except CalledProcessError as error:
            message = f"Fail to update the Jupyter reports repository '{self.report_git_url}'."
            self.log.error(message, exc_info=error)
            self.write_error(500, message, exc_info=sys.exc_info())
        else:
            html = self.render_template("report.html", reports=templates)
            self.write(html)

    @web.authenticated
    async def post(self):
        """Form callback to generate a report"""
        arguments = {}
        path = None
        for key, raw_value in self.request.body_arguments.items():
            value = raw_value[0].decode("utf-8")
            if key == "path":
                path = value
            else:
                match = TemplatesHandler.PARAMETER_NAME.match(key)
                if match:
                    arguments[match["name"]] = value

        self.redirect("?".join((path, urlencode(arguments))))


class TemplatesAPIHandler(ReportHandler):
    """REST API handler for the templates list."""

    @web.authenticated
    async def get(self):
        """List the Jupyter reports available."""
        self.set_header("Content-Type", "application/json")

        try:
            templates = await self._get_templates()
        except CalledProcessError as error:
            message = f"Fail to update the Jupyter reports repository '{self.report_git_url}'."
            self.log.error(message, exc_info=error)
            self.write_error(500, message, exc_info=sys.exc_info())
        else:
            self.set_status(200)
            self.finish(json.dumps({"templates": templates}))

    def write_error(
        self,
        status_code: int,
        message: str = "",
        error: tp.Optional[Exception] = None,
        **kwargs,
    ):
        """Format an error in JSON.

        Args:
            status_code: Error HTTP status code
            message: Error message
            error: Exception
        """
        self.set_header("Content-Type", "application/json")
        self.set_status(status_code)
        self.write(json.dumps(_serialize_exception(error, message)))


class TemplateHandler(ReportHandler):
    """Handle report generator."""

    def _save_broken_report(self, notebook_path: Path, username: str) -> Path:
        """Save the notebook in the broken reports folder.

        Args:
            notebook_path: The broken report
            username: User name trying to execute the report
        Returns:
            The copied broken report path
        """
        local_user = pwd.getpwnam(username) if username != ANONYMOUS_USER else None
        prefix = datetime.strftime(datetime.now(), "%Y-%m-%d") + "_broken_"
        broken_notebook = Path(self.broken_path) / (prefix + notebook_path.name)
        if not broken_notebook.parent.exists():
            broken_notebook.parent.mkdir(parents=True)
            if local_user:
                os.chown(broken_notebook.parent, local_user.pw_uid, local_user.pw_gid)

        broken_notebook.write_text(Path(notebook_path).read_text())
        if local_user:
            os.chown(broken_notebook, local_user.pw_uid, local_user.pw_gid)

        return broken_notebook

    def _report_error(
        self, message: str, error: BaseException, broken_report: tp.Optional[Path]
    ):
        """Generate the error page.

        Args:
            message: Understable error message
            error: Python error
            broken_report: Broken notebook path or None
        """
        if broken_report is not None:
            link = f"'{broken_report!s}'"
            if "JUPYTERHUB_BASE_URL" in os.environ:
                try:
                    url = "hub/user-redirect/lab/tree/".join(
                        (
                            os.environ["JUPYTERHUB_BASE_URL"],
                            str(broken_report.relative_to(self.notebook_dir)),
                        )
                    )
                    link = f'<a href="{url}">{broken_report!s}</a>'
                except ValueError:
                    pass  # if broken_report is not a subfolder of self.notebook_dir
            message = message + f"<br>The broken report has been copied to {link}."

        if isinstance(error, CalledProcessError):
            message += "<br><br><code>" + error.stderr.replace("\n", "<br>") + "</code>"

        self.log.error(message, exc_info=error)
        self.write_error(500, message, exc_info=sys.exc_info())

    @web.authenticated
    async def get(self, template_path: str):
        """Generate the template.

        .. note::
            Only the first query argument value is taken into account
            i.e. case such a=1&b="hello"&a=2 => parameters = {"a": 1, "b": "hello"}

        Args:
            template_path: The template path
            parameters ({name: str, value: Any}): Optional, parameters dictionary read from query arguments

        Returns:
            The HTML report resulting from the notebook execution
        """
        username = self.get_current_user()["name"]
        try:
            await update_git_repository(
                self.report_root_path, self.report_path, self.report_git_url
            )
        except CalledProcessError as error:
            self.log.error(
                f"Fail to update the Jupyter reports repository '{self.report_git_url}'.",
                exc_info=error,
            )

        template_dir = (Path(self.report_root_path) / self.report_path).resolve()

        tpl_path = template_dir / template_path
        if not tpl_path.exists():
            self.write_error(
                404, message=f"Template file <em>{tpl_path}</em> does not exists."
            )
            return

        with TemporaryDirectory() as output:
            os.chmod(
                output, stat.S_IRWXU | stat.S_IRWXO
            )  # Need to make the temporary file accessible by the request user
            tmp_folder = Path(output)
            parameters_file = tmp_folder / "parameters.json"
            # As the input parameters are read as bytes from the query, they are
            #  evaluated dynamically to retrieve their Python type.
            parameters = {}
            for key, values in self.request.query_arguments.items():
                value = values[0].decode("utf-8")
                try:
                    parameters[key] = ast.literal_eval(
                        value
                    )  # Forbidden none literal expression
                except BaseException:
                    self.log.debug(
                        f"Failed to evaluated '{value}' for parameter '{key}'."
                    )
                    parameters[key] = value

            parameters_file.write_text(json.dumps(parameters))
            output_nb = tmp_folder / tpl_path.name

            command = [
                sys.executable,
                "-m",
                "papermill.cli",
                "--no-progress-bar",
                "--request-save-on-cell-execute",
                "--parameters_file",
                str(parameters_file),
                str(tpl_path),
                str(output_nb),
            ]
            try:
                if username != ANONYMOUS_USER:
                    # Generate the report impersonating the authenticated user
                    await _execute_command(
                        ["su", username, "-l", "-c", " ".join(command)], cwd=tmp_folder
                    )
                else:
                    await _execute_command(command, cwd=tmp_folder)
            except BaseException as error:
                broken_report = None
                if output_nb.exists():
                    broken_report = self._save_broken_report(output_nb, username)
                return self._report_error(
                    f"Fail to execute report <em>{template_path!s}</em> with parameters '{self.request.query_arguments}'.",
                    error,
                    broken_report,
                )

            try:
                command = [
                    sys.executable,
                    "-m",
                    "nbconvert",
                    "--to=html",
                    f'--output-dir="{tmp_folder!s}"',
                    str(output_nb),
                ]

                if username != ANONYMOUS_USER:
                    await _execute_command(
                        ["su", username, "-l", "-c", " ".join(command)], cwd=tmp_folder
                    )
                else:
                    await _execute_command(command, cwd=tmp_folder)
            except BaseException as error:
                broken_report = None
                if output_nb.exists():
                    broken_report = self._save_broken_report(output_nb, username)
                return self._report_error(
                    f"Fail to render report '{template_path!s}' as HTML.",
                    error,
                    broken_report,
                )

            report = output_nb.parent / (output_nb.stem + ".html")

            self.set_status(200)
            self.finish(report.read_text())
