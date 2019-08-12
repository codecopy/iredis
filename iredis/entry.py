# -*- coding: utf-8 -*-
import os
import sys
import logging
from pathlib import Path
import time

import redis
import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.contrib.regular_languages.lexer import GrammarLexer
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.styles import Style

from .client import Client
from .renders import render_dict
from .redis_lexer import RedisLexer
from .redis_grammar import redis_grammar
from .commands_csv_loader import original_commands


logger = logging.getLogger(__name__)

HISTORY_FILE = Path(os.path.expanduser("~")) / ".iredis_history"
STYLE = Style.from_dict(
    {
        # User input (default text).
        "": "",
        # Prompt.
        "hostname": "",
    }
)
start_time = time.time()


example_style = Style.from_dict(
    {
        "operator": "#33aa33 bold",
        "number": "#ff0000 bold",
        "trailing-input": "bg:#662222 #ffffff",
    }
)

logger.debug(f"[timer] Grammer created: {time.time() - start_time} from start.")

# TODO verify
# Can all redis_grammar have only 1 token, and completer based on lexer?
lexers_dict = {
    "key": SimpleLexer("class:operator"),
    "value": SimpleLexer("class:number"),
}
lexers_dict.update(
    {key: SimpleLexer("class:pygments.keyword") for key in original_commands.keys()}
)
lexer = GrammarLexer(redis_grammar, lexers=lexers_dict)


completer_mapping = {
    syntax: WordCompleter(commands + [command.lower() for command in commands])
    for syntax, commands in original_commands.items()
}
# TODO add key value completer
completer = GrammarCompleter(redis_grammar, completer_mapping)


def repl(client, session):
    logger.debug(f"[timer] First REPL: {time.time() - start_time} from start.")
    while True:
        logger.debug("REPL waiting for command...")
        try:
            command = session.prompt(
                "{hostname}> ".format(hostname=str(client)),
                style=example_style,
                lexer=lexer,
                completer=completer,
            )
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt!")
            continue
        except EOFError:
            print("Goodbye!")
            sys.exit()
        logger.info(f"Command: {command}")

        # blank input
        if not command:
            continue

        try:
            answer = client.send_command(command)
        # Error with previous command or exception
        except Exception as e:
            print("(error)", str(e))

        # Fine with answer
        else:
            print(answer)


# command line entry here...
@click.command()
@click.pass_context
@click.option("-h", help="Server hostname", default="127.0.0.1")
@click.option("-p", help="Server port", default="6379")
@click.option("-n", help="Database number.", default="0")
def gather_args(ctx, h, p, n):
    logger.info(f"iredis start, host={h}, port={p}, db={n}.")
    return ctx


def main():
    # invoke in non-standalone mode to gather args
    ctx = gather_args.main(standalone_mode=False)
    if not ctx:  # called help
        return

    # Create history file if not exists.
    if not os.path.exists(HISTORY_FILE):
        logger.info(f"History file {HISTORY_FILE} not exists, create now...")
        f = open(HISTORY_FILE, "w+")
        f.close()

    session = PromptSession(history=FileHistory(HISTORY_FILE))

    client = Client(**ctx.params)
    repl(client, session)