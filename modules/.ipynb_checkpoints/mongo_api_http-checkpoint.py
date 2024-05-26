import os
import requests

class MongoDB:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def _handle_response(self, response):
        if response.ok:
            return response.json()
        else:
            return {"error": f"Request failed | status-code: {response.status_code} | message: {response.reason} | response: {response.text}"}
    
    def get_records(self, database, collection, query_params=None):
        try:
            url = f"{self.base_url}/{database}/{collection}"
            response = requests.get(url, params=query_params)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}
    
    def get_record_by_id(self, database, collection, record_id):
        try:
            url = f"{self.base_url}/{database}/{collection}/{record_id}"
            response = requests.get(url)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}
    
    def create_records(self, database, collection, record_data):
        try:
            url = f"{self.base_url}/{database}/{collection}"
            response = requests.post(url, json=record_data)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}
    
    def update_record(self, database, collection, record_id, updated_data):
        try:
            url = f"{self.base_url}/{database}/{collection}/{record_id}"
            response = requests.put(url, json=updated_data)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}
    
    def delete_record(self, database, collection, record_id):
        try:
            url = f"{self.base_url}/{database}/{collection}/{record_id}"
            response = requests.delete(url)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}

    def delete_records(self, database, collection):
        try:
            url = f"{self.base_url}/{database}/{collection}"
            response = requests.delete(url)
            return self._handle_response(response)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}

# # Example usage:
# if __name__ == "__main__":
#     mongo_client = MongoDB()
#     records = mongo_client.get_records("my_database", "my_collection")
#     print(records)

#     record = mongo_client.get_record_by_id("my_database", "my_collection", "some_record_id")
#     print(record)

#     new_record = {"name": "John Doe", "age": 30}
#     created_record = mongo_client.create_records("my_database", "my_collection", new_record)
#     print(created_record)

#     updated_data = {"age": 31}
#     updated_record = mongo_client.update_record("my_database", "my_collection", "some_record_id", updated_data)
#     print(updated_record)

#     deletion_result = mongo_client.delete_record("my_database", "my_collection", "some_record_id")
#     print(deletion_result)
