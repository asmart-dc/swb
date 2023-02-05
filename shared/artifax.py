import logging
from datetime import datetime
import json
from json.decoder import JSONDecodeError

from requests import Request, Session, HTTPError
import pandas as pd
import pyarrow

from shared.key_vault import KeyVault
from shared.datalake import Datalake


class ArtifaxRequest:
    def __init__(
        self, keyvault_name, datalake_name, filesystem_name, directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ):
        self.artifax_endpoint = endpoint
        self.artifax_api_secret = api_secret
        self.artifax_client_secret = client_secret
        self.keyvault_name = keyvault_name
        self.keyvault = KeyVault(azure_credential, self.keyvault_name)
        self.datalake_name = datalake_name
        self.filesystem_name = filesystem_name
        self.directory_name = directory_name
        self.datalake = Datalake(
            azure_credential, self.datalake_name,
            self.filesystem_name, self.directory_name
        )
        self.filename = endpoint.split("/")[1]
        self.import_date = datetime.now().strftime("%Y/%m/%d")

    def process(self):
        self._get_api_secrets()
        if self.artifax_endpoint == 'arrangements/event':
            self._get_event_data()
        else:
            self._get_data()
        self._save_to_lake()

        return self.filename, self.artifax_filename

    def _get_api_secrets(self):
        self.artifax_api_key = self.keyvault.get_key_vault_secret(self.artifax_api_secret)
        self.artifax_client_name = self.keyvault.get_key_vault_secret(self.artifax_client_secret)
        self.artifax_base_url = f"https://{self.artifax_client_name}.artifaxevent.com/api/"

    def _get_event_data(self):
        endpoint = self.artifax_endpoint
        self.artifax_endpoint = 'arrangements/arrangement'
        self._get_data()
        data = json.loads(self.data)
        arrangement_ids = []
        for arrangement in data:
            arrangement_ids.append(
                arrangement['arrangement_id']
            )
        logging.info(f"{len(arrangement_ids)} arrangements to retrieve events for.")

        self.artifax_endpoint = endpoint

        event_data = []
        for arrangement_id in arrangement_ids:
            params = {'arrangement_id': arrangement_id}
            self._get_data(params)

            data = json.loads(self.data)
            try:
                logging.info(f"Arrangement id: {arrangement_id} contains {len(data)} events.")
                event_data.extend(data)
            except TypeError:
                logging.info(f"Arrangement id: {arrangement_id} contains 0 events.")
                continue

        self.data = json.dumps(event_data, sort_keys=True, indent=4)

    def _get_data(self, parameters=None):
        self.url = self.artifax_base_url + self.artifax_endpoint
        self.method = "GET"
        data = self._make_request(parameters=parameters)
        self.data = json.dumps(data, sort_keys=True, indent=4)

    def _make_request(self, parameters=None):
        headers = {'X-API-KEY': self.artifax_api_key}
        session = Session()
        req = Request(method=self.method, url=self.url, headers=headers, params=parameters)

        try:
            r = session.send(req.prepare())
            r.raise_for_status()
            try:
                return r.json()
            except JSONDecodeError:
                # There is one endpoint which returns non-JSON content (instances/{}/status/detail)
                return r.content
        except HTTPError as exc:
            logging.info(exc.response.text)
            pass

    def _save_to_lake(self):
        now = datetime.now().strftime("%Y%m%dT%H%M%S")
        self.artifax_filename = f"{self.artifax_endpoint}/{self.import_date}/{self.filename}_{now}.json"
        self.datalake.upload_file_to_directory(self.artifax_filename, self.data)


