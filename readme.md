# DryRunovate Reporter

## Overview

The **DryRunovate Reporter** is a Python-based tool designed to process Renovate Dry-Run logs and generate an HTML report summarizing the state of all pull requests (PRs). It provides insights into the PR statuses (see below) and dependencies, making it easier to test and debug Renovate configurations without actually making any changes to the repository.

---

## Statuses
The PR statuses tell you what would happen with each PR when using a certain Renovate configuration:

- **NEW**: The PR would be created
- **UNCHANGED**: The PR would remain unchaged
- **UPDATED**: The PR would be updated
- **DISCARDED**: The PR would be discarded
- **SKIPPED**: This PR would be skipped and no changes would be applied to it (click the question mark for more info)
- **ERROR**: There was an error with this PR (click question mark for more info)
- **PENDING**: This PR is pending (click question mark for more info)
- **AUTOMERGED**: This PR would be automerged
- **UNKNOWN**: The status of this PR is unknown


---

## Installation

### Prerequisites

- Python 3.12 or higher

### Clone the repository
```bash
    git clone https://github.com/e-solutions-GmbH/dry-runovate-reporter.git
```

## Usage

### Command-Line
The tool can be executed via the command line. Below is the syntax:

```bash
python DryRunovateReporter.py --log <log_file_path> --out <output_file_path> --config <config_file_path>
```

#### Arguments

* ```--log```: Path to the Renovate log file.
* ```--out```: Path to where the output HTML file should be created. If the path leads to a directory then the file 
will be stored inside that directory with the name `DryRunovateReport_DATE_TIME.html`. `DATE` is the current date in the
format DAY-MONTH-YEAR. `TIME` is the current time in the format HOUR-MINUTES-SECONDS (24-hour format). If the path leads 
to a file then the report will be stored in said file.
* ```--config```: Path to the configuration JSON file.

### As a module
In order to use this script as a module, import it and then call the function ```execute``` with its required parameters. For example:

```python
import DryRunovateReporter

# Example usage
log_file_path = "path/to/log/file.log"
output_file_path = "path/to/output/file.html"
config_file_path = "path/to/config/file.json"

execute(log_file_path, output_file_path, config_file_path)
```

## Configuration

As this tool parses the Dry-Run logs, it depends on the log file and its entries having a certain structure. In order to increase the robustness of the tool, the regex patterns used to parse the logs are not hard-coded in the script. Instead, they are read from a JSON configuration file. If the log structure were to change, then theoretically only the configuration file has to be modified. 
The configuration file must contain the following 13 values:

* ```branches_info_start_pattern```: pattern that matches the start of the "branches info extended" section. This section contains all PRs (except autoclosed ones) and their correponding state.
* ```branches_info_end_pattern```: pattern that matches the end of the "branches info extended" section.
* ```repository_name_pattern```: pattern used to capture the repository name from the first line of a "branches info extended" section.
* ```timestamp_base_pattern```: pattern that matches the log's timestamps.
* ```timestamp_base_pattern_placeholder```: timestamp placeholder text used in other patterns.
* ```timestamp_pattern```: pattern used to remove timestamps from the log entries.
* ```dry_run_info_pattern_general```: pattern that matches the log's dry run entries.
* ```dry_run_info_pattern_autoclosed```: pattern that matches the first line of a "PR autoclosed" dry run log entry.
* ```dry_run_info_autoclosed_pr_title_line_number```: this number determines how many lines below the first line of a "PR autoclosed" dry run log entry is the pr title line of the entry
* ```dry_run_info_autoclosed_pr_title_pattern```: pattern used to capture the pr title value of a "PR autoclosed" dry run log entry
* ```updated_branch_pattern```: pattern that matches dry run log entries mentioning that a PR was updated
* ```created_branch_pattern```: pattern that matches dry run log entries mentioning that a PR was created
* ```commited_files_pattern```: pattern that matches dry run log entries mentioning that files would be committed to a branch

## HTML Report
The generated HTML report includes:

* **Repository Filter**: Dropdown to filter PRs by repository.
* **PR Details**: Table summarizing PR title, branch name, result, dependency information, and versions.
* **Extra info popup**: Detailed dry-run information accessible by clicking the question icon next to the PR Status.

## Testing

To run the tests:

```bash
python -m unittest discover tests
```

## Contributing

Contributions are welcome! Please create an issue describing your planned contribution and await approval from the repo maintainers before working on it.

## License

This project is licensed under the MIT License. See the ```LICENSE``` file for details.

We are not affiliated in any way with Renovate and this is not an official Renovate product.


