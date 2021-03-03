import pytest


@pytest.mark.e2e
def test_broken_report(report_page, base_url, slow_motion):
    # Click input[type="submit"]
    report_page.click('input[type="submit"]')

    # Expect we get a link to open the broken notebook back in JupyterLab
    with report_page.expect_navigation(url=base_url + "/user/marc/lab"):
        report_page.click(r"text=/.*/home/marc/broken_reports/.*broken.*\.ipynb/")

    report_page.waitForSelector(
        "//span[normalize-space(.)=\"An Exception was encountered at 'In [2]'.\"]"
    )

    slow_motion()


@pytest.mark.e2e
def test_no_parameters(report_page, slow_motion):
    report_page.select_option('select[id="report-selector"]', "no_parameters.ipynb")
    # No form displayed
    assert report_page.inner_text('div[id="autoform-holder"]') == ""

    report_page.click('input[type="submit"]')

    report_page.wait_for_selector(r"text=/.*None.*/")

    slow_motion()


@pytest.mark.e2e
def test_simple_execute(report_page, slow_motion):
    report_page.select_option(
        'select[id="report-selector"]', "subfolder/simple_execute.ipynb"
    )

    report_page.fill('input[name="root[msg]"]', '"Welcome"')

    report_page.click('input[type="submit"]')

    report_page.wait_for_selector("text=/.*WelcomeWelcomeWelcome.*/")

    slow_motion()


@pytest.mark.e2e
def test_direct_access_to_report(login, base_url, slow_motion):
    login.goto(base_url + "/services/report/subfolder/simple_execute.ipynb?n=4&msg=cherry%20")

    # Acknowledge oauth
    login.click('input[type="submit"]')

    login.wait_for_selector("text=/.*cherry cherry cherry cherry.*/")

    slow_motion()
