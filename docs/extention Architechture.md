# Browser Extension Architecture

## Technology

Chrome Extension
Manifest V3
JavaScript

## Components

### manifest.json

Defines:

- Extension metadata
- Permissions
- Content scripts
- Service worker
- Host permissions

### popup/

Contains teacher-facing extension UI.

### content/

Contains scripts that interact with the ERP webpage.

### background/

Contains service worker logic.

## Responsibilities

### Popup

- Start scan
- Upload image
- Display processing state
- Display results
- Ask for confirmation

### Content Script

- Detect ERP page
- Read student rows
- Match student rows
- Modify attendance controls
- Highlight changed rows

### Service Worker

- Handle extension events
- Coordinate messages
- Manage extension-level communication

## Security Rule

Do not request broad permissions unless necessary.

Use the minimum host permissions required.

Do not attempt to bypass authentication,
CAPTCHA, access controls, or ERP security mechanisms.