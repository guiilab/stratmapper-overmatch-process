# Data Processing for StratMapper - Overmatch

### Overview
This package converts CSV files into JSON files for visualization in StratMapper - Overmatch.

Note: users must maintain the file structure in this directory or change filepaths in the config file ('./processing/config.py').

### Get Started
Follow these steps to process CSV files for use in StratMapper:

1. Download the repository.
```sh
git clone https://github.com/guiilab/stratmapper-overmatch-process
```
2. Open 'stratmapper-overmatch-process' in IDE of choice.
3. Place CSV files in replays folder ('./data/replays'). By default, there are two files (126_ESP.csv, 221_ESP.csv) in this folder for demonstration purposes. To process different files, remove these.
4. Run 'raw_to_stratmapper.py' file in IDE or system command line.
5. Check output folder ('./data/output'). There are two directories and multiple files with an 'events' prefix. These are JSON arrays of events objects. In the 'config' directory, there will be a 'matches_config.json' file, which is a JSON array of all of the match configuration objects (one for each csv placed in ('./data/replays'). If renaming was elected, there will also be a rename_map.json file with this information. In the 'match_config' directory, there will be individual files for each match_config object in the previously mentioned JSON array of match_config objects.
6. To load these files into StratMapper, follow the instructions in this [repository](https://github.com/guiilab/stratmapper-overmatch).