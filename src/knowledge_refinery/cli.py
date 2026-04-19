import argparse
from argparse import SUPPRESS
from argparse import Action
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import Any
from typing import cast

from knowledge_refinery import get_version
from knowledge_refinery.agents_ops import GUIDE_FILENAME_CHOICES
from knowledge_refinery.agents_ops import LANG_CHOICES
from knowledge_refinery.agents_ops import apply_agents_md
from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.knowledge_ops import prepare_review
from knowledge_refinery.knowledge_ops import promote_review
from knowledge_refinery.knowledge_ops import refresh_review
from knowledge_refinery.knowledge_ops import reject_review
from knowledge_refinery.search_ops import search_knowledge
from knowledge_refinery.search_ops import search_review
from knowledge_refinery.search_ops import search_sessions
from knowledge_refinery.session_metadata import init_session
from knowledge_refinery.session_metadata import read_yaml_mapping
from knowledge_refinery.session_metadata import update_session
from knowledge_refinery.template_ops import SKILL_DESTINATION_CHOICES
from knowledge_refinery.template_ops import TEMPLATE_METADATA_RELATIVE_PATH
from knowledge_refinery.template_ops import apply_template


special_actions = (
    argparse._SubParsersAction,
    argparse._HelpAction,
    argparse._VersionAction,
)
flag_actions = (
    argparse._StoreConstAction,
    argparse._StoreTrueAction,
    argparse._StoreFalseAction,
)


