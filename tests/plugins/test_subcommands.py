# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from dataclasses import dataclass

import pytest
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from conda import plugins
from conda.auxlib.ish import dals
from conda.cli.conda_argparse import BUILTIN_COMMANDS
from conda.plugins.types import CondaSubcommand
from conda.testing import CondaCLIFixture


@dataclass(frozen=True)
class SubcommandPlugin:
    name: str
    summary: str

    def custom_command(self, args):
        pass

    @plugins.hookimpl
    def conda_subcommands(self):
        yield CondaSubcommand(
            name=self.name,
            summary=self.summary,
            action=self.custom_command,
        )


def test_invoked(plugin_manager, conda_cli: CondaCLIFixture, mocker: MockerFixture):
    """Ensure we are able to invoke our command after creating it."""
    # mocks
    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")

    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    conda_cli("custom", "some-arg", "some-other-arg")

    # assertions; make sure our command was invoked with the right arguments
    mocked.assert_called_with(("some-arg", "some-other-arg"))


def test_help(plugin_manager, conda_cli: CondaCLIFixture, capsys: CaptureFixture):
    """Ensures the command appears on the help page."""
    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    with pytest.raises(SystemExit, match="0"):
        conda_cli("--help")

    stdout, stderr = capsys.readouterr()

    # assertions; make sure our command appears with the help blurb
    assert "custom            Summary." in stdout
    assert not stderr


def test_duplicated(plugin_manager, conda_cli: CondaCLIFixture):
    """
    Ensures we get an error when attempting to register commands with the same `name` property.
    """
    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    with pytest.raises(ValueError, match="Plugin already registered"):
        plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))


@pytest.mark.parametrize("command", BUILTIN_COMMANDS)
def test_cannot_override_builtin_commands(command, plugin_manager, mocker, conda_cli):
    """
    Ensures that plugin subcommands do not override the builtin conda commands
    """
    # mocks
    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")
    mock_log = mocker.patch("conda.cli.conda_argparse.log")

    # setup
    plugin_manager.register(SubcommandPlugin(name=command, summary="Summary."))

    # test
    with pytest.raises(SystemExit, match="0"):
        conda_cli(command, "--help")

    # assertions; make sure we got the right error messages and didn't invoke the custom command
    assert mock_log.error.mock_calls == [
        mocker.call(
            dals(
                f"""
                The plugin '{command}' is trying to override the built-in command
                with the same name, which is not allowed.

                Please uninstall the plugin to stop seeing this error message.
                """
            )
        )
    ]

    assert mocked.mock_calls == []
