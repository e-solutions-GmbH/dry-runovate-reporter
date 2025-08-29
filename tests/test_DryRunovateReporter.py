import unittest
import json
from unittest.mock import patch, mock_open
from DryRunovateReporter import (
    Config,
    LogFileParsingError,
    _read_config_file, # type: ignore
    _find_branches_lists, # type: ignore
    _process_branches_lists, # type: ignore
    _determine_pr_status, # type: ignore
    _done_state_drilldown, # type: ignore
    _no_work_state_drilldown, # type: ignore
    _extract_general_dry_run_infos, # type: ignore
    _extract_and_process_autoclosed_dry_run_infos, #type: ignore
    UNCHANGED_PR,
    UPDATED_PR,
    NEW_PR,
    SKIPPED_PR,
    PENDING_PR,
    UNKNOWN_PR,
)

class TestReadConfigFile(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"branches_info_start_pattern": "start", "branches_info_end_pattern": "end", "repository_name_pattern": "repo", "timestamp_base_pattern": "123", "timestamp_base_pattern_placeholder": "PLACEHOLDER", "timestamp_pattern": "timestamp", "dry_run_info_pattern_general": "dry_run", "dry_run_info_pattern_autoclosed": "autoclosed", "dry_run_info_autoclosed_pr_title_line_number": 2, "dry_run_info_autoclosed_pr_title_pattern": "autoclosed_prTitle", "updated_branch_pattern": "updated", "created_branch_pattern": "created", "commited_files_pattern": "committed"}')
    def test_read_config_file(self, mock_file): # type: ignore
        config = _read_config_file("config.json")
        self.assertEqual(config.branches_info_start_pattern, "start")
        self.assertEqual(config.branches_info_end_pattern, "end")
        self.assertEqual(config.repository_name_pattern, "repo")
        self.assertEqual(config.timestamp_pattern, "timestamp")
        self.assertEqual(config.dry_run_info_pattern_general, "dry_run")
        self.assertEqual(config.dry_run_info_pattern_autoclosed, "autoclosed")
        self.assertEqual(config.dry_run_info_autoclosed_pr_title_line_number, 2)
        self.assertEqual(config.dry_run_info_autoclosed_pr_title_pattern, "autoclosed_prTitle")
        self.assertEqual(config.updated_branch_pattern, "updated")
        self.assertEqual(config.created_branch_pattern, "created")
        self.assertEqual(config.commited_files_pattern, "committed")

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_read_config_file_invalid_json(self, mock_file): # type: ignore
        with self.assertRaises(json.JSONDecodeError):
            _read_config_file("config.json")


class TestFindBranchesLists(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="start_pattern(repo: test_repo)\nbranch info\nend_pattern\n")
    @patch("DryRunovateReporter._extract_repository_name")
    def test_find_branches_lists_happy_path(self, mock_extract_repository_name, mock_file): # type: ignore

        mock_extract_repository_name.return_value = "test_repo"

        config = Config(
            branches_info_start_pattern="start_pattern",
            branches_info_end_pattern="end_pattern",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed = "",
            dry_run_info_autoclosed_pr_title_line_number = 2,
            dry_run_info_autoclosed_pr_title_pattern = "",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )
        result = _find_branches_lists("log.txt", config)

        mock_extract_repository_name.assert_called_once_with("start_pattern(repo: test_repo)", "") #type: ignore
        self.assertIn("test_repo", result)
        self.assertEqual(result["test_repo"], ["branch info"])

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_find_branches_lists_empty_log(self, mock_file): # type: ignore

        config = Config(
            branches_info_start_pattern="start_pattern",
            branches_info_end_pattern="end_pattern",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed = "",
            dry_run_info_autoclosed_pr_title_line_number = 2,
            dry_run_info_autoclosed_pr_title_pattern = "",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )

        with self.assertRaises(LogFileParsingError) as error:
            _find_branches_lists("log.txt", config)

        self.assertEqual(error.exception.message, "Log file is empty.")

    @patch("builtins.open", new_callable=mock_open, read_data="start_pattern(repo: test_repo)\nbranch info\n")
    @patch("DryRunovateReporter._extract_repository_name")
    def test_find_branches_lists_bad_log(self, mock_extract_repository_name, mock_file): # type: ignore

        mock_extract_repository_name.return_value = "test_repo"

        config = Config(
            branches_info_start_pattern="start_pattern",
            branches_info_end_pattern="end_pattern",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed = "",
            dry_run_info_autoclosed_pr_title_line_number = 2,
            dry_run_info_autoclosed_pr_title_pattern = "",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )

        with self.assertRaises(LogFileParsingError) as error:
            _ = _find_branches_lists("log.txt", config)


        mock_extract_repository_name.assert_called_once_with("start_pattern(repo: test_repo)", "") #type: ignore
        self.assertEqual(error.exception.message, "Start of the relevant section for repository test_repo was found but no end was found.")

    

