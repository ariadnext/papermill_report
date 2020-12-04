import pytest


@pytest.mark.e2e
def test_broken_report(report_page):
    # Click input[type="submit"]
    report_page.click('input[type="submit"]')

    # Expect we get a link to open the broken notebook back in JupyterLab
    with report_page.expect_navigation(url="http://localhost:8000/user/marc/lab"):
        report_page.click(r"text=/.*/home/marc/broken_reports/.*broken.*\.ipynb/")

    report_page.waitForSelector(
        "//span[normalize-space(.)=\"An Exception was encountered at 'In [2]'.\"]",
        timeout=5000,
    )


@pytest.mark.e2e
def test_no_parameters(report_page):
    report_page.selectOption('select[id="report-selector"]', "no_parameters.ipynb")
    # No form displayed
    assert report_page.innerText('div[id="autoform-holder"]') == ""

    report_page.click('input[type="submit"]')


@pytest.mark.e2e
def test_simple_execute(report_page):
    report_page.selectOption(
        'select[id="report-selector"]', "subfolder/simple_execute.ipynb"
    )

    report_page.fill('input[name="root[msg]"]', '"Welcome"')

    report_page.click('input[type="submit"]')

    report_page.waitForSelector("text=/.*WelcomeWelcomeWelcome.*/", timeout=3000)
