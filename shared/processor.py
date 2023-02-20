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
        self, keyvault_name, datalake_name, filesystem_raw_name, directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ):
        self.artifax_endpoint = endpoint
        self.artifax_api_secret = api_secret
        self.artifax_client_secret = client_secret
        self.keyvault_name = keyvault_name
        self.keyvault = KeyVault(azure_credential, self.keyvault_name)
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.directory_name = directory_name
        self.filename = endpoint.split("/")[1]
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        self._get_api_secrets()
        if self.artifax_endpoint == 'arrangements/event':
            self._get_event_data()
        elif self.artifax_endpoint == 'finances/invoice_schedule':
            self._get_invoice_schedule_data()
        else:
            self._get_data()
        self._upload_to_lake()

        return self.artifax_endpoint, self.artifax_filename

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

    def _get_invoice_schedule_data(self, previous_days=200):
        logging.info(f"Retrieving invoice schedules for previous {previous_days} days.")

        params = {
            'object_type': '1,2,3',
            'date': 'range',
            'range': 'last_days',
            'date_range': previous_days
        }

        self._get_data(params)

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

    def _upload_to_lake(self):
        directory_name = f"{self.directory_name}/{self.artifax_endpoint}/{self.import_date}"

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.directory_name
        )

        now = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"{self.filename}_{now}.json"
        self.artifax_filename = f"{self.artifax_endpoint}/{self.import_date}/{filename}"

        datalake.upload_file_to_directory(directory_name, filename, self.data)


class ArtifaxProcessor:
    def __init__(
        self, endpoint, raw_filename, datalake_name, filesystem_raw_name,
        filesystem_structured_name, root_directory_name, azure_credential
    ):
        self.directory_name = endpoint.split("/")[0]
        self.endpoint = endpoint
        self.entity = endpoint.split("/")[1]
        self.raw_filename = raw_filename
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.filesystem_structured_name = filesystem_structured_name
        self.root_directory_name = root_directory_name
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
            self.filesystem_raw_name, self.root_directory_name
        )

        raw_file = datalake.download_file_from_directory(self.raw_filename)

        try:
            json_file = raw_file.decode('utf-8')  # decode bytes to str
            return json_file
        except JSONDecodeError as e:
            print(e)

    def _upload_to_lake(self, filename, data, delete_files=True):
        directory_name = f"{self.root_directory_name}/{self.directory_name}/{filename}/{self.import_date}"

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_structured_name, self.root_directory_name
        )

        if delete_files:
            self._delete_existing_files(datalake, directory_name)

        now = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"{filename}_{now}.csv"
        datalake.upload_file_to_directory(directory_name, filename, data)

        return filename

    def _delete_existing_files(self, datalake, directory_name):
        if datalake.directory_exists(directory_name):
            files = datalake.list_directory_contents(directory_name)
            for file in files:
                filename = file.name.split('/')[-1]
                datalake.delete_file_from_directory(directory_name, filename)

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

    def _event_status(self, json_data):
        logging.info("Normalise event status entity")

        normalised_data = []

        # event status
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'event_status', 'data': data})

        return normalised_data

    def _invoice_schedule(self, json_data):
        logging.info("Normalise invoice schedule entity")

        normalised_data = []

        # invoice schedule
        cols = [
            'object_type',
            'arrangement_id',
            'ad_hoc_charge_id',
            'ad_hoc_charge_name',
            'ad_hoc_charge_type_id',
            'ad_hoc_charge_type_name',
            'event_id',
            'event_status_id',
            'room_id',
            'venue_id',
            'locale_id',
            'price_code_title_id',
            'price_code_name',
            'resource_booking_id',
            'resource_id',
            'resource_name',
            'resource_type_id',
            'resource_type_name',
            'unit_price',
            'unit_cost',
            'quantity',
            'source_amount',
            'amount_type_id',
            'amount_type_name',
            'entity_id',
            'entity_fullname',
            'purchase_order_number',
            'supplier_entity_id',
            'supplier_entity_full_name',
            'invoice_date',
            'tax_rate_1_id',
            'tax_rate_1_name',
            'tax_rate_1_code',
            'tax_rate_2_id',
            'tax_rate_2_name',
            'tax_rate_2_code',
            'net_amount',
            'tax_rate_1_amount',
            'tax_rate_2_amount',
            'tax_amount',
            'gross_amount',
            'invoice_number',
            'nominal_ledger_code_id',
            'nominal_ledger_code',
            'cost_centre_code_id',
            'cost_centre_code',
            'department_code_id',
            'department_code',
            'currency'
        ]
        df = pd.json_normalize(json_data)
        df = df[cols]
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'invoice_schedule', 'data': data})

        return normalised_data


