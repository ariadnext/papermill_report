import json

from nbformat.v4 import new_markdown_cell, new_notebook

from papermill_report.utils import update_git_repository


async def test_update_git_repository(template_root_dir, git_project):
    await update_git_repository(template_root_dir, f"file://{git_project!s}")

    counter = 0
    for f in git_project.rglob("*.ipynb"):
        counter += 1
        relative_f = f.relative_to(git_project)
        clone_f = git_project / relative_f
        assert f.read_bytes() == clone_f.read_bytes()

    assert counter == 2


async def test_Settings_update_git_clean(template_root_dir, git_project):
    # Initial clone
    await update_git_repository(template_root_dir, git_url=f"file://{git_project!s}")

    # Dummy change
    nb = template_root_dir / "notebook1.ipynb"
    nb.write_text(json.dumps(new_notebook(cells=[new_markdown_cell("# Title")])))

    # Clean should occur
    await update_git_repository(template_root_dir, git_url=f"file://{git_project!s}")

    counter = 0
    for f in git_project.rglob("*.ipynb"):
        counter += 1
        relative_f = f.relative_to(git_project)
        clone_f = git_project / relative_f
        assert f.read_bytes() == clone_f.read_bytes()

    assert counter == 2
