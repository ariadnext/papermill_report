
import sys

c.ServerProxy.servers = {
    "reports": {
        "command": [
            sys.executable,
            "-m",
            "papermill_report",
            '--PapermillReport.ip=0.0.0.0',
            '--PapermillReport.port={port}',
            "--PapermillReport.api_prefix={base_url}reports/",
            "--PapermillReport.broken_reports_dir=.",
            "--PapermillReport.template_root_dir=examples",
        ],
        "timeout": 120,
        "absolute_url": True,
        "launcher_entry": {
            "enabled": True,
            "title": "Papermill Report",
        },
    },
}