class SpektrixRequest:
    def __init__(
        self, landing_filename, datalake_name, filesystem_landing_name,
        filesystem_raw_name, root_directory_name, azure_credential
    ):
        self.datalake_name = datalake_name
        self.filesystem_landing_name = filesystem_landing_name
        self.filesystem_raw_name = filesystem_raw_name
        self.root_directory_name = root_directory_name
        self.landing_filename = landing_filename
        self.entity = self.landing_filename.split("-")[0][4:].lower()
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        spektrix_file = self._download_from_landing_zone()
        raw_filename = self._upload_to_raw_zone(spektrix_file)

        return raw_filename

    def _download_from_landing_zone(self):
        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_landing_name, self.root_directory_name
        )

        landing_file = datalake.download_file_from_directory(self.landing_filename)

        return landing_file

    def _upload_to_raw_zone(self, file):
        directory_name = f"{self.root_directory_name}/{self.entity}/{self.import_date}"
        landing_filename = self.landing_filename[4:]

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.root_directory_name
        )

        datalake.upload_file_to_directory(directory_name, landing_filename, file)

        filename = f"{self.entity}/{self.import_date}/{landing_filename}"

        return filename


class SpektrixProcessor:
    def __init__(
            self, raw_filepath, datalake_name, filesystem_raw_name,
            filesystem_structured_name, root_directory_name, azure_credential
    ):
        self.raw_filepath = raw_filepath
        self.entity = self.raw_filepath.split("/")[0]
        self.raw_filename = self.raw_filepath.split("/")[-1]
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.filesystem_structured_name = filesystem_structured_name
        self.root_directory_name = root_directory_name
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        excel_file = self._download_from_raw_zone()
        csv_file = self._entity(excel_file)
        self._upload_to_structured_zone(csv_file)

        return self.raw_filename

    def _entity(self, file):
        entity = f"_{self.entity}"
        if hasattr(self, entity) and callable(func := getattr(self, entity)):
            return func(file)

    def _download_from_raw_zone(self):
        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.root_directory_name
        )

        raw_file = datalake.download_file_from_directory(self.raw_filepath)

        return raw_file

    def _upload_to_structured_zone(self, file, delete_files=True):
        directory_name = f"{self.root_directory_name}/{self.entity}/{self.import_date}"

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_structured_name, self.root_directory_name
        )

        if delete_files:
            self._delete_existing_files(datalake, directory_name)

        datalake.upload_file_to_directory(directory_name, self.raw_filename, file)

    def _delete_existing_files(self, datalake, directory_name):
        if datalake.directory_exists(directory_name):
            files = datalake.list_directory_contents(directory_name)
            for file in files:
                filename = file.name.split('/')[-1]
                datalake.delete_file_from_directory(directory_name, filename)

    def _convert_excel_to_csv(self, excel_file):
        try:
            df = pd.read_excel(excel_file)
            csv_file = df.to_csv(index=False)
            self.raw_filename = self.raw_filename.split(".")[0] + ".csv"
        except Exception as e:
            raise

        return csv_file

    def _customer(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _opportunity_stage_change(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _membership(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _event_instance(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _event(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _event_attributes(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _campaign(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _ticket_scans(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file

    def _transaction_item(self, excel_file):
        logging.info(f"Converting file to csv")
        csv_file = self._convert_excel_to_csv(excel_file)

        return csv_file


class AccessRequest:
    def __init__(
        self, keyvault_name, datalake_name, filesystem_raw_name, root_directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ):
        self.directory_name = endpoint
        self.endpoint = endpoint.split("/")[1]
        self.api_secret = api_secret
        self.client_secret = client_secret
        self.keyvault_name = keyvault_name
        self.keyvault = KeyVault(azure_credential, self.keyvault_name)
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.root_directory_name = root_directory_name
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        self._get_api_secrets()
        self._get_data()
        filename = self._upload_to_raw_zone()

        return filename

    def _get_api_secrets(self):
        self.api_key = self.keyvault.get_key_vault_secret(self.api_secret)
        self.client_name = self.keyvault.get_key_vault_secret(self.client_secret)
        self.base_url = f"https://{self.client_name}.dataengine.accessacloud.com/ds/"

    def _get_data(self, parameters=None):
        self.url = self.base_url + self.endpoint
        self.method = "GET"
        data = self._make_request(parameters=parameters)
        self.data = json.dumps(data, sort_keys=True, indent=4)

    def _make_request(self, parameters=None):
        headers = {'Authorization': self.api_key}
        session = Session()
        req = Request(method=self.method, url=self.url, headers=headers, params=parameters)

        logging.info(f"Requesting: {self.url}")
        try:
            r = session.send(req.prepare())
            r.raise_for_status()
            try:
                return r.json()
            except JSONDecodeError:
                return r.content
        except HTTPError as exc:
            logging.info(exc.response.text)
            raise

    def _upload_to_raw_zone(self):
        directory_name = f"{self.root_directory_name}/{self.directory_name}/{self.import_date}"

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.root_directory_name
        )

        now = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"{self.endpoint}_{now}.json"

        datalake.upload_file_to_directory(directory_name, filename, self.data)

        return f"{self.directory_name}/{self.import_date}/{filename}"


class AccessProcessor:
    def __init__(
            self, raw_filepath, datalake_name, filesystem_raw_name,
            filesystem_structured_name, root_directory_name, azure_credential
    ):
        self.raw_filepath = raw_filepath
        self.raw_filename = self.raw_filepath.split("/")[-1]
        self.directory_name = self.raw_filepath.split("/")[0]
        self.entity = '_'.join(f"{self.raw_filepath}".split("/")[0:2])
        self.datalake_name = datalake_name
        self.filesystem_raw_name = filesystem_raw_name
        self.filesystem_structured_name = filesystem_structured_name
        self.root_directory_name = root_directory_name
        self.import_date = datetime.now().strftime("%Y/%m/%d")
        self.azure_credential = azure_credential

    def process(self):
        json_file = self._download_from_lake()
        json_data = json.loads(json_file)
        normalised_data = self._entity(json_data)

        for file in normalised_data:
            filename = file['filename']
            data = file['data']
            self._upload_to_structured_zone(filename, data)

        return self.raw_filename

    def _entity(self, json_data):
        entity = f"_{self.entity}"
        if hasattr(self, entity) and callable(func := getattr(self, entity)):
            return func(json_data)

    def _download_from_lake(self):
        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_raw_name, self.root_directory_name
        )

        raw_file = datalake.download_file_from_directory(self.raw_filepath)

        try:
            json_file = raw_file.decode('utf-8')  # decode bytes to str
            return json_file
        except JSONDecodeError as e:
            print(e)

    def _upload_to_structured_zone(self, filename, data, delete_files=True):
        directory_name = f"{self.root_directory_name}/{self.directory_name}/{filename}/{self.import_date}"

        datalake = Datalake(
            self.azure_credential, self.datalake_name,
            self.filesystem_structured_name, self.root_directory_name
        )

        if delete_files:
            self._delete_existing_files(datalake, directory_name)

        datalake.upload_file_to_directory(directory_name, self.raw_filename, data)

    def _delete_existing_files(self, datalake, directory_name):
        if datalake.directory_exists(directory_name):
            files = datalake.list_directory_contents(directory_name)
            for file in files:
                filename = file.name.split('/')[-1]
                datalake.delete_file_from_directory(directory_name, filename)

    def _hr_person(self, json_data):
        logging.info("Normalise person entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'person', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data

    def _hr_person_ses(self, json_data):
        logging.info("Normalise person ses entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'person_ses', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data

    def _hr_appointment(self, json_data):
        logging.info("Normalise appointment entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'appointment', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data

    def _finance_nl_account(self, json_data):
        logging.info("Normalise account entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'nl_account', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data

    def _finance_costcentre(self, json_data):
        logging.info("Normalise costcentre entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'costcentre', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data

    def _finance_costheader(self, json_data):
        logging.info("Normalise costheader entity")

        normalised_data = []

        # person
        df = pd.json_normalize(json_data)
        data = df.to_csv(index=False)
        normalised_data.append({'filename': 'costheader', 'data': data})
        self.raw_filename = self.raw_filename.split(".")[0] + ".csv"

        return normalised_data