class _ZshCompletionAction(Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str = SUPPRESS,
        default: str = SUPPRESS,
        help: str | None = None,
        deprecated: bool = False,
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        cast("ZshCompletionArgParser", parser).print_completion_script()
        parser.exit()


class _ZshCompletionArgumentGroup(argparse._ArgumentGroup):
    def add_argument(self, *args: Any, **kwargs: Any) -> argparse.Action:
        completion = kwargs.pop("completion", None)
        action = super().add_argument(*args, **kwargs)
        if completion is not None:
            action._completion = completion  # type: ignore[attr-defined] # zsh completion hint
        return action


class ZshCompletionArgParser(argparse.ArgumentParser):
    def __init__(
        self,
        *args: Any,
        func_name: str | None = None,
        completion_cmd: str = "zsh",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        # Ensure argument groups can accept completion metadata too.
        self._argument_group_class = _ZshCompletionArgumentGroup

        self.register("action", "zsh", _ZshCompletionAction)

        if func_name is None:
            self.func_name = self.prog
        else:
            self.func_name = func_name
        self.func_name = self.func_name.replace("-", "_").replace(" ", "_").replace(".", "_")

        if completion_cmd:
            self.add_argument(
                f"--{completion_cmd}",
                action="zsh",
                help="print zsh completion scripts of this argparser.",
            )

    def add_argument_group(self, *args: Any, **kwargs: Any) -> _ZshCompletionArgumentGroup:
        """Ensure groups also support completion metadata."""
        group = _ZshCompletionArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_argument(self, *args: Any, **kwargs: Any) -> argparse.Action:
        """Add an argument and optionally attach zsh completion metadata.

        Parameters
        ----------
        completion : {"file", "dir"} | None, optional (kw-only)
            zsh補完のために明示的な種別を指定する。

            - ``"file"``: ファイルパス補完。zsh側では ``_files`` を使用する。
            - ``"dir"``: ディレクトリ補完。zsh側では ``_path_files -/`` を使用する。

        Notes
        -----
        - ``completion`` が指定された場合、対応する補完関数を
          ``argparse.Action`` にメタデータとして保持する。
        - ``completion`` が指定されない場合でも、以下のヒューリスティックにより
          パス補完を推定する:
          - option/positional 名や help, metavar, dest に
            ``path``, ``file``, ``dir``, ``directory``, ``folder``,
            ``save``, ``output``, ``config`` が含まれる場合は ``file`` 補完
          - ``dir`` / ``directory`` / ``folder`` / ``save_dir`` などが
            明示されている場合は ``dir`` 補完を優先
        - ``choices`` が定義されている場合は、``choices`` による補完を優先し、
          ``completion`` の指定は無視する。
        - ``store_true`` など値を取らないフラグには補完は付与しない。
        """
        completion = kwargs.pop("completion", None)
        action = super().add_argument(*args, **kwargs)
        if completion is not None:
            action._completion = completion  # type: ignore[attr-defined] # zsh completion hint
        return action

    @property
    def has_subcmds(self) -> bool:
        return self.check_in_action(argparse._SubParsersAction)

    @property
    def has_help(self) -> bool:
        return self.check_in_action(argparse._HelpAction)

    @property
    def has_version(self) -> bool:
        return self.check_in_action(argparse._VersionAction)

    def check_in_action(self, target: type[argparse.Action]) -> bool:
        return any(isinstance(action, target) for action in self._actions)

    def print_completion_script(self) -> None:
        print(self.build_completion_script())

    def build_completion_script(self) -> str:
        """
        make zsh completion scripts
        """

        # In .py script

        script_header = f"#compdef {self.prog}\n"
        script_footer = f"compdef _{self.func_name} {self.prog}"

        script_main = self.generate_completion_function()

        return script_header + script_main + script_footer

    def make_function_header(self) -> str:
        """
        When this parser has sub command, define subcmds array as local variable.
        """

        if self.has_subcmds:
            # parser cannot have any _subParsersAction
            subcmd_action = self._find_subparsers_action()
            if subcmd_action is None:
                return "\n"

            subcmds = []
            for _pseudo_action in subcmd_action._choices_actions:
                dest = _pseudo_action.dest
                if _pseudo_action.help is not None:
                    prefix = "$"
                    help = _pseudo_action.help.replace("'", "\\'")
                else:
                    prefix = ""
                    help = ""

                subcmds.append(f"    {prefix}'{dest}[{help}]'")
            function_headers = [
                "local -a subcmds",
                "subcmds=(",
                "\n".join(subcmds),
                ")",
            ]

            return "\n".join(function_headers) + "\n"
        else:
            return "\n"

    def _find_subparsers_action(self) -> argparse._SubParsersAction | None:
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                return action
        return None

    def generate_completion_function(self, cmd_index: int = 1) -> str:  # noqa: C901
        """
        zshの補完用スクリプトを作成する

        """
        function_header = self.make_function_header()

        arguments = []
        if self.has_help:
            arguments.append("  '(- *)'{-h,--help} \\")
        if self.has_version:
            arguments.append("  '--version' \\")

        if self.has_subcmds:
            arguments.append("  '1: :->subcmds' \\")
            arguments.append("  '*:: :->args'")

            case_statement = "case $state in\n"
            case_statement += "  subcmds)\n"
            case_statement += "    _values 'subcommand' $subcmds\n"
            case_statement += "    ;;\n"
            case_statement += "  args)\n"
            case_statement += f'    local cur_cmd="_{self.func_name}_$words[{cmd_index}]"\n'
            case_statement += "    if (( $+functions[$cur_cmd] )); then\n"
            case_statement += "      $cur_cmd\n"
            case_statement += "    fi\n"
            case_statement += "    ;;\n"
            case_statement += "esac"
        else:
            case_statement = ""

            # postitional argumentsがある場合とない場合で処理が変わる
            cnt_positional_args = cmd_index
            positional_args = []
            for action in sorted(
                self._actions,
                key=lambda _act: 1 if _act.option_strings else 0,  # 位置引数から触る
            ):
                if isinstance(action, special_actions):
                    continue
                if action.help:
                    prefix = "$" if "'" in action.help else ""
                    help_text = action.help.replace("'", "\\'")
                else:
                    prefix = ""
                    help_text = ""

                completion_func = self._resolve_completion_function(action)

                if action.option_strings:
                    choice_sep = " "
                    if len(action.option_strings) == 1:
                        arg_value = f"  {prefix}'{action.option_strings[0]}[{help_text}]"
                    else:
                        option_strings_join_space = " ".join(action.option_strings)
                        option_strings_join_comma = ",".join(action.option_strings)
                        arg_value = (
                            f"  '({option_strings_join_space})'"
                            + ("{" + option_strings_join_comma + "}")
                            + f"{prefix}'[{help_text}]"
                        )
                    if isinstance(action, flag_actions):
                        pass
                    else:
                        if completion_func:
                            arg_value += f": :{completion_func}"
                        else:
                            arg_value += ": :"

                else:
                    choice_sep = " "
                    if completion_func:
                        arg_value = (
                            f"  {prefix}'{cnt_positional_args}:{help_text}:{completion_func}"
                        )
                    else:
                        arg_value = f"  {prefix}'{cnt_positional_args}:{help_text}:"
                    cnt_positional_args += 1

                if action.choices is not None:
                    arg_value = arg_value + f"({choice_sep.join(map(str, action.choices))})"
                else:
                    arg_value += ""

                if action.option_strings:
                    arguments.append(arg_value + "' \\")
                else:
                    positional_args.append(arg_value + "' \\")

            # 位置引数は(- *)のまえ
            arguments = positional_args + arguments

        scripts = function_header
        scripts += "_arguments \\\n" + "\n".join(arguments) + "\n\n"
        scripts += case_statement
        scripts = f"_{self.func_name}() " + "{\n" + scripts

        scripts = scripts.replace("\n", "\n" + "  ") + "\n}\n"

        if self.has_subcmds:
            subcmd_action = self._find_subparsers_action()
            if subcmd_action is None:
                return scripts
            for _, _parser in subcmd_action.choices.items():
                if isinstance(_parser, ZshCompletionArgParser):
                    scripts += _parser.generate_completion_function(cmd_index=cmd_index)

        return scripts

    def _resolve_completion_function(self, action: argparse.Action) -> str | None:
        """Return zsh completion function name for this action, if any."""
        if self._should_skip_completion(action):
            return None

        explicit = self._resolve_explicit_completion(action)
        if explicit is not None:
            return explicit

        return self._resolve_heuristic_completion(action)

    def _should_skip_completion(self, action: argparse.Action) -> bool:
        if isinstance(action, flag_actions) or isinstance(action, special_actions):
            return True
        return action.choices is not None

    def _resolve_explicit_completion(self, action: argparse.Action) -> str | None:
        explicit = getattr(action, "_completion", None)
        if explicit is None:
            return None
        mapping = {
            "file": "_files",
            "dir": "_path_files -/",
        }
        return mapping.get(str(explicit))

    def _resolve_heuristic_completion(self, action: argparse.Action) -> str | None:
        keywords: list[str] = []
        keywords.extend(action.option_strings)
        if action.dest:
            keywords.append(action.dest)
        if action.metavar:
            keywords.append(str(action.metavar))
        if action.help:
            keywords.append(action.help)

        haystack = " ".join(keywords).lower()
        dir_tokens = ("dir", "directory", "folder", "save_dir", "savedir")
        if any(token in haystack for token in dir_tokens):
            return "_path_files -/"
        file_tokens = ("path", "file", "save", "output", "config")
        if any(token in haystack for token in file_tokens):
            return "_files"
        return None


def build_parser() -> ZshCompletionArgParser:
    parser = ZshCompletionArgParser(
        prog="knowledge-refinery", description="Knowledge refinery CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser(
        "apply-template", help="Copy the refinery template into a target repository"
    )
    apply_parser.add_argument("--target", default=".", help="target repository path")
    apply_parser.add_argument("--force", action="store_true", help="overwrite existing files")
    apply_parser.add_argument(
        "--skill-destination",
        choices=SKILL_DESTINATION_CHOICES,
        default="codex",
        help="directory for distributed skills: .codex or .agent",
    )
    apply_parser.set_defaults(handler=run_apply_template)

    update_template_parser = subparsers.add_parser(
        "update-template",
        help="Refresh distributed refinery skills and shared files in a target repository",
    )
    update_template_parser.add_argument("--target", default=".", help="target repository path")
    update_template_parser.add_argument(
        "--skill-destination",
        choices=SKILL_DESTINATION_CHOICES,
        default="codex",
        help="directory for distributed skills: .codex or .agent",
    )
    update_template_parser.set_defaults(handler=run_update_template)

    agents_parser = subparsers.add_parser(
        "update-agents-md",
        help="Append or update the managed refinery section in a target AGENTS.md or CLAUDE.md",
    )
    agents_parser.add_argument(
        "--target", default=".", help="target repository path, AGENTS.md path, or CLAUDE.md path"
    )
    agents_parser.add_argument(
        "--lang", choices=LANG_CHOICES, default="jp", help="snippet language"
    )
    agents_parser.add_argument(
        "--filename",
        choices=GUIDE_FILENAME_CHOICES,
        default="AGENTS.md",
        help="guide file to create when --target is a directory",
    )
    agents_parser.set_defaults(handler=run_apply_agents_md)

    skills_parser = subparsers.add_parser(
        "skills", help="Run refinery runtime commands used by distributed skills"
    )
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    add_runtime_subcommands(skills_subparsers)

    return parser


def add_runtime_subcommands(subparsers: argparse._SubParsersAction) -> None:
    init_parser = subparsers.add_parser(
        "init-session",
        help="Initialize a refinery session",
    )
    init_parser.add_argument("--task", required=True, help="Task summary")
    init_parser.add_argument("--kind", default="task", help="Session kind (default: task)")
    init_parser.add_argument(
        "--title", default=None, help="Session title (default: same as --task)"
    )
    init_parser.add_argument(
        "--created-by",
        default="user",
        choices=["user", "llm"],
        help="Session creator (default: user)",
    )
    init_parser.add_argument("--repository", default=None, help="Repository name")
    init_parser.add_argument("--domain", default=None, help="Session domain")
    init_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    init_parser.set_defaults(handler=run_init_session)

    update_session_parser = subparsers.add_parser(
        "update-session",
        help="Update selected fields in a refinery session meta.yaml",
    )
    update_session_parser.add_argument("--session-id", required=True, help="Session ID to update")
    update_session_parser.add_argument("--title", default=None, help="Session title")
    update_session_parser.add_argument("--task", default=None, help="Task summary")
    update_session_parser.add_argument("--status", default=None, help="Session status")
    update_session_parser.add_argument("--phase", default=None, help="Session phase")
    update_session_parser.add_argument("--current-step", default=None, help="Current step")
    update_session_parser.add_argument("--next-action", default=None, help="Next action")
    update_session_parser.add_argument("--blocked-reason", default=None, help="Blocked reason")
    update_session_parser.add_argument("--resume-condition", default=None, help="Resume condition")
    update_session_parser.add_argument("--domain", default=None, help="Session domain")
    update_session_parser.add_argument("--repository", default=None, help="Repository name")
    update_session_parser.add_argument(
        "--evidence-status", default=None, help="Evidence collection status"
    )
    update_session_parser.add_argument("--flow-status", default=None, help="Flow status")
    update_session_parser.add_argument("--synthesis-status", default=None, help="Synthesis status")
    update_session_parser.add_argument("--coverage-status", default=None, help="Coverage status")
    update_session_parser.add_argument("--confidence", default=None, help="Confidence level")
    update_session_parser.add_argument(
        "--clear-blocked-reason", action="store_true", help="Clear blocked_reason"
    )
    update_session_parser.add_argument(
        "--clear-resume-condition", action="store_true", help="Clear resume_condition"
    )
    update_session_parser.add_argument("--clear-domain", action="store_true", help="Clear domain")
    update_session_parser.add_argument(
        "--clear-repository", action="store_true", help="Clear repository"
    )
    update_session_parser.add_argument(
        "--root", default=".refinery", help="Refinery root directory"
    )
    update_session_parser.set_defaults(handler=run_update_session)

    search_parser = subparsers.add_parser(
        "search",
        help="Search refinery knowledge, review, or session metadata",
    )
    search_subparsers = search_parser.add_subparsers(dest="search_command", required=True)

    search_knowledge_parser = search_subparsers.add_parser(
        "knowledge", help="Search refinery knowledge files"
    )
    search_knowledge_parser.add_argument(
        "terms", nargs="*", default=[], help="search terms combined with AND matching"
    )
    search_knowledge_parser.add_argument(
        "--root", default=".refinery", help="Refinery root directory"
    )
    search_knowledge_parser.add_argument(
        "--scope",
        action="append",
        choices=["raw", "flow", "review", "stock"],
        default=[],
        help="limit search to a layer; may be specified multiple times",
    )
    search_knowledge_parser.add_argument(
        "--session-id",
        action="append",
        default=[],
        help=(
            "session ID filter; path-based for raw/flow and source_sessions-based for review/stock"
        ),
    )
    search_knowledge_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="require a tag exact match; may be specified multiple times",
    )
    search_knowledge_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id exact match; may be specified multiple times",
    )
    search_knowledge_parser.add_argument(
        "--include-rejected", action="store_true", help="include rejected review files"
    )
    search_knowledge_parser.set_defaults(handler=run_search_knowledge)

    search_review_parser = search_subparsers.add_parser(
        "review", help="Search review knowledge files in shared/review"
    )
    search_review_parser.add_argument(
        "terms", nargs="*", default=[], help="search terms combined with AND matching"
    )
    search_review_parser.add_argument(
        "--root", default=".refinery", help="Refinery root directory"
    )
    search_review_parser.add_argument(
        "--session-id",
        action="append",
        default=[],
        help="source session ID filter; may be specified multiple times",
    )
    search_review_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="require a tag exact match; may be specified multiple times",
    )
    search_review_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id exact match; may be specified multiple times",
    )
    search_review_parser.add_argument(
        "--include-rejected", action="store_true", help="include rejected review files"
    )
    search_review_parser.set_defaults(handler=run_search_review)

    search_sessions_parser = search_subparsers.add_parser(
        "sessions", help="Search refinery session metadata and state"
    )
    search_sessions_parser.add_argument(
        "terms", nargs="*", default=[], help="search terms combined with AND matching"
    )
    search_sessions_parser.add_argument(
        "--root", default=".refinery", help="Refinery root directory"
    )
    search_sessions_parser.add_argument(
        "--session-id",
        action="append",
        default=[],
        help="session ID exact match; may be specified multiple times",
    )
    search_sessions_parser.add_argument(
        "--status",
        action="append",
        default=[],
        help="session status exact match; may be specified multiple times",
    )
    search_sessions_parser.add_argument(
        "--phase",
        action="append",
        default=[],
        help="session phase exact match; may be specified multiple times",
    )
    search_sessions_parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="session domain exact match; may be specified multiple times",
    )
    search_sessions_parser.set_defaults(handler=run_search_sessions)

    review_parser = subparsers.add_parser(
        "prepare-review", help="Copy flow knowledge files into shared/review"
    )
    review_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    review_parser.add_argument(
        "--session-id", default=None, help="Session ID to process (default: all sessions)"
    )
    review_parser.add_argument(
        "--force", action="store_true", help="overwrite existing review files"
    )
    review_parser.set_defaults(handler=run_prepare_review)

    promote_parser = subparsers.add_parser(
        "promote-review", help="Copy review knowledge files into shared/stock"
    )
    promote_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    promote_parser.add_argument("--all", action="store_true", help="promote all review files")
    promote_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to promote; may be specified multiple times",
    )
    promote_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to promote; may be specified multiple times",
    )
    promote_parser.add_argument(
        "--force", action="store_true", help="overwrite existing stock files"
    )
    promote_parser.set_defaults(handler=run_promote_review)

    refresh_parser = subparsers.add_parser(
        "refresh-review", help="Refresh review files from their flow sources"
    )
    refresh_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    refresh_parser.add_argument("--all", action="store_true", help="refresh all review files")
    refresh_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to refresh; may be specified multiple times",
    )
    refresh_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to refresh; may be specified multiple times",
    )
    refresh_parser.set_defaults(handler=run_refresh_review)

    reject_parser = subparsers.add_parser(
        "reject-review", help="Move review files out of the active review queue"
    )
    reject_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    reject_parser.add_argument("--all", action="store_true", help="reject all review files")
    reject_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to reject; may be specified multiple times",
    )
    reject_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to reject; may be specified multiple times",
    )
    reject_parser.add_argument(
        "--force", action="store_true", help="overwrite existing rejected files"
    )
    reject_parser.set_defaults(handler=run_reject_review)


