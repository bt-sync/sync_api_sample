#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys

SYNC_API_BASE_URL = 'http://localhost:8888/api/v2'

# Update with folder share ids
SYNC_FOLDER_SHARE_ID = ''
STATUS_FOLDER_SHARE_ID = ''

EVENTS_LIST = [
    'EVENT_LOCAL_FILE_ADDED',
    'EVENT_REMOTE_FILE_ADDED',
    'EVENT_LOCAL_FILE_REMOVED',
    'EVENT_REMOTE_FILE_REMOVED',
    'EVENT_LOCAL_FILE_CHANGED',
    'EVENT_REMOTE_FILE_CHANGED',
    'EVENT_FILE_DOWNLOAD_COMPLETED',
]

def get_folder_path(folder_id):
    '''
    Get path on disk of a folder based on folder id/folder share id.
    '''
    res = requests.get('%s/folders/%s' % (SYNC_API_BASE_URL, folder_id))
    path = res.json().get('data').get('path')

    # Windows path
    if path.startswith('\\\\?\\'):
        path = path[4:]
    return path


def check_peer_status():
    '''
    Reads status files for each peer of a folder to check if that peer has the folder in
    sync.
    '''
    # Get path of folder that contains peer status files
    status_folder_path = get_folder_path(STATUS_FOLDER_SHARE_ID)

    # Get folder hash of the folder you want to keep in sync
    res = requests.get('%s/folders/%s/activity' % (SYNC_API_BASE_URL, SYNC_FOLDER_SHARE_ID))
    client_hash = res.json().get('data').get('hash')

    # Get peers of folder so we can check if they are in sync
    peers = res.json().get('data').get('peers')

    # Loop through peers, reading status file for each to compare hash values.
    # Status file is named by peer id. Hash value will match main client's folder hash
    # if the two folders are in the same sync state
    peer_list = []
    for peer in peers:
        try:
            _id = peer.get('id')
            with open('%s/%s.txt' % (status_folder_path, _id), 'r') as status_file:
                data = json.loads(status_file.read())
                is_online = peer.get('isonline')

                # Convert time ticks to display str
                data['last_modified'] = time.ctime(int(data['last_modified']))
                data['peer_id'] = _id
                data['is_online'] = 1 if is_online else 0
                data['sync'] = 1 if data['hash'] == client_hash else 0
                peer_list.append(data)
        except IOError:
            unknown_peer = {}
            unknown_peer['name'] = 'Unknown'
            unknown_peer['peer_id'] = _id
            unknown_peer['last_modified'] = 'Unknown'
            unknown_peer['is_online'] = -1
            unknown_peer['sync'] = -1
            peer_list.append(unknown_peer)
    return peer_list


def update_peer_status():
    '''
    Listens to events. When a folder event occurs, write out the peer's folder hash to
    a text file in the status folder. The file name will be the peer id. Comparing the
    folder hash across different peers lets us check if they are in sync.
    '''
    last_event_id = -1

    # Get path of folder that contains peer status files
    status_folder_path = get_folder_path(STATUS_FOLDER_SHARE_ID)

    # Get peer id
    res = requests.get('%s/client' % SYNC_API_BASE_URL)
    peer_id = res.json().get('data').get('peerid')

    # Get peer name
    res = requests.get('%s/client/settings' % SYNC_API_BASE_URL)
    peer_name = res.json().get('data').get('devicename')

    # Should update status once on start
    write_peer_status(peer_id, peer_name, status_folder_path, SYNC_FOLDER_SHARE_ID)

    while True:
        try:
            print 'Request with Event ID >> %s' % last_event_id #DEBUG
            res = requests.get('%s/events?id=%s' % (SYNC_API_BASE_URL, last_event_id))
            events = res.json().get('data').get('events')

            # Store last event id
            last_event_id = res.json().get('data').get('id')

            # Sort events by id. We want lowest id (earliest) events first so they process first
            # By default we are returned highest id (most current) events
            sorted_events = sorted(events, key=lambda k: k['id'], reverse=False)

            for event in sorted_events:
                event_type = event.get('typename')

                # We only care about folder events where the state changes
                if event_type not in EVENTS_LIST:
                    continue
                else:
                    # We do this here because not all events have a folder object
                    share_id = event.get('folder').get('shareid')

                    # We only care about events for the folder that we want to keep in sync
                    if share_id != SYNC_FOLDER_SHARE_ID:
                        continue

                    write_peer_status(peer_id, peer_name, status_folder_path, SYNC_FOLDER_SHARE_ID)
        except Exception as e:
            print 'Error %s' % e


def write_peer_status(peer_id, peer_name, status_folder_path, sync_folder_id):
    '''
    Helper function to write out folder info to a text file in specified folder.
    '''
    # Get hash of folder you want to keep in sync
    res = requests.get('%s/folders/%s/activity' % (SYNC_API_BASE_URL, sync_folder_id))
    _hash = res.json().get('data').get('hash')

    # Create json object to write to file
    data = {}
    data['name'] = peer_name
    data['last_modified'] = time.time()
    data['hash'] = _hash

    with open('%s/%s.txt' % (status_folder_path, peer_id), 'w') as status_file:
        status_file.write(json.dumps(data))
        print 'Writing to status file >>> Peer id: ' + peer_id


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Error, missing arguments'
        sys.exit()
    elif sys.argv[1] == '--peer':
        update_peer_status()
    else:
        print 'Error, invalid argument'
