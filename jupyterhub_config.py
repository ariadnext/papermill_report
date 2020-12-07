"""JupyterHub configuration for testing this service."""
import sys

# c.JupyterHub.log_level = "DEBUG"

c.JupyterHub.authenticator_class = "jupyterhub.auth.DummyAuthenticator"

# c.DummyAuthenticator.password = 'password'

c.Authenticator.admin_users = {"jovyan"}
c.Authenticator.allowed_users = {"jovyan", "marc"}

c.JupyterHub.redirect_to_server = False

c.JupyterHub.spawner_class = "jupyterhub.spawner.LocalProcessSpawner"

c.LocalProcessSpawner.notebook_dir = "/home/{username}"

c.Spawner.default_url = "/lab"

c.JupyterHub.services = [
    {
        "name": "report",
        "url": "http://127.0.0.1:8888",
        "command": [
            sys.executable,
            "-m",
            "papermill_report",
            "--debug",
            "--PapermillReport.ip",
            "127.0.0.1",
            "--PapermillReport.port",
            "8888",
            "--PapermillReport.template_root_dir",
            "/opt/ariadnext/reports/",
            # Uncomment the two following options if you want to test the git case
            # "--PapermillReport.template_git_url",
            # "/tmp/papermill_report/",
            # "--PapermillReport.template_dir",
            # "examples"
        ],
        # "oauth_no_confirm": True,
    }
]