def run_apply_template(args: argparse.Namespace) -> int:
    target_root = Path(args.target).resolve()
    template_root, copied = apply_template(
        target_root,
        force=args.force,
        skill_destination=args.skill_destination,
    )

    print(f"Applied template from: {template_root}")
    print(f"Target repository: {target_root}")
    print(f"Skill destination: .{args.skill_destination}/skills")
    print(f"Copied files: {len(copied)}")
    print("\nNext steps:")
    print(
        "1) Install `knowledge-refinery` with `uv tool install ...` "
        "in the environment that will run the CLI."
    )
    print(
        "2) Update the managed AGENTS.md or CLAUDE.md section with "
        "`knowledge-refinery update-agents-md --target ... --lang jp|en`."
    )
    print(
        f"3) Confirm .{args.skill_destination}/skills/, .refinery/shared/, and "
        "`.refinery/template-meta.yaml` were copied."
    )
    print(
        "4) Later template updates can be applied with "
        "`knowledge-refinery update-template --target ...`."
    )
    print("5) Use `knowledge-refinery skills ...` for session, search, and review operations.")
    print("6) Use sessions/*/meta.yaml as the single session metadata format.")
    return 0


def run_update_template(args: argparse.Namespace) -> int:
    target_root = Path(args.target).resolve()
    template_root, copied = apply_template(
        target_root,
        force=True,
        skill_destination=args.skill_destination,
    )

    print(f"Updated template from: {template_root}")
    print(f"Target repository: {target_root}")
    print(f"Skill destination: .{args.skill_destination}/skills")
    print(f"Updated files: {len(copied)}")
    print("\nNext steps:")
    print(
        "1) Reinstall `knowledge-refinery` in the environment that runs "
        "the CLI if the package source was updated."
    )
    print(
        "2) Refresh the managed AGENTS.md or CLAUDE.md section with "
        "`knowledge-refinery update-agents-md --target ... --lang jp|en`."
    )
    print(
        f"3) Review the updated diffs under "
        f".{args.skill_destination}/skills/ and .refinery/shared/."
    )
    print(
        "4) `.refinery/template-meta.yaml` is refreshed to match the CLI version used "
        "for this update."
    )
    print("5) Existing .refinery/shared/state.md is preserved during template refreshes.")
    print("6) Use `knowledge-refinery skills ...` for session, search, and review operations.")
    print("7) Keep sessions/*/meta.yaml as the single session metadata format.")
    return 0


