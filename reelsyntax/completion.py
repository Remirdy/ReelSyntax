import argparse
from typing import Any

SUPPORTED_COMPLETION_SHELLS = ("bash", "zsh", "fish", "powershell")


def _extract_cli_tree(root_parser: argparse.ArgumentParser) -> dict[str, Any]:
    global_opts: list[str] = []
    subcommands: dict[str, dict[str, Any]] = {}

    for action in root_parser._actions:
        for opt in action.option_strings:
            global_opts.append(opt)
        if isinstance(action, argparse._SubParsersAction):
            for cmd_name, sub_parser in sorted(action.choices.items()):
                opts: list[str] = []
                nested: list[str] = []
                for sub_act in sub_parser._actions:
                    for opt in sub_act.option_strings:
                        opts.append(opt)
                    if isinstance(sub_act, argparse._SubParsersAction):
                        nested.extend(sorted(sub_act.choices.keys()))
                subcommands[cmd_name] = {
                    "options": sorted(set(opts)),
                    "subcommands": nested,
                }
    return {
        "global_options": sorted(set(global_opts)),
        "commands": subcommands,
    }


def generate_completion(shell: str) -> str:
    normalized = shell.strip().lower()
    if normalized not in SUPPORTED_COMPLETION_SHELLS:
        raise ValueError(f"Unsupported shell {shell!r}; choose from {list(SUPPORTED_COMPLETION_SHELLS)}")

    from .cli import parser

    tree = _extract_cli_tree(parser())
    commands = sorted(tree["commands"].keys())
    global_opts = tree["global_options"]
    top_words = " ".join(commands + global_opts)

    if normalized == "bash":
        cases: list[str] = []
        for cmd in commands:
            words = " ".join(tree["commands"][cmd]["subcommands"] + tree["commands"][cmd]["options"])
            cases.append(
                f'        {cmd})\n            COMPREPLY=( $(compgen -W "{words}" -- "${{cur}}") )\n            return 0\n            ;;'
            )
        joined_cases = "\n".join(cases)
        return (
            "_reelsyntax_complete() {\n"
            "    local cur prev cmd\n"
            '    cur="${COMP_WORDS[COMP_CWORD]}"\n'
            '    prev="${COMP_WORDS[COMP_CWORD-1]}"\n'
            '    if [[ ${COMP_CWORD} -eq 1 ]]; then\n'
            f'        COMPREPLY=( $(compgen -W "{top_words}" -- "${{cur}}") )\n'
            "        return 0\n"
            "    fi\n"
            '    cmd="${COMP_WORDS[1]}"\n'
            '    case "${cmd}" in\n'
            f"{joined_cases}\n"
            "    esac\n"
            "    return 0\n"
            "}\n"
            "complete -F _reelsyntax_complete reelsyntax\n"
        )

    if normalized == "zsh":
        sub_cases: list[str] = []
        for cmd in commands:
            words = " ".join(tree["commands"][cmd]["subcommands"] + tree["commands"][cmd]["options"])
            sub_cases.append(f"        {cmd}) compadd -- {words} ;;")
        joined_zsh = "\n".join(sub_cases)
        return (
            "_reelsyntax() {\n"
            "    if (( CURRENT == 2 )); then\n"
            f"        compadd -- {top_words}\n"
            "        return\n"
            "    fi\n"
            '    case "${words[2]}" in\n'
            f"{joined_zsh}\n"
            "    esac\n"
            "}\n"
            "compdef _reelsyntax reelsyntax\n"
        )

    if normalized == "fish":
        lines = [
            f"complete -c reelsyntax -n '__fish_use_subcommand' -a '{cmd}'"
            for cmd in commands
        ]
        for gopt in global_opts:
            clean = gopt.lstrip("-")
            flag = "-l" if gopt.startswith("--") else "-s"
            lines.append(f"complete -c reelsyntax -n '__fish_use_subcommand' {flag} '{clean}'")
        for cmd in commands:
            for sub in tree["commands"][cmd]["subcommands"]:
                lines.append(f"complete -c reelsyntax -n '__fish_seen_subcommand_from {cmd}' -a '{sub}'")
            for opt in tree["commands"][cmd]["options"]:
                if opt.startswith("--"):
                    lines.append(f"complete -c reelsyntax -n '__fish_seen_subcommand_from {cmd}' -l '{opt[2:]}'")
        return "\n".join(lines) + "\n"

    cmd_array = ", ".join(f"'{w}'" for w in commands + global_opts)
    ps_branches: list[str] = []
    for cmd in commands:
        sub_items = tree["commands"][cmd]["subcommands"] + tree["commands"][cmd]["options"]
        arr = ", ".join(f"'{item}'" for item in sub_items)
        ps_branches.append(f"        '{cmd}' {{ $candidates = @({arr}) }}")
    joined_ps = "\n".join(ps_branches)
    return (
        "Register-ArgumentCompleter -Native -CommandName reelsyntax -ScriptBlock {\n"
        "    param($wordToComplete, $commandAst, $cursorPosition)\n"
        "    $tokens = $commandAst.CommandElements | ForEach-Object { $_.Extent.Text }\n"
        "    if ($tokens.Count -le 2) {\n"
        f"        $candidates = @({cmd_array})\n"
        "    } else {\n"
        "        $candidates = @()\n"
        "        switch ($tokens[1]) {\n"
        f"{joined_ps}\n"
        "        }\n"
        "    }\n"
        "    $candidates | Where-Object { $_ -like \"$wordToComplete*\" } | ForEach-Object {\n"
        "        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)\n"
        "    }\n"
        "}\n"
    )
