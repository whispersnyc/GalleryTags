TODO
- [ ] unicode file names
- [ ] show all existing tags (among loaded files)
- [ ] upload build and add easy quickstart to README
- [ ] if its tag-sorted, re-sort after editing tags
- [ ] edit tags for multiple entries ex. `(multiple values), common tag`
- [ ] `*` = all tags, cli for search/list/get-set
- [ ] `-tag` = hide items with tag if negative prefix
- [ ] refactor redundant headless code

- [ ] add a loading indicator for the enter key add tag menu
- [ ] open file by clicking preview with LAUNCH setting executable; color schemes; video support
- [ ] bulletproof edge cases and error handle everything
- [ ] highlight confirm button in Add Tag screen

- [ ] app.py <folder> --export "/path/to/output.md" "& tag1, tag2" --export ...
- [ ] change export config system, add GUI for export


gallery-tags/
├── managers/
│   ├── image_manager.py      # Handles image loading, sorting, filtering
│   ├── export_manager.py     # Handles export functionality
│   ├── selection_manager.py  # Handles cell selection logic
│   └── tag_manager.py        # Handles tag operations
├── ui/
│   ├── gallery.py           # Only UI-specific code
│   └── tag_dialog.py        # Tag input dialog


floating tagbar, X Untagged option, pywebview/server mode (systray and clickable toast).
