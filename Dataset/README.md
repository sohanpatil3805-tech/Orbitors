# ESA CDM dataset

The CSV files are git-ignored. Download them from the
[ESA Kelvins Collision Avoidance Challenge data page](https://kelvins.esa.int/collision-avoidance-challenge/data/)
(also archived on [Zenodo](https://zenodo.org/records/4463683)) and place them here:

| File | Rows | Used by |
|---|---|---|
| `train_data.csv` (inside `train_data.zip`) | 162,634 CDMs · 13,154 events · 103 columns | training (`collision_model.py`, `uncertainty_model.py`), `validate.py`, dashboard SHAP pages, ESA replays in the web app (held-out validation events) |
| `test_data.csv` | 24,484 CDMs · 2,167 events | test scores (`evaluate_splits`), `validate.py`, dashboard Model Performance page |

The test set only contains CDMs issued at least 2 days before closest approach, so the web app replays events
from the model's held-out validation split of `train_data.csv`, which has complete histories.

Paths are set in `config.py` (`TRAIN_DATA_PATH`, `TEST_DATA_PATH`). Live screening does not need these files.