def run_apply_agents_md(args: argparse.Namespace) -> int:
    agents_path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
    print(agents_path.as_posix())
    return 0


def run_init_session(args: argparse.Namespace) -> int:
    session_root = init_session(
        Path(args.root),
        task=args.task,
        kind=args.kind,
        title=args.title or args.task,
        created_by=args.created_by,
        repository=args.repository,
        domain=args.domain,
    )
    print(session_root.as_posix())
    return 0


def run_update_session(args: argparse.Namespace) -> int:
    updates = {
        field: value
        for field, value in [
            ("title", args.title),
            ("task", args.task),
            ("status", args.status),
            ("phase", args.phase),
            ("current_step", args.current_step),
            ("next_action", args.next_action),
            ("blocked_reason", args.blocked_reason),
            ("resume_condition", args.resume_condition),
            ("domain", args.domain),
            ("repository", args.repository),
            ("evidence_status", args.evidence_status),
            ("flow_status", args.flow_status),
            ("synthesis_status", args.synthesis_status),
            ("coverage_status", args.coverage_status),
            ("confidence", args.confidence),
        ]
        if value is not None
    }
    clear_fields = [
        field
        for field, enabled in [
            ("blocked_reason", args.clear_blocked_reason),
            ("resume_condition", args.clear_resume_condition),
            ("domain", args.clear_domain),
            ("repository", args.clear_repository),
        ]
        if enabled
    ]
    path, meta = update_session(
        Path(args.root),
        session_id=args.session_id,
        updates=updates,
        clear_fields=clear_fields,
    )
    print(
        render_key_value_line(
            [
                ("path", path.parent.as_posix()),
                ("session_id", str(meta.get("session_id", ""))),
                ("title", str(meta.get("title", ""))),
                ("task", str(meta.get("task", ""))),
                ("status", str(meta.get("status", ""))),
                ("phase", str(meta.get("phase", ""))),
                ("flow_status", str(meta.get("flow_status", ""))),
                ("next_action", str(meta.get("next_action", ""))),
            ]
        )
    )
    return 0


