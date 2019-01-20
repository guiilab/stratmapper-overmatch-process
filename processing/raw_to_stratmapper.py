import csv
import json
import copy
import os
import numpy as np
from processing.config import raw_data_folder, output_folder, rename, event_map_file, match_config_file

TEAM_1 = "Blue Team"
TEAM_2 = "Red Team"

unique_node_id = 1
unique_match_id = 1

MAP_WIDTH = 600
MAP_HEIGHT = 600
X_MIN = -57500
X_MAX = 57500
Y_MIN = 57500
Y_MAX = -57500

# colors for players
WARM_COLOR = ["#C003B5", "#B83E00", "#FFA646", "#F14264", "#DF020A", "#AB0022", "#FF7800", "#F49AC1", "#FFF200", "#FF00FF"]
COOL_COLOR = ["#0B1BC5", "#1EE000", "#0779AA", "#035072", "#149500", "#4C14C6", "#6968A0", "#85D4E6", "#BDF3B1", "#0049FF"]

# events to handle
NOT_VALID = ['No Valid Target', 'No valid instigator']
EXCEPTIONAL_EVENT = ["ObjectiveCaptured"]
UNUSED_EVENTS = ["PlayerSteamId", "CameraChangeEvent"]
GLOBAL_EVENTS = ["GameMode", "MatchState", "Version", "MapName", "PlayersPerTeam", "ObjectiveCaptured"]
UNIT_EVENTS = ["PlayerTeamJoin", "VehicleSpawned", "PlayerKilled", "UAVLaunch",
               "UAVDestroyed", "ProjectileImpact", "VehicleDamage", "PlayerLeave", "FireEvent",
               "ProjectileImpactExtended", "PlayerJoin", "UAVDamaged"]
UPDATE_EVENTS = ["LocationEvent", "VehicleLocationEvent", "VehicleVelocityEvent", "VehicleOrientationEvent",
                 "CameraOrientationEvent", "WeaponOrientationEvent"]
LINKED_EVENTS = ["PlayerKilled", "VehicleDamage", "UAVDestroyed", "UAVDamaged"]

LINKED_EVENTS_DICT = {"PlayerKilled": [{'event_type': 'player_kill', 'unit': 'attackerName', 'linked_unit': 'victimName'},
                                       {'event_type': 'death', 'unit':'victimName', 'linked_unit': 'attackerName'}],
                     "VehicleDamage": [{'event_type': 'vehicle_damage_delivered', 'unit': 'attackerName', 'linked_unit': 'victimName', 'damage_value': 'damageTaken', 'weapon_type': 'weaponType'},
                                      {'event_type': 'vehicle_damage_received', 'unit':'victimName', 'linked_unit': 'attackerName', 'damage_value': 'damageTaken', 'weapon_type': 'weaponType'}],
                     "UAVDestroyed": [{'event_type': 'uav_destroyed_delivered', 'unit': 'attackerName', 'linked_unit': 'victimName'},
                                      {'event_type': 'uav_destroyed_received', 'unit':'victimName', 'linked_unit': 'attackerName'}],
                     "UAVDamaged": [{'event_type': 'uav_damaged_delivered', 'unit': 'attackerName', 'linked_unit': 'victimName'},
                                      {'event_type': 'uav_damaged_received', 'unit':'victimName', 'linked_unit': 'attackerName'}]
                     }

# rename event names
REFINED_EVENT_NAMES = {"PlayerTeamJoin": "player_team_join", "VehicleSpawned": "vehicle_spawned",
                       "UAVLaunch": "uav_launch", "ProjectileImpact": "projectile_impact_extended",
                       "PlayerLeave": "player_leave", "FireEvent": "fire_event",
                       "ProjectileImpactExtended": "projectile_impact_extended", "PlayerJoin": "player_team_join",
                       "UAVDestroyed": "uav_destroyed", "UAVDamaged": "uav_damaged",
                       "LocationEvent": "VehicleLocationEvent"}

TEAM_NAME = {'Red Team': "red", "Blue Team": "blue"}


Player_Rename_Map = {}
red_player_count = 1
blue_player_count = 1
All_Team_Player_Map = {}


def reset_global_variables():
    """
    reset all global variables after processing one match file
    :return:
    """
    global unique_node_id, Player_Rename_Map, red_player_count, blue_player_count

    unique_node_id = 1
    Player_Rename_Map = {}
    red_player_count = 1
    blue_player_count = 1


