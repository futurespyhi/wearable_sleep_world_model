# Web AI, GitHub, Canva and Overleaf

Official documentation checked 2026-11-12. ChatGPT, Claude, Canva and Overleaf connector availability, connected accounts and application write permissions have not been tested. HPG Git transport is tracked separately in [CURRENT_STATUS](../CURRENT_STATUS.md). This repository does not install connectors or schedule work.

## Shared evidence workflow

GitHub holds goals, task specs, code, aggregate reports and decisions. ChatGPT/Claude read the current commit and run reports, propose revisions and write task specs through authorized GitHub tools. Codex implements in HPG and records results back into the repository. Canva and Overleaf consume the reviewed scientific evidence for presentation and manuscript work.

Start with an explicit refresh/read on each web-AI review. A Git push is not by itself a notification or a new chat turn. Automatic triggers are a separate optional setup.

## ChatGPT

Official documentation supports plugins with MCP tools in ChatGPT web; service authentication and allowed actions determine what can be read or written. Use the GitHub capability available to the account, then verify access to the intended private repository. Do not infer write permission from successful reading.

- [OpenAI plugins documentation](https://learn.chatgpt.com/docs/plugins)
- [Custom MCP connection quickstart](https://developers.openai.com/plugins/quickstart)

On eligible plans/workspaces, GitHub pull-request events can trigger scheduled tasks; availability and repository authorization are required. This is optional and has not been configured here. An initial manual loop is sufficient.

- [OpenAI scheduled tasks](https://learn.chatgpt.com/docs/automations)

## Claude

Claude's built-in GitHub integration supplies files from a chosen branch and offers explicit synchronization. Its documented context does not include commit/PR metadata; do not treat that file integration as a write-back tool. Remote MCP supports external actions when the server exposes them and the user grants access.

- [Claude GitHub integration](https://support.claude.com/en/articles/10167454-use-the-github-integration)
- [Claude remote MCP connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
- [GitHub official MCP server](https://github.com/github/github-mcp-server)

GitHub's hosted MCP endpoint is `https://api.githubcopilot.com/mcp/`. Authentication compatibility and required tools must be verified in the actual client. There is no need to expose the HPG login node as a public MCP endpoint for this GitHub-mediated workflow.

## Canva

Use Canva's official AI connector / MCP for creating, editing and exporting designs. The Canva Dev MCP targets app development and is a different tool. Generate scientific plots and numbers from experiment code, then use Canva for presentation layout.

- [Canva MCP documentation](https://www.canva.dev/docs/apps/mcp/)
- [Connect Claude to Canva](https://www.canva.com/help/connect-claude-to-canva/)
- [Canva connector setup](https://www.canva.com/help/mcp-agent-setup/)

## Overleaf

Use official Git or GitHub synchronization as the initial bridge. Both are Premium features, potentially covered by an institution or group. GitHub synchronization is explicit push/pull, not continuous live synchronization. Initial connection pairs an existing Overleaf project with a new GitHub repository, or imports an existing GitHub repository into a new Overleaf project; it does not directly pair two pre-existing objects.

Keep a manuscript in a focused manuscript repository or an explicitly managed export. Overleaf Git does not implement the full branching/tag/LFS behavior of a general code repository. This bootstrap found an independent old AD manuscript in local `IoT_medical/paper/`; it was not changed or imported as the G3 paper.

- [Overleaf GitHub synchronization](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/github-synchronization)
- [Overleaf Git integration](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration)
- [Overleaf Premium features](https://docs.overleaf.com/getting-started/free-and-premium-plans/premium-features)

No official Overleaf MCP was located in the reviewed official documentation. Third-party MCP implementations are optional alternatives, not a prerequisite or an official integration established by this work.
