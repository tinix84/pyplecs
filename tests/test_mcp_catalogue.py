import pytest

from pyplecs.mcp.plecs_tools import (
    TOOL_CATALOGUE,
    ToolCatalogue,
    ToolDefinition,
)
from pyplecs.mcp.server import build_server

EXPECTED_ARGUMENTS = {
    "plecs_lookup": "topic",
    "plecs_search": "query",
    "plecs_xml": "element",
    "plecs_url": "topic",
    "plecs_component": "name",
    "plecs_rpc": "function",
    "pyplecs_wrappers": None,
    "pyplecs_rpc_surface": None,
}


def test_catalogue_listing_has_explicit_descriptions_and_accurate_schemas():
    assert set(TOOL_CATALOGUE.names) == set(EXPECTED_ARGUMENTS)
    for definition in TOOL_CATALOGUE.definitions:
        argument = EXPECTED_ARGUMENTS[definition.name]
        assert definition.description
        assert definition.input_schema["type"] == "object"
        assert definition.input_schema["additionalProperties"] is False
        if argument is None:
            assert definition.input_schema["properties"] == {}
            assert definition.input_schema["required"] == []
        else:
            assert set(definition.input_schema["properties"]) == {argument}
            assert definition.input_schema["properties"][argument]["type"] == "string"
            assert definition.input_schema["required"] == [argument]


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("plecs_lookup", {}, "missing required argument(s): topic"),
        ("plecs_lookup", {"topic": 3}, "argument 'topic' must be a string"),
        ("plecs_lookup", {"topic": ""}, "argument 'topic' must not be empty"),
        ("plecs_lookup", {"argument": "xml"}, "unexpected argument(s): argument"),
        ("pyplecs_wrappers", {"name": "x"}, "unexpected argument(s): name"),
    ],
)
def test_catalogue_validation_is_local_and_explicit(name, arguments, message):
    outcome = TOOL_CATALOGUE.dispatch(name, arguments)

    assert outcome.success is False
    assert message in outcome.error


def test_catalogue_dispatches_tools_without_runtime_interface_reflection():
    no_argument = TOOL_CATALOGUE.dispatch("pyplecs_rpc_surface", {})
    with_argument = TOOL_CATALOGUE.dispatch("plecs_url", {"topic": "saturable inductor"})

    assert no_argument.success is True
    assert isinstance(no_argument.value, list)
    assert with_argument.success is True
    assert with_argument.value.startswith("https://docs.plexim.com")


def test_unknown_and_execution_errors_are_owned_by_the_catalogue():
    def explode(topic):
        raise RuntimeError(f"cannot read {topic}")

    catalogue = ToolCatalogue(
        [
            ToolDefinition(
                name="explode",
                description="Fail for testing.",
                input_schema={
                    "type": "object",
                    "properties": {"topic": {"type": "string", "minLength": 1}},
                    "required": ["topic"],
                    "additionalProperties": False,
                },
                handler=explode,
            )
        ]
    )

    unknown = catalogue.dispatch("missing", {})
    failed = catalogue.dispatch("explode", {"topic": "offline"})

    assert unknown.error == "unknown tool: missing"
    assert failed.error == "tool 'explode' execution error: cannot read offline"


def test_stdio_adapter_registers_catalogue_listing_and_dispatch_handlers():
    server = build_server()

    assert server.get_request_handler("tools/list") is not None
    assert server.get_request_handler("tools/call") is not None
