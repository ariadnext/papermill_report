import json

from papermill_report.papermill_report import PapermillReport


def test_configuration_file(tmp_path):
    fake_config = tmp_path / "papermill_service_config.json"

    broken_folder = "/path/USERNAME/broken"
    tpl_folder = "/path/to/templates"
    git_folder = "subfolder"
    git_tpl = "https://my.git.io/namespace/project.git"
    git_auth = "powerfull:user"
    nb_dir = "/home/USERNAME"
    tpl_paths = ["one", "two/tpl"]
    fake_config.write_text(
        json.dumps(
            {
                "PapermillReport": {
                    "broken_reports_dir": broken_folder,
                    "notebook_dir": nb_dir,
                    "template_root_dir": tpl_folder,
                    "template_dir": git_folder,
                    "template_git_url": git_tpl,
                    "git_auth": git_auth,
                    "template_paths": tpl_paths
                }
            }
        )
    )

    app = PapermillReport()
    app.initialize(argv=[f"--config={fake_config!s}"])

    assert app.broken_reports_dir == broken_folder
    assert app.notebook_dir == nb_dir
    assert app.git_auth == git_auth
    assert app.template_dir == git_folder
    assert app.template_git_url == git_tpl
    assert app.template_root_dir == tpl_folder
    assert app.template_paths == tpl_paths


def test_configuration_cli():
    broken_folder = "/path/USERNAME/broken"
    tpl_folder = "/path/to/templates"
    git_folder = "subfolder"
    git_tpl = "https://my.git.io/namespace/project.git"
    git_auth = "powerfull:user"
    nb_dir = "/home/USERNAME"
    tpl_paths = ["one", "two/tpl"]

    app = PapermillReport()
    app.initialize(
        argv=[
            f"--PapermillReport.broken_reports_dir={broken_folder}",
            f"--PapermillReport.notebook_dir={nb_dir}",
            f"--PapermillReport.git_auth={git_auth}",
            f"--PapermillReport.template_dir={git_folder}",
            f"--PapermillReport.template_git_url={git_tpl}",
            f"--PapermillReport.template_root_dir={tpl_folder}",
            f"--PapermillReport.template_paths={tpl_paths}",
        ]
    )

    assert app.broken_reports_dir == broken_folder
    assert app.notebook_dir == nb_dir
    assert app.git_auth == git_auth
    assert app.template_dir == git_folder
    assert app.template_git_url == git_tpl
    assert app.template_root_dir == tpl_folder
    assert app.template_paths == tpl_paths
