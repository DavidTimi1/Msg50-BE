import json
import os
import re
import subprocess
import time
from xmlrpc.client import boolean
from django.conf import settings
from django.core.management.base import BaseCommand
import requests


API_TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")
USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")


class Command(BaseCommand):
    help = "Sync remote pythonanywhere webapp with local files changes."

    def list_files(self, retry, tag="[pa-CICD]"):
        """Get the list of files changed since the last commit with a specific tag in its message."""
        try:
            # Find the commit hash of the last commit with the specified tag
            result = subprocess.run(
                ["git", "log", "--grep", tag, "--format=%H", "-n", "1"],
                capture_output=True,
                text=True
            )
            last_tagged_commit = result.stdout.strip()

            if not last_tagged_commit:
                # No commit with the specified tag found, return all changes ever
                result = subprocess.run(
                    ["git", "log", "--name-status", "--pretty=format:"],
                    capture_output=True,
                    text=True
                )
                synced_files = set()
                if retry:
                    synced_files_path = "pyanywhere_synced.json"
                    if os.path.exists(synced_files_path):
                        with open(synced_files_path, "r") as f:
                            synced_files = set(json.load(f))

                # Only keep the latest change for each file
                file_changes = {}

                for line in result.stdout.strip().split("\n"):
                    if line:
                        status, file_path = line.split("\t", 1)
                        file_changes[file_path] = status
                    
                changed_files = [(status, file_path) for file_path, status in file_changes.items() if not retry or file_path not in synced_files]
                return changed_files

            # Get the list of changed files since the last tagged commit
            result = subprocess.run(
                ["git", "diff", "--name-status", f"{last_tagged_commit}..HEAD"],
                capture_output=True,
                text=True
            )

            # Only keep the latest change for each file
            file_changes = {}
            for line in result.stdout.strip().split("\n"):
                if line:
                    status, file_path = line.split("\t", 1)
                    file_changes[file_path] = status
                
            changed_files = [(status, file_path) for file_path, status in file_changes.items() if not retry or file_path not in synced_files]

            return changed_files

        except subprocess.CalledProcessError as e:
            print(f"Error while fetching changed files: {e}")
            return []


    def delete_file_from_pythonanywhere(self, remote_path):
        """Delete a file from PythonAnywhere."""
        url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/files/path{remote_path}"
        headers = {"Authorization": f"Token {API_TOKEN}"}

        response = requests.delete(url, headers=headers)

        if response.status_code < 300:
            print(f"File '{remote_path}' deleted successfully.")
        elif response.status_code == 404:
            print(f"File '{remote_path}' not found.")
        elif response.status_code == 429:
            time_lapse = response.headers.get("Retry-After", 60)
            print(f"Rate limited. Retrying after {time_lapse} seconds.")
            time.sleep(int(time_lapse))
            self.delete_file_from_pythonanywhere(remote_path)
        else:
            print(f"Failed to delete file '{remote_path}'. Status code: {response.status_code}, Response: {response.text}")


    def upload_file_to_pythonanywhere(self, file_path, destination_path):
        """Upload a single file to PythonAnywhere."""
        url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/files/path{destination_path}"
        headers = {"Authorization": f"Token {API_TOKEN}"}

        try:
            with open(file_path, "rb") as file:
                response = requests.post(url, headers=headers, files={"content": file})
        
        except FileNotFoundError:
            self.stdout.write("File no longer exists")
            return

        if response.status_code < 400:
            print(f"File '{file_path}' uploaded successfully to '{destination_path}'.")

        elif response.status_code == 429:
            time_lapse = response.headers.get("Retry-After", 60)
            print(f"Rate limited. Retrying after {time_lapse} seconds.")
            time.sleep(int(time_lapse))
            self.upload_file_to_pythonanywhere(file_path, destination_path)
        else:
            print(f"Failed to upload file '{file_path}' to '{destination_path}'. Status code: {response.status_code}, Response: {response.text}")


    def add_arguments(self, parser):
        """Define optional arguments for project and destination directories."""
        parser.add_argument(
            "--project-dir",
            type=str,
            default=settings.BASE_DIR,  # Default to Django project root
            help="Path to the Django project directory (default: BASE_DIR)"
        )
        parser.add_argument(
            "--destination-dir",
            type=str,
            required=True,
            help="Path to the destination directory on PythonAnywhere"
        )
        parser.add_argument(
            "--retry",
            type=boolean,
            default=False,  # Default to Django project root
            help="Retrying a stopped upload"
        )


    def handle(self, *args, **options):
        """Sync files based on the latest Git commit."""
        project_dir = options["project_dir"]
        destination_dir = f"/home/{USERNAME}/{options['destination_dir']}"
        retry = options["retry"]

        self.stdout.write(f"Using project directory: {project_dir}")
        self.stdout.write(f"Syncing to destination: {destination_dir}")

        changed_files = self.list_files(retry)

        for status, file_path in changed_files:
            relative_path = os.path.relpath(file_path, project_dir)
            remote_path = os.path.join(destination_dir, relative_path).replace("\\", "/")

            if status in ['D', 'M', 'R']:
                self.delete_file_from_pythonanywhere(remote_path)
                # self.stdout.write(f"File '{remote_path}' deleted remotely.")

            if status in ['M', 'R', 'A']:
                self.upload_file_to_pythonanywhere(file_path, remote_path)
                # self.stdout.write(f"File '{file_path}' uploaded to '{remote_path}'.")

