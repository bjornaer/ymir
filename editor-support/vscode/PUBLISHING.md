# Publishing Ymir Extension to VSCode Marketplace

This guide explains how to publish the Ymir Language Support extension to the Visual Studio Code Marketplace.

## Prerequisites

1. **Microsoft Account**: You'll need a Microsoft account to access Azure DevOps
2. **Azure DevOps Organization**: Create one at https://dev.azure.com if you don't have one
3. **Personal Access Token (PAT)**: Required for publishing

## Step 1: Create a Publisher Account

1. Go to the [Visual Studio Marketplace Publishing Portal](https://marketplace.visualstudio.com/manage)
2. Sign in with your Microsoft account
3. Click on "Create publisher"
4. Fill in the details:
   - **Publisher ID**: A unique identifier (e.g., `ymir-lang`)
   - **Display Name**: Human-readable name (e.g., `Ymir Language Team`)
   - **Description**: Brief description of your publisher profile

## Step 2: Create a Personal Access Token (PAT)

1. Go to https://dev.azure.com
2. Click on "User Settings" (top right) → "Personal Access Tokens"
3. Click "+ New Token"
4. Configure the token:
   - **Name**: "VSCode Extension Publishing"
   - **Organization**: Select "All accessible organizations"
   - **Expiration**: Choose a suitable duration (90 days recommended for security)
   - **Scopes**: Select "Marketplace" → Check "Manage"
5. Click "Create" and **COPY THE TOKEN** (you won't be able to see it again!)

## Step 3: Update package.json

Before publishing, update the `publisher` field in `package.json` to match your publisher ID:

```json
{
  "publisher": "your-publisher-id",
  ...
}
```

Then recompile and repackage:

```bash
npm run compile
vsce package
```

## Step 4: Login with vsce

Login to your publisher account using the PAT:

```bash
vsce login your-publisher-id
```

When prompted, paste your Personal Access Token.

## Step 5: Publish the Extension

### Option A: Publish directly

```bash
vsce publish
```

This will:
- Automatically increment the version
- Package the extension
- Upload it to the marketplace

### Option B: Publish a specific version

```bash
# Publish as patch version (0.1.0 → 0.1.1)
vsce publish patch

# Publish as minor version (0.1.0 → 0.2.0)
vsce publish minor

# Publish as major version (0.1.0 → 1.0.0)
vsce publish major

# Publish specific version
vsce publish 0.2.0
```

### Option C: Publish pre-packaged .vsix

If you already have a `.vsix` file:

```bash
vsce publish --packagePath ./ymir-language-0.1.0.vsix
```

## Step 6: Verify Publication

1. Go to https://marketplace.visualstudio.com/vscode
2. Search for "Ymir Language Support"
3. Verify the extension appears correctly
4. Check that the icon, description, and screenshots are correct

## Local Installation (Testing Before Publishing)

To test the extension locally before publishing:

```bash
code --install-extension ymir-language-0.1.0.vsix
```

Or in VSCode:
1. Open Extensions (Ctrl+Shift+X)
2. Click "..." menu → "Install from VSIX..."
3. Select `ymir-language-0.1.0.vsix`

## Updating the Extension

When you make changes:

1. Update version in `package.json`
2. Update `CHANGELOG.md` with changes
3. Commit your changes
4. Recompile and publish:

```bash
npm run compile
vsce publish
```

## Important Notes

### Publisher ID
The current `package.json` uses `"publisher": "ymir"`. You'll need to either:
- Register the publisher ID "ymir" on the marketplace, OR
- Change it to your registered publisher ID

### Icon
The extension uses the Ymir logo from `/assets/ymir_logo_full_ice.png`. Make sure this is properly attributed if required.

### Repository
Update the repository URL in `package.json` if you're publishing from a fork:

```json
{
  "repository": {
    "type": "git",
    "url": "https://github.com/YOUR-USERNAME/ymir"
  }
}
```

## Marketplace Badge

After publishing, you can add a marketplace badge to your README:

```markdown
[![VSCode Marketplace](https://img.shields.io/vscode-marketplace/v/ymir.ymir-language.svg)](https://marketplace.visualstudio.com/items?itemName=ymir.ymir-language)
```

## Troubleshooting

### "Publisher not found"
- Make sure you've created the publisher account
- Verify you're logged in: `vsce logout` then `vsce login your-publisher-id`

### "Error: Missing publisher name"
- Update the `publisher` field in `package.json`

### "Invalid Personal Access Token"
- Create a new PAT with correct permissions (Marketplace → Manage)
- Make sure "All accessible organizations" is selected

### "Version already exists"
- Increment the version number in `package.json`
- Or use `vsce publish patch/minor/major`

## Unpublishing (Use with Caution)

To remove the extension from the marketplace:

```bash
vsce unpublish your-publisher-id.ymir-language
```

⚠️ **Warning**: Unpublishing can confuse users who have already installed the extension. Consider deprecating instead.

## Continuous Integration

For automated publishing with GitHub Actions, see the example workflow in `.github/workflows/publish-extension.yml` (if created).

## Resources

- [Publishing Extensions](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Extension Manifest](https://code.visualstudio.com/api/references/extension-manifest)
- [Visual Studio Marketplace](https://marketplace.visualstudio.com/)

