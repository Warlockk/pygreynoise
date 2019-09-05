"""CLI subcommand decorators.

Decorators used to add common functionality to subcommands.

"""
import functools

import click

from greynoise.api import GreyNoise
from greynoise.cli.formatter import FORMATTERS
from greynoise.cli.parameter import ip_addresses_parameter
from greynoise.exceptions import RequestFailure
from greynoise.util import load_config


def echo_result(function):
    """Decorator that prints subcommand results correctly formatted.

    :param function: Subcommand that returns a result from the API.
    :type function: callable
    :returns: Wrapped function that prints subcommand results
    :rtype: callable

    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        result = function(*args, **kwargs)
        context = click.get_current_context()
        params = context.params
        output_format = params["output_format"]
        formatter = FORMATTERS[output_format]
        if isinstance(formatter, dict):
            # For the text formatter, there's a separate formatter for each subcommand
            formatter = formatter[context.command.name]

        output = formatter(result, params.get("verbose", False)).strip("\n")
        click.echo(
            output, file=params.get("output_file", click.open_file("-", mode="w"))
        )

    return wrapper


def handle_exceptions(function):
    """Print error and exit on API client exception.

    :param function: Subcommand that returns a result from the API.
    :type function: callable
    :returns: Wrapped function that prints subcommand results
    :rtype: callable

    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except RequestFailure as exception:
            body = exception.args[1]
            click.echo("API error: {}".format(body["error"]))
            click.get_current_context().exit(-1)

    return wrapper


def pass_api_client(function):
    """Create API client form API key and pass it to subcommand.

    :param function: Subcommand that returns a result from the API.
    :type function: callable
    :returns: Wrapped function that prints subcommand results
    :rtype: callable

    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        context = click.get_current_context()
        api_key = context.params["api_key"]

        if api_key is None:
            config = load_config()
            if not config["api_key"]:
                prog_name = context.parent.info_name
                click.echo(
                    "\nError: API key not found.\n\n"
                    "To fix this problem, please use any of the following methods "
                    "(in order of precedence):\n"
                    "- Pass it using the -k/--api-key option.\n"
                    "- Set it in the GREYNOISE_API_KEY environment variable.\n"
                    "- Run {!r} to save it to the configuration file.\n".format(
                        "{} setup".format(prog_name)
                    )
                )
                context.exit(-1)
            api_key = config["api_key"]

        api_client = GreyNoise(api_key)
        return function(api_client, *args, **kwargs)

    return wrapper


def gnql_command(function):
    """Decorator that groups decorators common to gnql query and stats subcommands."""

    @click.command()
    @click.argument("query", required=False)
    @click.option("-k", "--api-key", help="Key to include in API requests")
    @click.option("-i", "--input", "input_file", type=click.File(), help="Input file")
    @click.option(
        "-o", "--output", "output_file", type=click.File(mode="w"), help="Output file"
    )
    @click.option(
        "-f",
        "--format",
        "output_format",
        type=click.Choice(["json", "txt", "xml"]),
        default="txt",
        help="Output format",
    )
    @click.option("-v", "--verbose", is_flag=True, help="Verbose output")
    @pass_api_client
    @click.pass_context
    @echo_result
    @handle_exceptions
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)

    return wrapper


def ip_lookup_command(function):
    """Decorator that groups decorators common to ip and quick subcommand."""

    @click.command()
    @click.argument("ip_address", callback=ip_addresses_parameter, nargs=-1)
    @click.option("-k", "--api-key", help="Key to include in API requests")
    @click.option("-i", "--input", "input_file", type=click.File(), help="Input file")
    @click.option(
        "-o", "--output", "output_file", type=click.File(mode="w"), help="Output file"
    )
    @click.option(
        "-f",
        "--format",
        "output_format",
        type=click.Choice(["json", "txt", "xml"]),
        default="txt",
        help="Output format",
    )
    @pass_api_client
    @click.pass_context
    @echo_result
    @handle_exceptions
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)

    return wrapper