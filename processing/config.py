raw_data_folder = '../data/replays/'
output_folder = '../data/output/'

# event_map_file contains event names and corresponding properties
event_map_file = '../data/game_info/overmatch_event_map.json'

# match_config_file contains necessary stratmapper configuration information for different events
match_config_file = '../data/game_info/match_config.json'

# the "rename" variable controls the renaming of the players and teams
# if rename = True, it renames teams as red1, blue1, red2, blue2, and so on. red1, blue1 mean red and blue team
# from match 1, and similarly for others
# player names are also renamed as Blue1_P1, Blue1_P2, Red1_P1, Red1_P2, and so on

# if rename = False, the team names are kept as red and blue and players name as in the csv files

rename = True
