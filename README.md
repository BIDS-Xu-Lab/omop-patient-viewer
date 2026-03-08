# omop-patient-viewer

Terminal patient viewer for OMOP CDM CSV datasets.

## Run

```bash
uv run omop-patient-viewer ./sample_omop_data
```

## Current Features

- Detects standard OMOP CSV tables in a directory
- Shows a patient list with fixed visit and event statistics
- Provides `Table View` and `Visit Based View`
- Supports reload and record expansion shortcuts

## Keys

- `Up/Down` or `j/k`: move patient selection
- `Tab`: switch focus
- `v`: toggle detail mode
- `Up/Down` on the detail navigator: switch table or visit
- `[` / `]`: switch current table in table view
- `x`: expand or collapse full record details
- `r`: reload CSV data
- `?`: help
- `q`: quit
