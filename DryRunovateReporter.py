import re
import json
import argparse
import sys
from typing import TextIO, no_type_check
from typing import Final
import logging
import os
from datetime import datetime

UNCHANGED_PR : Final[str] = "UNCHANGED"
UPDATED_PR: Final[str] = "UPDATED"
NEW_PR: Final[str] = "NEW"
DISCARDED_PR: Final[str] = "DISCARDED"
SKIPPED_PR: Final[str] = "SKIPPED"
ERROR_PR: Final[str] = "ERROR"
PENDING_PR: Final[str] = "PENDING"
AUTOMERGED_PR: Final[str] = "AUTOMERGED"
UNKNOWN_PR: Final[str] = "UNKNOWN"

class Config:

    """Configuration class for script"""

    def __init__(self, branches_info_start_pattern : str, branches_info_end_pattern : str, repository_name_pattern : str, timestamp_base_pattern : str, timestamp_base_pattern_placeholder : str, timestamp_pattern : str, dry_run_info_pattern_general : str, dry_run_info_pattern_autoclosed : str, dry_run_info_autoclosed_pr_title_line_number : int, dry_run_info_autoclosed_pr_title_pattern : str, updated_branch_pattern : str, created_branch_pattern : str, commited_files_pattern : str):
        self.branches_info_start_pattern = branches_info_start_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.branches_info_end_pattern = branches_info_end_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.repository_name_pattern = repository_name_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.timestamp_pattern = timestamp_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.dry_run_info_pattern_general = dry_run_info_pattern_general.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.dry_run_info_pattern_autoclosed = dry_run_info_pattern_autoclosed.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.dry_run_info_autoclosed_pr_title_line_number = dry_run_info_autoclosed_pr_title_line_number
        self.dry_run_info_autoclosed_pr_title_pattern = dry_run_info_autoclosed_pr_title_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.updated_branch_pattern = updated_branch_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.created_branch_pattern = created_branch_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)
        self.commited_files_pattern = commited_files_pattern.replace(timestamp_base_pattern_placeholder, timestamp_base_pattern)


class LogFileParsingError(Exception):
    """
    Custom exception raised when errors occur during log file parsing operations.

    Attributes:
        message (str): A descriptive error message explaining the parsing issue.

    Example:
        >>> raise LogFileParsingError("Start of section found but no end was found")
        LogFileParsingError: Start of section found but no end was found
    """
    def __init__(self, message : str):
        self.message = message
        super().__init__(self.message)