class TestProcessBranchesLists(unittest.TestCase):
    def test_process_branches_lists(self):
        relevant_sections = {"test_repo": ["[2025-06-24T10:41:40.220Z] \"someEntry\": 1,", "[2025-06-24T10:41:40.220Z] \"anotherEntry\": 2"]}
        autoclosed_branches : list[tuple[str | None, str | None]] = [("test_repo2", "test_prTitle")]
        result = _process_branches_lists(relevant_sections, autoclosed_branches,"^\\[\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z\\]\\s*")
        self.assertEqual(result["items"][0]["repository"], "test_repo")
        self.assertEqual(result["items"][0]["someEntry"], 1)
        self.assertEqual(result["items"][0]["anotherEntry"], 2)
        self.assertEqual(result["items"][1]["repository"], "test_repo2")
        self.assertEqual(result["items"][1]["branchesInformation"][0], {"prTitle": "test_prTitle", "result": "discarded"})

class TestExtractDryRunInfos(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="dry_run_pattern repo: test_repo branch: test_branch info: test_info\n")
    def test_extract_general_dry_run_infos(self, mock_file): # type: ignore
        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general=r"dry_run_pattern repo: (?P<repository_name>\w+) branch: (?P<branch_name>\w+) info: (?P<info>.+)",
            dry_run_info_pattern_autoclosed="",
            dry_run_info_autoclosed_pr_title_line_number=0,
            dry_run_info_autoclosed_pr_title_pattern="",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )
        result = _extract_general_dry_run_infos("log.txt", config)
        self.assertEqual(result, [("test_repo", "test_branch", "test_info")])

class TestDeterminePRStatus(unittest.TestCase):
    @patch("DryRunovateReporter._done_state_drilldown")
    def test_determine_pr_status(self, mock_done_state_drilldown): # type: ignore

        mock_done_state_drilldown.return_value = (UPDATED_PR, "")

        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed="",
            dry_run_info_autoclosed_pr_title_line_number=0,
            dry_run_info_autoclosed_pr_title_pattern="",
            updated_branch_pattern="updated",
            created_branch_pattern="created",
            commited_files_pattern="committed",
        )

        dry_run_infos : list[tuple[str | None, str | None, str | None]] = [("test_repo", "test_branch", "updated"), ("test_repo", "test_branch", "someOtherInfo")]
        result = _determine_pr_status("done", "test_repo", "test_branch", config, dry_run_infos)

        mock_done_state_drilldown.assert_called_once_with(config, ["updated", "someOtherInfo"]) # type: ignore
        self.assertEqual(result, (UPDATED_PR, ""))

        result = _determine_pr_status("already-existed", "test_repo", "test_branch", config, dry_run_infos)
        self.assertEqual(result, (SKIPPED_PR, "There is a closed PR for this dependency update so Renovate skipped the recreation of the PR"))

        result = _determine_pr_status("pending", "test_repo", "test_branch", config, dry_run_infos)
        self.assertEqual(result, (PENDING_PR, "updated<br>someOtherInfo"))

        result = _determine_pr_status("someWeirdStatus", "test_repo", "test_branch", config, dry_run_infos)
        self.assertEqual(result, (UNKNOWN_PR, "Unknown PR state<br>updated<br>someOtherInfo"))