def render_search_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def render_key_value_line(pairs: list[tuple[str, object]]) -> str:
    return " ".join(f"{key}={render_search_value(value)}" for key, value in pairs)


def run_search_sessions(args: argparse.Namespace) -> int:
    entries = search_sessions(
        Path(args.root),
        terms=list(args.terms),
        session_ids=list(args.session_id),
        statuses=list(args.status),
        phases=list(args.phase),
        domains=list(args.domain),
    )
    if not entries:
        print("No sessions found.")
        return 0

    for entry in entries:
        print(
            render_key_value_line(
                [
                    ("path", entry.path.as_posix()),
                    ("session_id", entry.session_id),
                    ("title", entry.title),
                    ("task", entry.task),
                    ("status", entry.status),
                    ("phase", entry.phase),
                    ("flow_status", entry.flow_status),
                    ("next_action", entry.next_action),
                ]
            )
        )
    return 0


def run_search_knowledge(args: argparse.Namespace) -> int:
    entries = search_knowledge(
        Path(args.root),
        terms=list(args.terms),
        scopes=list(args.scope),
        session_ids=list(args.session_id),
        tags=list(args.tag),
        knowledge_ids=list(args.knowledge_id),
        include_rejected=bool(args.include_rejected),
    )
    if not entries:
        print("No knowledge files found.")
        return 0

    for entry in entries:
        print(
            render_key_value_line(
                [
                    ("path", entry.path.as_posix()),
                    ("scope", entry.scope),
                    ("knowledge_id", entry.knowledge_id),
                    ("title", entry.title),
                    ("summary", entry.summary),
                    ("tags", entry.tags),
                    ("source_sessions", entry.source_sessions),
                ]
            )
        )
    return 0