def create_directory(path):
    """
    create a directory as the given path if doesn't exist
    :param path: directory to be created
    :return:
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            print("Creation of the directory %s failed" % path)


def refine_event_name(event_name):
    """
    rename events from the REFINED_EVENT_NAMES dictionary
    :param event_name: raw event name
    :return:
    """
    if event_name in REFINED_EVENT_NAMES:
        return REFINED_EVENT_NAMES[event_name]


def get_name_and_extension(file_name):
    """
    get name and extension of a file_name
    :param file_name:
    :return:
    """
    tokens = file_name.split('.')
    return {'name': '.'.join(tokens[0:-1]), 'ext': tokens[-1]}


def convert_timestamp_to_second(timestamp):
    """
    convert x:y:z string time to second in float
    :param timestamp:
    :return:
    """
    parts = timestamp.split(":")
    second = 0
    i = 0
    for part in reversed(parts):
        second += (float(part)*60**i)
        i += 1

    return second


def map_3d_to_2d_location(node_context):
    """
    returns 2d location from 3d. Currently only sends back x,y from x,y,z
    :param node_context: this dictionary contains 'Location_posX', 'Location_posY', 'Location_posZ'
    :return:
    """
    posX_2d = None
    posY_2d = None
    if 'Location_posX' in node_context:
        posX = node_context['Location_posX']
        posY = node_context['Location_posY']
        posZ = node_context['Location_posZ']

        # convert 3d to 2d
        posX_2d = posX
        posY_2d = posY

    elif 'VehicleLocation_posX' in node_context:
        posX = node_context['VehicleLocation_posX']
        posY = node_context['VehicleLocation_posY']
        posZ = node_context['VehicleLocation_posZ']

        # convert 3d to 2d
        posX_2d = posX
        posY_2d = posY

    return posX_2d, posY_2d


def read_event_mapping(fname):
    """
    read event mapping file
    :param fname: event name and corresponding properties in this file
    :return: dictionary of events and properties
    """
    with open(fname) as json_file:
        data = json.load(json_file)
        # print event_mapping
        dict_mapping = {'domain_id': data['domain_id']}
        for event in data['events']:
            dict_mapping[event['event_id']] = event['properties']
        return dict_mapping


def process_global_event(event_row, global_events, event_map):
    """
    processes global events defined in GLOBAL_EVENTS
    :param event_row: one row from csv file
    :param global_events: store info about events
    :param event_map: event name and properties information
    :return:
    """
    event_id = event_row[0]
    # list of properties
    properties = event_map[event_id]

    if event_id == 'MatchState':
        name = ''
        for prop_ind, prop in enumerate(properties):
            element_index = prop_ind + 1
            if prop['property_id'] == 'name':
                name = event_row[element_index]
            if prop['property_id'] == 'timestamp':
                timestamp = convert_timestamp_to_second(event_row[element_index])

        global_events[name+'_timestamp'] = round(timestamp)

    else:

        for prop_ind, prop in enumerate(properties):
            element_index = prop_ind + 1
            if prop['property_id'] == 'timestamp':
                continue
            global_events[prop['property_id']] = event_row[element_index]


def process_exceptional_event(event_row, global_events):
    """
    processes "Objective Captured" event to see the result of the match
    :param event_row: one row from csv file
    :param global_events: store info about events
    :return:
    """
    event_id = event_row[0]
    if event_id == "ObjectiveCaptured":
        global_events['Objective Captured Players: '] = []
        global_events['Objective Captured timestamp: '] = event_row[-1]

    for i in range(1, len(event_row)-1):
        global_events['Objective Captured Players: '].append(event_row[i])


def process_update_event(event_row, player_events, event_map):
    """
    processes update events defined in UPDATE_EVENTS
    :param event_row: one row from csv file
    :param player_events: store info about events
    :param event_map: event name and properties information
    :return:
    """
    event_id = event_row[0]
    properties = event_map[event_id]

    if event_id in REFINED_EVENT_NAMES:
        event_prefix = REFINED_EVENT_NAMES[event_id].replace("Event", "")
    else:
        event_prefix = event_id.replace("Event", "")
    info = {}
    for prop_ind, prop in enumerate(properties):
        element_index = prop_ind + 1

        if prop['property_id'] == 'playerName':
            player_name = event_row[element_index]
            if player_name not in player_events:
                player_events[player_name] = {}
        elif prop['property_id'] == 'timestamp':
            actual_timestamp = convert_timestamp_to_second(event_row[element_index])
            timestamp = int(actual_timestamp)

            if timestamp not in player_events[player_name]:
                player_events[player_name][timestamp] = {'node_context': {}, 'events': [], 'timestamp': actual_timestamp}

        else:
            temp = event_prefix + '_' + prop['property_id']
            info[temp] = event_row[element_index]

    player_events[player_name][timestamp]['node_context'].update(info)


def process_unit_event(event_row, player_events, event_map):
    """
    processes unit events defined in UNIT_EVENTS
    :param event_row: one row from csv file
    :param player_events: store info about events
    :param event_map: event name and properties information
    :return:
    """
    global unique_node_id, red_player_count, blue_player_count, Player_Rename_Map

    # print(event_row)
    event_id = event_row[0]
    # list of properties
    properties = event_map[event_id]

    # store renaming information
    if event_id in ['PlayerTeamJoin', 'PlayerJoin']:
        if event_row[2] in TEAM_NAME and TEAM_NAME[event_row[2]] == 'red':
            Player_Rename_Map[event_row[1]] = 'Red' + str(unique_match_id) + '_P' + str(red_player_count)
            red_player_count += 1
        elif event_row[2] in TEAM_NAME and TEAM_NAME[event_row[2]] == 'blue':
            Player_Rename_Map[event_row[1]] = 'Blue' + str(unique_match_id) + '_P' + str(blue_player_count)
            blue_player_count += 1

    event_info = {"node_id": unique_node_id, "event_type": event_id}
    unique_node_id += 1

    if event_id not in LINKED_EVENTS:
        for prop_ind, prop in enumerate(properties):
            element_index = prop_ind + 1

            # for uav_destroyed and uav_delivered -> because those don't have playerName in data
            if event_id in ['UAVDestroyed', 'UAVDamaged']:
                if prop['property_id'] == 'victimName':
                    player_name = event_row[element_index]
                    event_info['unit'] = player_name
                    if player_name not in player_events:
                        player_events[player_name] = {}

            if prop['property_id'] == 'playerName':
                player_name = event_row[element_index]
                event_info['unit'] = player_name
                if player_name not in player_events:
                    player_events[player_name] = {}

            elif prop['property_id'] == 'timestamp':
                timestamp = convert_timestamp_to_second(event_row[element_index])
                event_info['timestamp'] = timestamp
                if timestamp not in player_events[player_name]:
                    player_events[player_name][timestamp] = {'node_context': {}, 'events': [], 'timestamp': timestamp}

            else:
                event_info[prop['property_id']] = event_row[element_index]

        # refine names
        event_info['event_type'] = refine_event_name(event_info['event_type'])
        player_events[player_name][timestamp]['events'].append(event_info)

    else:
        linked_events = copy.deepcopy(LINKED_EVENTS_DICT[event_id])

        base_event = {}
        for prop_ind, prop in enumerate(properties):
            element_index = prop_ind + 1
            base_event[prop['property_id']] = event_row[element_index]
            if prop['property_id'] == 'timestamp':
                timestamp = convert_timestamp_to_second(event_row[element_index])
                base_event[prop['property_id']] = timestamp

        for link_event in linked_events:
            base_event_copy = copy.deepcopy(base_event)
            for key in link_event:
                if link_event[key] in base_event:
                    del base_event_copy[link_event[key]]
                    link_event[key] = base_event[link_event[key]]

        link_event_1 = linked_events[0]
        link_event_2 = linked_events[1]
        link_event_1_node_id = unique_node_id
        unique_node_id += 1
        link_event_2_node_id = unique_node_id
        unique_node_id += 1

        link_event_1.update({"node_id": link_event_1_node_id})
        link_event_2.update({"node_id": link_event_2_node_id})
        link_event_1.update({"linked_node_id": link_event_2_node_id})
        link_event_2.update({"linked_node_id": link_event_1_node_id})

        if link_event_1['unit'] not in NOT_VALID:
            if timestamp not in player_events[link_event_1['unit']]:
                player_events[link_event_1['unit']][timestamp] = {'node_context': {}, 'events': [], 'timestamp': timestamp}

            player_events[link_event_1['unit']][timestamp]['events'].append(link_event_1)

        if link_event_2['unit'] not in NOT_VALID:
            if timestamp not in player_events[link_event_2['unit']]:
                player_events[link_event_2['unit']][timestamp] = {'node_context': {}, 'events': [], 'timestamp': timestamp}

            player_events[link_event_2['unit']][timestamp]['events'].append(link_event_2)


def process_single_match(csv_data_file, event_map):
    """
    processes single match file
    :param csv_data_file: csv file for one match
    :param event_map: event name and properties info
    :return:
    """
    global unique_node_id

    csv_reader = csv.reader(csv_data_file)

    player_id = []
    player_timestamp_events = {}
    global_events = {}
    player_event_list = {}

    i = 0

    for row in csv_reader:
        event_id = row[0]

        if event_id in GLOBAL_EVENTS:
            process_global_event(row, global_events, event_map)

        elif event_id in UPDATE_EVENTS:
            process_update_event(row, player_timestamp_events, event_map)
            i += 1

        elif event_id in UNIT_EVENTS:
            process_unit_event(row, player_timestamp_events, event_map)

        elif event_id in EXCEPTIONAL_EVENT:
            process_exceptional_event(row, global_events, event_map)

        else:
            if event_id not in UNUSED_EVENTS:
                print("Unknown event found: ", event_id)

    for player in player_timestamp_events:
        if rename:
            if player in Player_Rename_Map:  # some players has no team when they join, they are discarded in SM
                player_rename = Player_Rename_Map[player]
            else:
                player_rename = player
        else:
            player_rename = player

        if player_rename not in player_event_list:
            player_event_list[player_rename] = []
        for tstamp in player_timestamp_events[player]:
            # if the event doesn't have any node context
            if not player_timestamp_events[player][tstamp]['node_context']:
                prev_event_tstamp = int(np.floor(tstamp))
                next_event_tstamp = int(np.ceil(tstamp))

                act_next_t = act_prev_t = -1
                if next_event_tstamp in player_timestamp_events[player]:
                    act_next_t = player_timestamp_events[player][next_event_tstamp]['timestamp']

                if prev_event_tstamp in player_timestamp_events[player]:
                    act_prev_t = player_timestamp_events[player][prev_event_tstamp]['timestamp']

                # no update event with that timestamp
                if act_next_t < 0 and act_prev_t < 0:
                    for event in player_timestamp_events[player][tstamp]['events']:
                        event.update({'posX': None, 'posY': None, 'node_context': None})
                        # timestamp is rounded
                        event['timestamp'] = int(np.round(tstamp))
                        player_event_list[player_rename].append(event)
                else:
                    if np.abs(act_next_t - tstamp) < np.abs(act_prev_t - tstamp):
                        for event in player_timestamp_events[player][tstamp]['events']:
                            player_timestamp_events[player][next_event_tstamp]['events'].append(event)
                    else:
                        for event in player_timestamp_events[player][tstamp]['events']:
                            player_timestamp_events[player][prev_event_tstamp]['events'].append(event)

        for tstamp in player_timestamp_events[player]:
            if player_timestamp_events[player][tstamp]['node_context']:
                if not player_timestamp_events[player][tstamp]['events']:
                    event = {'node_id': unique_node_id, 'unit': player_rename, 'event_type': 'status_update'}
                    unique_node_id += 1
                    event['node_context'] = player_timestamp_events[player][tstamp]['node_context']
                    # print('Second:', event)
                    posX_2d, posY_2d = map_3d_to_2d_location(player_timestamp_events[player][tstamp]['node_context'])
                    event.update({'posX': posX_2d, 'posY': posY_2d})
                    event['timestamp'] = tstamp
                    player_event_list[player_rename].append(event)
                for event in player_timestamp_events[player][tstamp]['events']:
                    # print('Second:', event)
                    event['node_context'] = player_timestamp_events[player][tstamp]['node_context']
                    posX_2d, posY_2d = map_3d_to_2d_location(player_timestamp_events[player][tstamp]['node_context'])
                    event.update({'posX': posX_2d, 'posY': posY_2d})
                    event['timestamp'] = tstamp
                    player_event_list[player_rename].append(event)

    final_event_list = []
    for player in player_event_list:
        player_event_list[player].sort(key=lambda key_id: key_id['timestamp'])

        # update posX, posY of events that doesn't have corresponding status updates with the posX, poY of last event
        no_pos_events = ['player_team_join', 'player_join', 'vehicle_spawned']
        update_posX = None
        update_posY = None
        update_node_context = None
        for event in player_event_list[player]:
            if event['event_type'] not in no_pos_events:
                if event['posX'] == None or event['posY'] == None:
                    event['posX'] = update_posX
                    event['posY'] = update_posY
                    event['node_context'] = update_node_context
                else:
                    update_posX = event['posX']
                    update_posY = event['posY']
                    update_node_context = event['node_context']

        final_event_list.extend(player_event_list[player])

    return global_events, final_event_list, player_event_list


def read_match_config_file(fname):
    """
    reads configuration of the events for stratmapper configuration
    :param fname: file name
    :return:
    """
    with open(fname) as json_file:
        data = json.load(json_file)

    return data


def match_configuration(file_name, player_event_list, global_events, match_config_file):
    """
    creates configuration of a match for stratmapper
    :param file_name: name of the file/match
    :param player_event_list: list of player events information
    :param global_events: list of global events information
    :param match_config_file: partial info of the configuration file that are fixed for all matches
    :return:
    """
    global unique_match_id

    BLACK = "#000000"

    match_config = read_match_config_file(match_config_file)

    warm_color_shuffled = copy.deepcopy(WARM_COLOR)
    np.random.shuffle(warm_color_shuffled)
    cool_color_shuffled = copy.deepcopy(COOL_COLOR)
    np.random.shuffle(cool_color_shuffled)

    # set unit
    units = []
    unit_names = []
    warm_color_count = 0
    cool_color_count = 0
    for player in player_event_list:
        # print(player)
        for event in player_event_list[player]:
            if event['event_type'] == 'player_team_join':
                if 'teamName' in event:
                    if event['teamName'] == TEAM_2:
                        color = warm_color_shuffled[warm_color_count]
                        warm_color_count += 1
                    else:
                        color = cool_color_shuffled[cool_color_count]
                        cool_color_count += 1

                    unit = {"name": player,
                            "group": TEAM_NAME[event['teamName']] + str(unique_match_id),
                            "color": color}
                else:
                    unit = {"name": player,
                            "group": None,
                            "color": BLACK}

                units.append(unit)
                unit_names.append(unit['name'])
                break

    timestamp_range = {
        "start": global_events["MatchStart_timestamp"],
        "end": global_events["MatchEnd_timestamp"]
    }

    groups = [
        {
            "name": "blue" + str(unique_match_id),
            "color": "blue"
        },
        {
            "name": "red" + str(unique_match_id),
            "color": "red"
        }
    ]

    load_settings = {
        "incremental_timeline": False,
        "selected_units": unit_names,  # now all names are in selected units
        "selected_groups": None,
        "selected_events": [
            "death",
            "player_kill",
            "fire_event",
            "projectile_impact_extended",
            "vehicle_damage_delivered",
            "vehicle_damage_received",
            "vehicle_spawned",
            "uav_launch",
            "player_team_join",
            "player_leave"
        ]
    }

    match_config_set = {"file_name": file_name,
                        "match_id": unique_match_id,
                        "timestamp_range": timestamp_range,
                        "coordinate_range": {
                            "x": {
                                "min": X_MIN,
                                "max": X_MAX
                            },
                            "y": {
                                "min": Y_MIN,
                                "max": Y_MAX
                            }
                        },
                        "map": {
                            "map_name": "Overmatch",
                            "map_width": MAP_WIDTH,
                            "map_height": MAP_HEIGHT,
                            "map_url": "http://"
                        },
                        "units": units,
                        "groups": groups,
                        "load_settings": load_settings}

    unique_match_id += 1

    match_config_set.update(match_config)

    return match_config_set


def process_files(data_folder, output_folder, event_map, match_config_file):
    """
    process all match files
    :param data_folder: input raw data folder
    :param output_folder: output folder for stratmapper json file
    :param event_map: event name and properties info
    :param match_config_file: partial info of the configuration file that are fixed for all matches
    :return:
    """
    global unique_node_id

    all_match_configs = []

    for subdir, dirs, files in os.walk(data_folder):
        ind = 1
        for filename in files:
            unique_node_id = 1  # reset unique node id for each match

            name_extension = get_name_and_extension(filename)
            name = name_extension['name']
            ext = name_extension['ext'].lower()

            if ext == 'csv':
                print(ind, ":", name)

                with open(os.path.join(data_folder, filename), 'r') as data_file:
                    global_events, event_list, player_event_list = process_single_match(data_file, event_map)
                    match_config = match_configuration(name, player_event_list, global_events, match_config_file)
                    all_match_configs.append(match_config)

                    create_directory(output_folder)
                    with open(output_folder + name + '.json', 'w') as outfile:
                        json.dump(event_list, outfile)
                        outfile.close()

                # saving all the renaming player with actual names
                if name not in All_Team_Player_Map:
                    All_Team_Player_Map[name] = Player_Rename_Map

                reset_global_variables()

                ind += 1

    create_directory(output_folder + 'config/')
    with open(output_folder + 'config/matches_config.json', 'w') as outfile:
        json.dump(all_match_configs, outfile)
        outfile.close()

    # write renaming map
    # a dictionary that keeps the player names with the new renamed names
    with open(output_folder + 'config/rename_map.json', 'w') as outfile:
        json.dump(All_Team_Player_Map, outfile)
        outfile.close()


if __name__ == "__main__":
    event_map = read_event_mapping(event_map_file)
    process_files(raw_data_folder, output_folder, event_map, match_config_file)