class HTMLReportGenerator:
    """
    Generates an HTML report from processed Renovate dry-run data.

    The generated HTML report includes:
    - Repository dropdown filter for easy navigation
    - Tables showing PR details for each repository
    - Interactive modals with additional dry-run information

    Attributes:
        json_data: Structured data containing repository and branch information
        dry_run_infos: List of tuples containing dry-run log entries
        config: Configuration object with regex patterns and settings
        output_file: Path where the HTML report will be saved

    Example:
        >>> config = Config(...)
        >>> json_data = {"items": [{"repository": "repo1", "branchesInformation": [...]}]}
        >>> dry_run_infos = [("repo1", "branch1", "info")]
        >>> HTMLReportGenerator(json_data, dry_run_infos, config, "report.html")._generate()
    """
    @no_type_check
    def __init__(self, json_data, dry_run_infos, config, output_file):
        self.json_data = json_data
        self.dry_run_infos = dry_run_infos
        self.config = config
        self.output_file = output_file

    @no_type_check
    def _generate(self):
        html_parts : list[str] = list()
        html_parts.append("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Renovate PR-Report</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }
                h1 {
                    color: #2c3e50;
                }
                .filter-container {
                    margin: 20px 0;
                }
                .repository-dropdown {
                    padding: 10px;
                    font-size: 16px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    z-index: 1;
                }
                table, th, td {
                    border: 1px solid #bdc3c7;
                }
                th, td {
                    padding: 10px;
                    text-align: left;
                }
                th {
                    background-color: #ecf0f1;
                }
                .hidden {
                    display: none;
                }
                .modal {
                    background-color: rgba(0,0,0,0.8);
                    display: none;
                    z-index: 2;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    overflow: auto;
                    position: fixed;
                }
                .modal-content {
                    background-color: #fefefe;
                    margin: 10% auto;
                    padding: 20px;
                    border: 1px solid #888;
                    width: 80%;
                    max-width: 800px;
                    border-radius: 8px;
                    position: relative;
                }
                .close {
                    color: #aaa;
                    position: absolute;
                    top: 10px;
                    right: 20px;
                    font-size: 28px;
                    font-weight: bold;
                    cursor: pointer;
                }
                .close:hover,
                .close:focus {
                    color: #000;
                    text-decoration: none;
                    cursor: pointer;
                }
                .question-icon {
                    cursor: pointer;
                    font-size: 18px;
                    margin-left: 5px;
                    color: #3498db;
                    vertical-align: middle;
                }
                .question-icon:hover {
                    color: #217dbb;
                }
            </style>
            <script>
                function filterByRepository() {
                    const selectedRepository = document.getElementById("repositoryDropdown").value;
                    const tables = document.querySelectorAll(".repository-table");

                    tables.forEach(table => {
                        if (selectedRepository === "all" || table.dataset.repository === selectedRepository) {
                            table.classList.remove("hidden");
                        } else {
                            table.classList.add("hidden");
                        }
                    });
                }
                function showModal(helpInfo) {
                    const modal = document.getElementById('resultModal');
                    const modalContent = document.getElementById('modalContent');
                    modalContent.innerHTML = helpInfo;
                    modal.style.display = 'block';
                }
                function closeModal() {
                    document.getElementById('resultModal').style.display = 'none';
                }
                window.onclick = function(event) {
                    var modal = document.getElementById('resultModal');
                    if (event.target == modal) {
                        modal.style.display = "none";
                    }
                }
            </script>
        </head>
        <body>
            <h1>Renovate PR-Report</h1>
            <div class="filter-container">
                <label for="repositoryDropdown">Filter by Repository:</label>
                <select id="repositoryDropdown" class="repository-dropdown" onchange="filterByRepository()">
                    <option value="all">All</option>
        """)

        # Add repository options to the dropdown
        for item in self.json_data['items']: # type: ignore
            repository = item['repository'] # type: ignore
            html_parts.append(f'<option value="{repository}">{repository}</option>')

        html_parts.append("""
                </select>
            </div>
            <div id="resultModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <div id="modalContent"></div>
                </div>
            </div>
        """)

        # Add tables for each repository
        for item in self.json_data['items']:
            repository = item['repository']
            branches_info = item.get('branchesInformation', [])

            html_parts.append(f'<table class="repository-table" data-repository="{repository}">')
            html_parts.append(f"""
            <caption class="repository">{repository}</caption>
            <thead>
                <tr>
                    <th>PR Title</th>
                    <th>Branch Name</th>
                    <th>PR Status</th>
                    <th>Dependency Name</th>
                    <th>Current</th>
                    <th>New</th>
                </tr>
            </thead>
            <tbody>
            """)

            for branch in branches_info:
                pr_title = branch.get('prTitle', 'N/A')
                pr_state, help_info = _determine_pr_status(branch.get('result'), repository, pr_title, self.config, self.dry_run_infos)
                if not help_info:
                    help_info = "No extra information available"
                branch_name = branch.get('branchName', 'N/A')
                upgrades = branch.get('upgrades', [])
                
                if len(upgrades) > 0:
                    html_parts.append(f"""
                    <tr>
                        <td rowspan={len(upgrades)}>{pr_title}</td>
                        <td rowspan={len(upgrades)}>{branch_name}</td>
                        <td rowspan={len(upgrades)}>{pr_state}<span class="question-icon" title="Click for more info" onclick="showModal('{help_info}')">&#x2753;</span></td>
                        <td>{upgrades[0].get('packageName', 'N/A')}</td>
                        <td>{upgrades[0].get('currentVersion', 'N/A')}</td>
                        <td>{upgrades[0].get('newVersion', 'N/A')}</td>
                    </tr>
                    """)

                    upgrades.pop(0)

                    for upgrade in upgrades:
                        dep_name = upgrade.get('packageName', 'N/A')
                        current_version = upgrade.get('currentVersion', 'N/A')
                        new_version = upgrade.get('newVersion', 'N/A')

                        html_parts.append(f"""
                        <tr>
                            <td>{dep_name}</td>
                            <td>{current_version}</td>
                            <td>{new_version}</td>
                        </tr>
                        """)
                else:
                    html_parts.append(f"""
                <tr>
                    <td>{pr_title}</td>
                    <td>{branch_name}</td>
                    <td>{pr_state}<span class="question-icon" title="Click for more info" onclick="showModal('{help_info}')">&#x2753;</span></td>
                    <td>'N/A'</td>
                    <td>'N/A'</td>
                    <td>'N/A'</td>
                </tr>
                """)

            html_parts.append("""
            </tbody>
            </table>
            """)

        html_parts.append("""
        </body>
        </html>
        """)

        if os.path.isdir(self.output_file):
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            self.output_file = os.path.join(self.output_file, f"DryRunovateReport_{timestamp}.html")

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        with open(self.output_file, 'w', encoding='utf-8') as file:
            file.write("".join(html_parts))

def _parse_arguments():
    parser = argparse.ArgumentParser(description="This script takes a Renovate Dry-Run Job Log file with Log-Level DEBUG and generates an HTML report which shows all the PRs that would be created by Renovate." \
    "The report shows for each PR: PR title, PR state (new or edited), dependency name, dependency current version and dependency new version.")
    parser.add_argument("--log", help="Path to the log file")
    parser.add_argument("--out", help="Path where the HTML report should be saved")
    parser.add_argument("--config", help="Path to the configuration file. The configuration file contains the regex patterns that the script should look for in the log file.")

    args = parser.parse_args()
    if not args.log or not args.out or not args.config:
        raise ValueError("Not all required arguments were passed. Use the argument --help to learn how to use this script.")
    if not os.path.exists(args.log):
        raise FileNotFoundError(f"Log file '{args.log}' not found.")
    if not os.path.exists(args.config):
        raise FileNotFoundError(f"Configuration file '{args.config}' not found.")

    return args

def _read_config_file(config_file_path : str):
    """
    Reads and parses the configuration file.

    Parameters:
        config_file_path (str): Path to the configuration file.

    Returns:
        Config: An instance of the `Config` class initialized with the parsed data.

    Raises:
        json.JSONDecodeError: If the configuration file contains invalid JSON.
    """
    try:
        with open(config_file_path, "r") as file:
            config_data = json.load(file)
            return Config(**config_data)
    except json.JSONDecodeError as ex:
        raise json.JSONDecodeError(f"Invalid JSON format in configuration file '{config_file_path}'.", ex.doc, ex.pos)

def _get_next_line(file : TextIO) -> str | None:
    """
    Reads the next line from a file and strips whitespace.

    Parameters:
        file (TextIO): File object to read from.

    Returns:
        str | None: The next line stripped of whitespace, or `None` if the end of the file is reached.
    """
    try:
        line : str = next(file)
        return line.strip()
    except StopIteration:
        return None

def _extract_repository_name(line : str, repository_name_pattern : str) -> str:
    """
    Extracts the repository name from a line using a regex pattern.

    Parameters:
        line (str): The line to extract the repository name from.
        repository_name_pattern (str): Regex pattern to match the repository name.

    Returns:
        str: Extracted repository name.

    Raises:
        ValueError: If the repository name cannot be extracted.
    """
    match = re.search(repository_name_pattern, line)
    if match:
        return match.group(1)
    else:
        raise ValueError("Repository name could not be extracted.")

def _find_branches_lists(log_file_path : str, config : Config):
    """
    Extracts the list of branches and their information from the "branches info extended" section of the Renovate log file.

    Parameters:
        log_file_path (str): Path to the log file.
        config (Config): Configuration object containing regex patterns.

    Returns:
        dict[str, list[str]]: A dictionary where keys are repository names and values are lists of lines from the relevant sections.

    Raises:
        LogFileError: If the log file is empty or no relevant sections are found.
    """
    start_pattern = config.branches_info_start_pattern
    end_pattern = config.branches_info_end_pattern
    repository_name_pattern = config.repository_name_pattern
    relevant_sections : dict[str, list[str]] = dict()
    relevant_section : list[str] = list()
    repository_name = None

    # Read the log file
    with open(log_file_path, "r") as file:
        line = _get_next_line(file)
        if not line:
            raise LogFileParsingError("Log file is empty.")
        while line:
            if re.match(start_pattern, line):
                repository_name = _extract_repository_name(line, repository_name_pattern)
                line = _get_next_line(file)
                while line:
                    if re.match(end_pattern, line):
                        relevant_sections[repository_name] = list(relevant_section)
                        relevant_section.clear()
                        line = _get_next_line(file)
                        break
                    else:
                        relevant_section.append(line)
                        line = _get_next_line(file)
            else:
                line = _get_next_line(file)

        else:
            if repository_name is None:
                logging.warning("No relevant sections found in the log file.")
            else:
                if repository_name not in relevant_sections:
                    raise LogFileParsingError(f"Start of the relevant section for repository {repository_name} was found but no end was found.")
                
        logging.info(f"{len(relevant_sections)} branches found in the log file.")
        return relevant_sections

def _process_branches_lists(relevant_sections : dict[str, list[str]], autoclosed_branches : list[tuple[str | None, str | None]], timestamp_pattern : str):
    """
    Processes the relevant sections to remove timestamps then structures all this data into a dictonary.

    Parameters:
        relevant_sections (dict[str, list[str]]): Dictionary of repository names and their corresponding log lines.
        timestamp_pattern (str): Regex pattern to remove timestamps from the log lines.

    Returns:
        dict[str, list[dict[str, str]]]: A dictionary containing the structured branch information for each repository.

    Raises:
        json.JSONDecodeError: If JSON parsing fails for any section.
    """
    items : list[dict[str, str]] = list()

    for repository, lines in relevant_sections.items():
        stripped_lines = [re.sub(timestamp_pattern, "", line) for line in lines]

        joined_string = "{" + "".join(stripped_lines) + "}"
        
        try:
            items.append({"repository": repository, **json.loads(joined_string)})
        except json.JSONDecodeError as ex:
            raise json.JSONDecodeError(f"Failed to parse JSON: {ex}", ex.doc, ex.pos)
    
    for repository, prTitle in autoclosed_branches:
        branches_info = "{" + "\"branchesInformation\":" + "[" + "{" + f"\"prTitle\": \"{prTitle or "N/A"}\", \"result\": \"discarded\"" + "}" + "]" + "}"
        items.append({"repository": repository or "N/A", **json.loads(branches_info)})

    return {"items": items}
    
def _extract_general_dry_run_infos(log_file_path : str, config: Config):
    """
    Finds and extracts the "DRY-RUN" log entries in the log file.

    Parameters:
        log_file_path (str): Path to the log file.
        config (Config): Configuration object containing regex patterns.

    Returns:
        list[tuple[str | None, str | None, str | None]]: A list of tuples containing repository name, branch name, and DRY-RUN entry.
    """
    dry_run_infos : list[tuple[str | None, str | None, str | None]] = list()
    with open(log_file_path, "r") as file:
        line = _get_next_line(file)
        while line:
            match = re.match(config.dry_run_info_pattern_general, line)
            if match:
                repository_name = match.group('repository_name')
                branch_name = match.group('branch_name')
                info = match.group('info')
                dry_run_infos.append((repository_name, branch_name, info))
                line = _get_next_line(file)
            else:
                line = _get_next_line(file)
    
    return dry_run_infos

def _extract_and_process_autoclosed_dry_run_infos(log_file_path : str, config: Config):

    result : list[tuple[str | None, str | None]] = list()

    with open(log_file_path, "r") as file:
        line = _get_next_line(file)
        while line:
            match = re.match(config.dry_run_info_pattern_autoclosed, line)
            if match:
                repository_name = match.group('repository_name')
                for _ in range(config.dry_run_info_autoclosed_pr_title_line_number):   
                    line = _get_next_line(file)
                if line is not None:
                    match = re.match(config.dry_run_info_autoclosed_pr_title_pattern, line)
                    if match:
                        pr_title = match.group('pr_title')
                        result.append((repository_name, pr_title))
                    else:
                        raise LogFileParsingError(f"pr title was not found {config.dry_run_info_autoclosed_pr_title_line_number} lines below the log entry matched by config.dry_run_info_pattern_autoclosed. Instead the following line was found: {line}")
                else:
                    raise LogFileParsingError(f"pr title was not found {config.dry_run_info_autoclosed_pr_title_line_number} lines below the log entry matched by config.dry_run_info_pattern_autoclosed. Said line is non-existent.")
            else:
                line = _get_next_line(file)
    
    logging.info(f"{len(result)} autoclosed branches found")
    return result

def _get_dry_run_info(repository_name : str, branch_name: str, dry_run_infos : list[tuple[str | None, str | None, str | None]]):
    """
    Gets the "DRY-RUN" entries for a specific repository and branch from a given list of tuples.

    Parameters:
        repository_name (str): Name of the repository.
        branch_name (str): Name of the branch.
        dry_run_infos (list[tuple[str | None, str | None, str | None]]): List of "DRY-RUN" information tuples.

    Returns:
        list[str]: A list of "DRY-RUN" information strings for the specified repository and branch.
    """
    result : list[str] = list()

    for repository, branch, info in dry_run_infos:
        if repository == repository_name and branch == branch_name and info is not None:
            result.append(info)

    return result
    
def _done_state_drilldown(config: Config, dry_run_info : list[str]):
    """
    Determines the exact PR state for branches with the "done" state.

    Parameters:
        config (Config): Configuration object containing regex patterns.
        dry_run_info (list[str]): List of dry-run information strings.

    Returns:
        tuple[str, str]: PR state and additional information.
    """
    if len(dry_run_info) == 0:
        return UNCHANGED_PR, ""
    elif any(re.match(config.updated_branch_pattern, info) for info in dry_run_info):
        return UPDATED_PR, ""
    elif any(re.match(config.created_branch_pattern, info) for info in dry_run_info):
        return NEW_PR, ""
    elif any(re.match(config.commited_files_pattern, info) for info in dry_run_info): #this means the PR was rebased but not changed
        return UNCHANGED_PR, ""
    else:
        return UNKNOWN_PR, "<br>".join(dry_run_info)

def _no_work_state_drilldown(config: Config, dry_run_info : list[str]):
    """
    Determines the exact PR state for branches with the "no-work" state.

    Parameters:
        config (Config): Configuration object containing regex patterns.
        dry_run_info (list[str]): List of dry-run information strings.

    Returns:
        tuple[str, str]: PR state and additional information.
    """
    if len(dry_run_info) == 0:
        return UNCHANGED_PR, ""
    else:
        if any(re.match(config.commited_files_pattern, info) for info in dry_run_info):
            return NEW_PR, ""
        else:
            return UNKNOWN_PR, "<br>".join(dry_run_info)

def _determine_pr_status(pr_result : str, repository_name : str, branch_name: str, config: Config, dry_run_infos : list[tuple[str | None, str | None, str | None]]):
    """
    Determines the exact PR status based on the PR-result value and dry-run information.

    Parameters:
        pr_result (str): Result value of the PR being processed.
        repository_name (str): Name of the repository.
        branch_name (str): Name of the branch.
        config (Config): Configuration object containing regex patterns.
        dry_run_infos (list[tuple[str | None, str | None, str | None]]): List of dry-run information tuples.

    Returns:
        tuple[str, str]: PR state and additional information.
    """
    dry_run_info = _get_dry_run_info(repository_name, branch_name, dry_run_infos)
    match pr_result:
        case "discarded":
            return DISCARDED_PR, "PR would be discarded"
        case "already-existed":
            return SKIPPED_PR, "There is a closed PR for this dependency update so Renovate skipped the recreation of the PR"
        case "not-scheduled":
            return SKIPPED_PR, "PR is not scheduled for this repository"
        case "update-not-scheduled":
            return SKIPPED_PR, "PR is not scheduled for this repository"
        case "pr-limit-reached":
            return SKIPPED_PR, "PR limit reached for this repository"
        case "commit-limit-reached":
            return SKIPPED_PR, "Commit limit reached for this repository"
        case "branch-limit-reached":
            return SKIPPED_PR, "Branch limit reached for this repository"
        case "pr-edited":
            return SKIPPED_PR, "PR has been manually edited so Renovate skipped any processing in order to not override any manual changes"
        case "error":
            return ERROR_PR, "<br>".join(dry_run_info)
        case "pending":
            return PENDING_PR, "<br>".join(dry_run_info)
        case "needs-pr-approval":
            return PENDING_PR, "<br>".join(dry_run_info)
        case "needs-approval":
            return PENDING_PR, "<br>".join(dry_run_info)
        case "no-work":
            return _no_work_state_drilldown(config, dry_run_info)
        case "done":
            return _done_state_drilldown(config, dry_run_info)
        case "pr-created":
            return NEW_PR, ""
        case "rebase":
            return UNCHANGED_PR, "PR would be rebased"
        case "automerged":
            return AUTOMERGED_PR, "PR would be automerged"
        case _:
            return UNKNOWN_PR, "Unknown PR state<br>" + "<br>".join(dry_run_info)


def execute(log_file_path : str, output_file_path : str, config_file_path : str):
    """
    Executes the script to generate an HTML report from the log file.

    Parameters:
        log_file_path (str): Path to the log file.
        output_file_path (str): Path where the HTML report should be saved.
        config_file_path (str): Path to the configuration file.

    Returns:
        None
    """
    logging.basicConfig(level=logging.INFO)
    logging.info("Reading configuration file...")
    config = _read_config_file(config_file_path)
    logging.info("Configuration file sucessfully read")
    logging.info("Getting general dry run log entries...")
    dry_run_infos = _extract_general_dry_run_infos(log_file_path, config)
    logging.info("General Dry run log entries successfully retrieved")
    logging.info("Getting list of autoclosed PRs...")
    autoclosed_branches  = _extract_and_process_autoclosed_dry_run_infos(log_file_path, config)
    logging.info("List of autoclosed PRs successfully retrieved")
    logging.info("Getting list of branches from log file...")
    branches_lists = _find_branches_lists(log_file_path, config)
    logging.info("List of branches successfully retrieved")
    logging.info("Processing branches...")
    serialized_branches_lists = _process_branches_lists(branches_lists, autoclosed_branches, config.timestamp_pattern)
    logging.info("Branches successfully processed")
    logging.info("Generating HTML report...")
    HTMLReportGenerator(serialized_branches_lists, dry_run_infos, config, output_file_path)._generate()
    logging.info(f"HTML report successfully generated at {output_file_path}")

def _main():
    args = _parse_arguments()
    execute(args.log, args.out, args.config)

if __name__ == "__main__":
    try:
        _main()
    except Exception as e:
        print(e, file=sys.stderr)