class TestDrillDowns(unittest.TestCase):
    def test_done_state_drilldown(self):

        dry_run_infos = ["updated"]
        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed="",
            dry_run_info_autoclosed_pr_title_line_number=0,
            dry_run_info_autoclosed_pr_title_pattern="",
            updated_branch_pattern="updated",
            created_branch_pattern="created",
            commited_files_pattern="committed",
        )

        result = _done_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (UPDATED_PR, ""))

        dry_run_infos.clear()
        dry_run_infos.append("created")

        result = _done_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (NEW_PR, ""))

        dry_run_infos.clear()
        dry_run_infos.append("committed")

        result = _done_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (UNCHANGED_PR, ""))

        dry_run_infos.clear()

        result = _done_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (UNCHANGED_PR, ""))

    def test_no_work_state_drilldown(self):
        dry_run_infos = ["committed"]
        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed="",
            dry_run_info_autoclosed_pr_title_line_number=0,
            dry_run_info_autoclosed_pr_title_pattern="",
            updated_branch_pattern="updated",
            created_branch_pattern="created",
            commited_files_pattern="committed",
        )

        result = _no_work_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (NEW_PR, ""))

        dry_run_infos.clear()
        dry_run_infos.append("someInfo")
        dry_run_infos.append("otherInfo")

        result = _no_work_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (UNKNOWN_PR, "someInfo<br>otherInfo"))

        dry_run_infos.clear()

        result = _no_work_state_drilldown(config, dry_run_infos)
        self.assertEqual(result, (UNCHANGED_PR, ""))

class TestExtractAndProcessAutoclosedInfos(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="\"repo\": \"someRepoName\"\nsomeLine\n\"prTitle\": \"somePrTitle\"")
    def test_extract_and_process_autoclosed_dry_run_infos_happy_path(self, mock_file): #type: ignore

        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed="\"repo\":\\s*\"(?P<repository_name>.+?)\"$",
            dry_run_info_autoclosed_pr_title_line_number=2,
            dry_run_info_autoclosed_pr_title_pattern="\"prTitle\":\\s*\"(?P<pr_title>.+?)\"$",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )

        result = _extract_and_process_autoclosed_dry_run_infos("log.txt", config)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ("someRepoName", "somePrTitle"))

    @patch("builtins.open", new_callable=mock_open, read_data="\"repo\": \"someRepoName\"\nsomeLine\n\"prTitle\": \"somePrTitle\"")
    def test_extract_and_process_autoclosed_dry_run_infos_bad_line_number(self, mock_file): #type: ignore

        config = Config(
            branches_info_start_pattern="",
            branches_info_end_pattern="",
            repository_name_pattern="",
            timestamp_base_pattern="",
            timestamp_base_pattern_placeholder="",
            timestamp_pattern="",
            dry_run_info_pattern_general="",
            dry_run_info_pattern_autoclosed="\"repo\":\\s*\"(?P<repository_name>.+?)\"$",
            dry_run_info_autoclosed_pr_title_line_number=1,
            dry_run_info_autoclosed_pr_title_pattern="\"prTitle\":\\s*\"(?P<pr_title>.+?)\"$",
            updated_branch_pattern="",
            created_branch_pattern="",
            commited_files_pattern="",
        )

        with self.assertRaises(LogFileParsingError) as error:
            _extract_and_process_autoclosed_dry_run_infos("log.txt", config)

        self.assertEqual(error.exception.message, f"pr title was not found {config.dry_run_info_autoclosed_pr_title_line_number} lines below the log entry matched by config.dry_run_info_pattern_autoclosed. Instead the following line was found: someLine")


        config.dry_run_info_autoclosed_pr_title_line_number = 3
        with self.assertRaises(LogFileParsingError) as error:
            _extract_and_process_autoclosed_dry_run_infos("log.txt", config)

        self.assertEqual(error.exception.message, f"pr title was not found {config.dry_run_info_autoclosed_pr_title_line_number} lines below the log entry matched by config.dry_run_info_pattern_autoclosed. Said line is non-existent.")





if __name__ == "__main__":
    unittest.main()