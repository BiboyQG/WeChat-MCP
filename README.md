# WeChat MCP Landing Page

This branch contains the built landing page for WeChat MCP.

**Live site**: https://biboyqg.github.io/WeChat-MCP/

## About WeChat MCP

WeChat MCP is an MCP server that automates WeChat on macOS using the Accessibility API. It enables AI assistants like Claude Code to read and send WeChat messages.

For the source code and documentation, see the [master branch](https://github.com/BiboyQG/WeChat-MCP/tree/master).

## Development

The landing page is built with:
- React
- TypeScript
- Vite
- Linear-inspired design

### Update and Deploy

To update the landing page and deploy in a single command:

```bash
npm run build --prefix landing-page && cp -r landing-page/dist/* . && git add -A && git commit -m "chore: update landing page" && git push
```

### Manual Steps

1. Make changes to the landing page source in `landing-page/src/`
2. Build the project: `npm run build --prefix landing-page`
3. Copy built files: `cp -r landing-page/dist/* .`
4. Commit and push: `git add -A && git commit -m "chore: update landing page" && git push`
