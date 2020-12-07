import json
import re
from subprocess import check_call

import pytest
from jupyter_client import kernelspec
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from papermill_report.papermill_report import PapermillReport


FORBIDDEN = re.compile(r"[\/\.:\s]+")


@pytest.fixture(scope="function")
def git_project(tmp_path):
    git_ref = tmp_path / "ref"
    for name in kernelspec.find_kernel_specs():
        ks = kernelspec.get_kernel_spec(name)
        if ks.language != "python":
            continue
        metadata = {
            "kernelspec": {
                "name": name,
                "language": ks.language,
                "display_name": ks.display_name,
            }
        }
        break

    fake_notebooks = {
        git_ref
        / "notebook1.ipynb": new_notebook(
            cells=[
                new_code_cell(
                    "a: int = 2 # Beautiful", metadata={"tags": ["parameters"]}
                ),
                new_code_cell("a"),
            ],
            metadata=metadata,
        ),
        git_ref
        / "subfolder"
        / "notebook2.ipynb": new_notebook(
            cells=[
                new_code_cell(
                    "b: str = 'The famous B' # Beautiful",
                    metadata={"tags": ["parameters"]},
                ),
                new_markdown_cell("# Surprise"),
                new_code_cell("f'{b}eaver'"),
            ],
            metadata=metadata,
        ),
    }

    for path, nb in fake_notebooks.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(nb))

    # Initialize the git repository
    check_call(["git", "init", str(git_ref)])
    check_call(["git", "add", "-A"], cwd=str(git_ref))
    check_call(["git", "commit", "-am", '"First commit"'], cwd=str(git_ref))

    yield git_ref


@pytest.fixture(scope="function")
def template_root_dir(tmp_path):
    tpl_folder = tmp_path / "local_tpl"
    yield tpl_folder


@pytest.fixture
def app(tmp_path, template_root_dir, git_project):
    service = PapermillReport(
        broken_reports_dir=str(tmp_path / "broken_reports"),
        template_root_dir=str(template_root_dir),
        template_git_url=str(git_project),
    )
    service.initialize()
    return service.make_app()
