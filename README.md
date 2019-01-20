# Data Processing for StratMapper - Overmatch

### Overview
This package converts CSV files into JSON files for visualization in StratMapper - Overmatch.

Note: users must maintain the file structure in this directory or change filepaths in the config file ('./processing/config/py').

### Get Started
Follow these steps to process CSV files for use in StratMapper:

1. Download repository.
```sh
git clone https://github.com/guiilab/stratmapper-overmatch-process
```
2. Open 'stratmapper-overmatch-process' in IDE of choice.
3. Place CSV files in replays folder ('./data/replays').
4. Run 'raw_to_stratmapper.py' file.
5. Check output folder ('./data/output'). There will be JSON files for each CSV file, as well as a directory 'config' with a 'matches_config.json' file, which is a JSON Array of formatted match files (one for each csv file).
6. To load these files into StratMapper, follow the instructions in this [repository](https://github.com/guiilab/stratmapper-overmatch).