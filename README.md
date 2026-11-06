# Why This Song? - D2

This Mesa model selects ten recommended songs from a 90song catalogue using established and recent preference profiles. It compares three hypothetical listening scenarios at weights 0, .25, .50, .75 and 1. The main D2 comparison is .50 versus .75.

## Run

Use Python 3.12. From this folder:

```text
python -m pip install -r requirements.txt
python run.py
python run_source_example.py
```

The first command installs the dependencies. run.py runs the recommendation model, run_source_example.py runs the separately preserved original Mesa example.

No account, API key or external dataset is required. Model runs work offline after installation.

## Files

- data/catalogue.csv: the 90 total songs and their characteristics.
- data/profiles.json: the fixed hypothetical listening sets and selection rationale.
- src/project_model/: the adapted agents, model, scoring and output code.
- src/boltzmann_wealth_model/: the complete unchanged Mesa starting example, its licence and source citation. My project uses its Mesa structure, not its wealth rules or much of its content in general. Its original browser demonstrations are preserved but are not needed for the documented headless run.
- docs/report.md: the eClass report link for the projects D2 specifications (I only put the link because I did not want my D2 and project info to be on a public GitHub repo, at least yet).

## Six output files

| File in outputs/                        | Contents                                                                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| baseline_raw_00_rankings.csv            | All candidate scores and selected ranks at w=.50                                                                                                    |
| alternative_raw_00_rankings.csv         | Same fields at w=0, .25, .75 and 1; filter .75 for the main alternative                                                                             |
| baseline_processed_00_playlists.html    | Baseline playlists and genre counts                                                                                                                 |
| alternative_processed_00_playlists.html | Alternative playlists and genre counts, labelled by weight                                                                                          |
| alternative_processed_01_comparison.csv | Songs replaced between weights, song IDs entering/leaving, score gaps between ranks 10 and 11, and counts across all five weights                   |
| alternative_processed_02_comparison.png | Songs replaced when the weight increases by 0.25, songs recommended only at middle weights, and different songs recommended across all five weights |

Each CSV identifies its scenario and weight. A positive selected_rank identifies a recommended song, 0 means it was not selected. Exact fractions determine scores and ties, decimal scores are for display. From w=0.50 to w=0.75, aligned replaces 0 of its ten songs, half different replaces 1 and contrasting replaces 4

Across all five playlists, aligned recommends 10 different songs, half different recommends 15 and contrasting recommends 22. Count each song ID once, even if it appears in more than one playlist. So 15 means 15 different songs across the five playlists, each playlist still contains ten songs. In the comparison CSV, unique_tracks_all_weights is this total and additional_tracks_all_weights is the total minus ten. These totals repeat on each row for that scenario, do not add them together.

Songs replaced when the weight increases by 0.25 means ten minus the number of songs shared by those two playlists. Changing the order of the same songs does not count as replacement. Songs recommended only at middle weights means songs selected at w=0.25, 0.50 or 0.75 that are selected at neither w=0 nor w=1. The count is calculated separately at each middle weight.

Rerunning replaces these six files. To save a separate run, use `python run.py --output-dir PATH`. `--data-dir PATH` selects another folder containing catalogue.csv and profiles.json.

## Limits

Fixed feature weights: genre 50%, tempo 15%, year 20%, duration 10% and estimated key 5%.
Ten Mesa steps for one playlist, not ten weeks. Metadata includes estimates, and profiles are only hypothetical. There is no listener customization, learning, user study and it does not reproduce Spotifys algorithms. See the report for evidence and explanations.

Repository: https://github.com/Can1Cyp2/eecs4461-spotify-recommendations
