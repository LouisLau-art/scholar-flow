# Research: UI Standardization

## Unknowns & Resolutions

| Unknown | Status | Resolution |
|---------|--------|------------|
| Missing `components.json` | Resolved | Project has partial manual Shadcn setup. Will initialize standard config to enable CLI. |
| Missing `Button`/`RadioGroup` | Resolved | Will install via `shadcn-ui` CLI after config setup. |
| Existing `Tabs` implementation | Resolved | Uses hardcoded Slate colors. Will be updated to standard CSS-variable based implementation during init. |
| DecisionPanel "white-on-white" | Resolved | Resolved by replacing manual classes with standard Shadcn components. |
| Dark Mode Strategy | Resolved | **Explicitly Disabled**. Will lock CSS variables to light mode values in `globals.css` and disable dark mode in Tailwind config. |

## Technical Decisions

### 1. Shadcn Strategy
- **Approach**: "Adopt & Eject" (Initialize standard configuration, then customize).
- **Theme**: "Slate" (Matches existing `slate-900` usage).
- **CSS Variables**: **Enable**. Although we are enforcing light mode, using CSS variables (`--primary`, `--background`) is standard for Shadcn components and allows future flexibility.
- **Light Mode Enforcement**:
    - **Tailwind**: Set `darkMode: ['class']` but strictly do NOT add the class to the root.
    - **CSS**: In `globals.css`, do NOT add `.dark` overrides. Ensure `:root` defines only the light theme values.
    - **Rationale**: Meets FR-009 requirements while maintaining code standard.

### 2. Component Migration
- **Target Components**: `Button`, `RadioGroup`, `Label`, `Tabs` (update), `Card`.
- **Refactoring**: Replace `div` + `onClick` in `DecisionPanel` with `RadioGroup` and `Button`.
- **State Precedence**: Ensure custom styles (if any) prioritize `.data-[state=checked]` or `.data-[state=active]` over `:hover`.

### 3. Dependencies
- Need to install: `class-variance-authority`, `tailwindcss-animate`, `@radix-ui/react-radio-group`, `@radix-ui/react-label`, `@radix-ui/react-slot`.

## Plan Implications
- **Phase 2 Setup**: Will require running shell commands to install dependencies and init Shadcn.
- **Verification**: Check `Tabs` still works after migration. Verify contrast in "DecisionPanel".