def run_prepare_review(args: argparse.Namespace) -> int:
    results = prepare_review(Path(args.root), session_id=args.session_id, force=args.force)
    if not results:
        print("No flow knowledge files found.")
        return 0

    copied = 0
    skipped = 0
    for result in results:
        status = "copied" if result.copied else "skipped"
        rel_source = result.source.as_posix()
        rel_target = result.target.as_posix()
        print(f"{status}\t{rel_target}\tfrom={rel_source}")
        if result.copied:
            copied += 1
        else:
            skipped += 1

    print(f"Prepared review files: copied={copied} skipped={skipped}")
    return 0


def run_promote_review(args: argparse.Namespace) -> int:
    results = promote_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
        force=args.force,
    )

    copied = 0
    skipped = 0
    for result in results:
        status = "copied" if result.copied else "skipped"
        rel_source = result.source.as_posix()
        rel_target = result.target.as_posix()
        print(f"{status}\t{rel_target}\tfrom={rel_source}")
        if result.copied:
            copied += 1
        else:
            skipped += 1

    print(f"Promoted review files: copied={copied} skipped={skipped}")
    return 0


def run_search_review(args: argparse.Namespace) -> int:
    entries = search_review(
        Path(args.root),
        terms=list(args.terms),
        session_ids=list(args.session_id),
        tags=list(args.tag),
        knowledge_ids=list(args.knowledge_id),
        include_rejected=bool(args.include_rejected),
    )
    if not entries:
        print("No review files found.")
        return 0

    for entry in entries:
        print(
            render_key_value_line(
                [
                    ("path", entry.path.as_posix()),
                    ("knowledge_id", entry.knowledge_id),
                    ("title", entry.title),
                    ("summary", entry.summary),
                    ("tags", entry.tags),
                    ("source_sessions", entry.source_sessions),
                ]
            )
        )
    return 0


