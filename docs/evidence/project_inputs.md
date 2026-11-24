# Project inputs

## E4. Song catalogue
I selected 90 real songs from my own app, VoiceVault, to make the catalogue. I used a random order within genres so the catalogue would have a mix of genres. The exact songs and characteristics I used are in [data/catalogue.csv](../../data/catalogue.csv). Some values are estimates, specifically the tempo and key. A release year can be from a reissue.


## E5. Listening sets

[data/profiles.json](../../data/profiles.json) has the ten songs I chose for established taste profile and the ten songs for the recent listening in each scenario. The three recent sets share either the same ten songs, five, or zero songs with the established set. I made these sets in order to compare how different songs affect the song recommendations. They are hypothetical listening histories.


## E6. Scoring rule and proposed control

The matching rules and feature weights are in [domain.py](../../src/project_model/domain.py). [agents.py](../../src/project_model/agents.py) combines the established and recent matches. I chose the characteristic weights (genre, tempo, key, bpm, release year) and each setting (for example 70% influence for established taste, versus 30% for recent listening) in the runs. The slider to change the weights is my proposal.
