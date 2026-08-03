# UI/UX guidelines

forager's look is **SpaceTheme-inspired** (the dark, layered, rounded aesthetic
of the Steam client skin). Principles:

## Colour

- Near-black base (`#0a0a0a`) with layered "shelf" surfaces (COLOR_1/2/3/4).
- One accent for interactive/primary actions: `#666cff` (accent-1), lightened
  to `#878cff` on hover.
- Semantic colours kept sparse: blue for section titles/links, green for
  positive (install), red for destructive (launch-adjacent or sign-out).
- Muted text `#8e8e8e` for secondary information; full white only for primary.

See [theming.md](theming.md) for the palette and QSS mechanics.

## Shape & spacing

- Unified border radius of 8px everywhere (cards, panels, inputs).
- Content sits on raised panels (COLOR_2) against the page gradient; sections
  are cards with their own rows, never bare group boxes.
- Generous margins inside cards; consistent 14–20px spacing rhythm.

## Interaction

- Primary actions are filled accent buttons; secondary actions are flat
  surface buttons with a hairline border.
- Selected state is unmistakable: filled accent (radios/checkboxes) or an
  accent underline/border (tabs/nav).
- Hover feedback on everything clickable; the cursor is a pointing hand for
  buttons.

## Reading

- Fonts: Roboto (system) for the UI; VT323 reserved for generated placeholder
  artwork titles. See [typography.md](typography.md).
- Never rely on colour alone — selected/hover states also change shape/weight.