def run_refresh_review(args: argparse.Namespace) -> int:
    results = refresh_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
    )
    refreshed = 0
    for result in results:
        print(f"refreshed\t{result.target.as_posix()}\tfrom={result.source.as_posix()}")
        refreshed += 1
    print(f"Refreshed review files: {refreshed}")
    return 0


def run_reject_review(args: argparse.Namespace) -> int:
    results = reject_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
        force=args.force,
    )
    moved = 0
    skipped = 0
    for result in results:
        status = "moved" if result.copied else "skipped"
        print(f"{status}\t{result.target.as_posix()}\tfrom={result.source.as_posix()}")
        if result.copied:
            moved += 1
        else:
            skipped += 1
    print(f"Rejected review files: moved={moved} skipped={skipped}")
    return 0


def resolve_refinery_root(args: argparse.Namespace) -> Path | None:
    if hasattr(args, "root"):
        return Path(args.root).resolve()

    if not hasattr(args, "target"):
        return None

    target = Path(args.target).resolve()
    if args.command == "update-agents-md" and target.name in GUIDE_FILENAME_CHOICES:
        target = target.parent

    return target / TEMPLATE_METADATA_RELATIVE_PATH.parent.name


def warn_if_cli_version_mismatch(args: argparse.Namespace) -> None:
    refinery_root = resolve_refinery_root(args)
    if refinery_root is None:
        return

    metadata_path = refinery_root / TEMPLATE_METADATA_RELATIVE_PATH.name
    if not metadata_path.is_file():
        return

    try:
        metadata = read_yaml_mapping(metadata_path)
    except (OSError, SystemExit, RefineryCliError) as exc:
        detail = exc.render() if isinstance(exc, RefineryCliError) else str(exc)
        print(
            f"Warning: failed to read template metadata at {metadata_path}: {detail}",
            file=sys.stderr,
        )
        return

    applied_version = metadata.get("cli_version")
    current_version = get_version()
    if applied_version != current_version:
        print(
            "Warning: distributed refinery template was applied with CLI version "
            f"{applied_version}, but the current CLI version is {current_version}.",
            file=sys.stderr,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        warn_if_cli_version_mismatch(args)
        return args.handler(args)
    except RefineryCliError as exc:
        print(exc.render(), file=sys.stderr)
        return exc.exit_code