class ArtifaxProcessor:
    def __init__(
        self, endpoint, raw_filename, datalake_name, filesystem_raw_name,
        filesystem_structured_name, directory_name, azure_credential
    ):
        self.endpoint = endpoint
        self.entity = endpoint.split("/")[1]
        self.raw_filename = raw_filename
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.filesystem_structured_name = filesystem_structured_name
        self.directory_name = directory_name
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        json_file = self._download_from_lake()
        json_data = json.loads(json_file)
        normalised_data = self._entity(json_data)

        for file in normalised_data:
            filename = file['filename']
            data = file['data']
            self._upload_to_lake(filename, data)

        return self.entity

    def _entity(self, json_data):
        entity = f"_{self.entity}"
        if hasattr(self, entity) and callable(func := getattr(self, entity)):
            return func(json_data)

    def _download_from_lake(self):
        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.directory_name
        )

        raw_file = datalake.download_file_from_directory(self.raw_filename)

        try:
            json_file = raw_file.decode('utf-8')  # decode bytes to str
            return json_file
        except JSONDecodeError as e:
            print(e)

    def _upload_to_lake(self, filename, data):
        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_structured_name, self.directory_name
        )

        now = datetime.now().strftime("%Y%m%dT%H%M%S")

        filename = f"{self.endpoint}/{filename}/{self.import_date}/{filename}_{now}.csv"
        datalake.upload_file_to_directory(filename, data)

        return filename

    def _arrangement(self, json_data):
        logging.info("Normalise arrangement entity")

        normalised_data = []

        # arrangement
        cols = [
            'arrangement_created',
            'arrangement_id',
            'arrangement_reference',
            'arrangement_temporary',
            'arrangement_type_background_colour',
            'arrangement_type_id',
            'arrangement_type_name',
            'arrangement_type_text_colour',
            'close_date_time',
            'contact_entity_full_name',
            'contact_entity_id',
            'customer_entity_full_name',
            'customer_entity_id',
            'customer_entity_type',
            'date_first_confirmed_event',
            'date_first_confirmed_public_event',
            'date_first_event',
            'date_first_public_event',
            'date_last_confirmed_event',
            'date_last_confirmed_public_event',
            'date_last_event',
            'date_last_public_event',
            'description',
            'estimated_revenue',
            'sales_manager_full_name',
            'sales_manager_user_id',
            'sales_process_stage_id',
            'sales_process_stage_title',
            'sales_team_id',
            'sales_team_name'
        ]
        df = pd.json_normalize(json_data)
        df = df[cols]
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'arrangement', 'data': data})

        # arrangement custom forms
        df = pd.json_normalize(
            json_data,
            record_path=['custom_forms', 'custom_form_sections', 'custom_form_elements'],
            meta=[
                'arrangement_id',
                ['custom_forms', 'custom_form_assignment_id'],
                ['custom_forms', 'custom_form_definition_id'],
                ['custom_forms', 'custom_form_name'],
                ['custom_forms', 'custom_form_sections', 'custom_form_section_id'],
                ['custom_forms', 'custom_form_sections', 'custom_form_section_name']
            ]
        )
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'arrangement_custom_forms', 'data': data})

        return normalised_data

    def _event(self, json_data):
        logging.info("Normalise event entity")

        normalised_data = []

        # event
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'event', 'data': data})

        return normalised_data

    def _venue(self, json_data):
        logging.info("Normalise venue entity")

        normalised_data = []

        # venue
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'venue', 'data': data})

        return normalised_data

    def _room(self, json_data):
        logging.info("Normalise room entity")

        normalised_data = []

        # room
        cols = [
            'room_id', 'room_type_id', 'sort_order', 'venue_id', 'code',
            'custom_forms', 'events', 'room_name', 'room_type_name'
        ]
        df = pd.json_normalize(json_data)
        df = df[cols]
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'room', 'data': data})

        # room layouts
        df = pd.json_normalize(json_data, record_path=['room_layouts'], meta=['room_id'])
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'room_room_layout', 'data': data})

        # room event activities
        df = pd.json_normalize(json_data, record_path=['event_activities'], meta=['room_id'])
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'room_event_activity', 'data': data})

        return normalised_data

    def _locale(self, json_data):
        logging.info("Normalise locale entity")

        normalised_data = []

        # locale
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'locale', 'data': data})

        return normalised_data

    def _event_activity(self, json_data):
        logging.info("Normalise event activity entity")

        normalised_data = []

        # event activity
        cols = [
            'activity_id', 'background_color', 'code', 'custom_forms',
            'event_activity_name', 'text_color'
        ]
        df = pd.json_normalize(json_data)
        df = df[cols]
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'event_activity', 'data': data})

        # event activity arrangement types
        df = pd.json_normalize(json_data, record_path=['arrangement_types'], meta=['activity_id'])
        df = df.drop(columns=['name'])
        df.rename(columns={'id': 'arrangement_type_id'}, inplace=True)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'event_activity_arrangement_type', 'data': data})

        return normalised_data




