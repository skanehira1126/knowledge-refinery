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
            "refinery_browse_knowledge_tags",
            "refinery_get_experience",
            "refinery_get_memory",
            "refinery_get_project_metadata",
            "refinery_info",
            "refinery_list_projects",
            "refinery_record_experience",
            "refinery_record_memory",
            "refinery_search_experiences",
            "refinery_search_knowledge_tags",
            "refinery_search_memory",
            "refinery_update_tag_description",
            "refinery_update_project_metadata",
            "refinery_validate",
        }
        descriptions = {tool.name: tool.description for tool in result.tools}
        assert descriptions == {
            "refinery_browse_knowledge_tags": (
                "Knowledge tagを指定階層の直下だけ、説明と利用件数を付けて取得します。"
            ),
            "refinery_get_experience": (
                "experience IDまたはproject-id/experience-idを指定してexperienceを取得します。"
            ),
            "refinery_get_memory": (
                "memory IDとscopeを指定してprojectまたはshared memoryを取得します。"
            ),
            "refinery_get_project_metadata": (
                "有効なrepositoryに対応する中央project metadataを取得します。"
            ),
            "refinery_info": (
                "MCP packageと文書schemaのversionを返し、CLIとのずれを確認できるようにします。"
            ),
            "refinery_list_projects": (
                "active vaultに登録されたprojectの識別・検索用metadataを一覧取得します。"
            ),
            "refinery_record_experience": (
                "experienceを作成し、既存文書は直前に取得したrevisionを使って更新します。"
            ),
            "refinery_record_memory": (
                "memoryを作成し、既存文書はrefinery_get_memoryのrevisionを使って更新します。"
            ),
            "refinery_search_experiences": (
                "有効なrepositoryのexperienceを検索し、必要な場合はvault全体へ対象を広げます。"
            ),
            "refinery_search_knowledge_tags": (
                "Knowledge tagのpathと説明をAND条件の語句で検索し、利用件数も取得します。"
            ),
            "refinery_search_memory": (
                "有効なrepositoryからproject/shared memoryを構造化fieldと全文で検索します。"
            ),
            "refinery_update_project_metadata": (
                "project metadataを部分更新します。省略fieldは保持し、"
                "空listは対象listを消去します。"
            ),
            "refinery_update_tag_description": (
                "Knowledge tagの説明をtaxonomyの現在revisionを使って登録・更新します。"
            ),
            "refinery_validate": (
                "active vaultのtaxonomy、project metadata、experience、memoryを検証します。"
            ),
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
        browse_tags = next(
            tool for tool in result.tools if tool.name == "refinery_browse_knowledge_tags"
        )
        assert "project_path" in browse_tags.inputSchema.get("required", [])
        assert "parent_tag" not in browse_tags.inputSchema.get("required", [])
        search_tags = next(
            tool for tool in result.tools if tool.name == "refinery_search_knowledge_tags"
        )
        assert "terms" in search_tags.inputSchema.get("required", [])
        update_tag = next(
            tool for tool in result.tools if tool.name == "refinery_update_tag_description"
        )
        assert "expected_updated_at" not in update_tag.inputSchema.get("required", [])

    anyio.run(exercise_server)
