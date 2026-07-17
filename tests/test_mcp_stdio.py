from __future__ import annotations

import anyio
from mcp import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_server_lists_expected_tools() -> None:
    async def exercise_server() -> None:
        parameters = StdioServerParameters(
            command="uv",
            args=[
                "run",
                "--frozen",
                "--project",
                ".",
                "knowledge-refinery",
                "mcp",
                "serve",
            ],
        )
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await session.list_tools()

        names = {tool.name for tool in result.tools}
        assert names == {
            "refinery_get_experience",
            "refinery_get_memory",
            "refinery_get_project_metadata",
            "refinery_info",
            "refinery_list_projects",
            "refinery_record_experience",
            "refinery_record_memory",
            "refinery_search_experiences",
            "refinery_search_memory",
            "refinery_update_project_metadata",
            "refinery_validate",
        }
        record_experience = next(
            tool for tool in result.tools if tool.name == "refinery_record_experience"
        )
        assert "expected_updated_at" in record_experience.inputSchema["properties"]
        assert "expected_updated_at" not in record_experience.inputSchema.get("required", [])
        update_metadata = next(
            tool for tool in result.tools if tool.name == "refinery_update_project_metadata"
        )
        assert "expected_updated_at" in update_metadata.inputSchema.get("required", [])
        assert "name" not in update_metadata.inputSchema.get("required", [])
        assert "tags" not in update_metadata.inputSchema.get("required", [])

    anyio.run(exercise_server)
