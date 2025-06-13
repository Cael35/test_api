#!/usr/bin/env python3
# -*- coding: utf-8 -*-
################################################################################

import argparse
import json
import os
import sys

import requests

################################################################################


class Token:
    """
    GitHub/GitLab token, the value is the one you get when you create the token on the forge website and is read from
    the file file_name.

    Attributes:
      file_name: str: file path that contains the token.
      value: str: the token to pass in the request.
    """

    FORGE_LABEL = "##FORGE##"
    DEFAULT_FILE_NAME = f"~/.config/diverse-utilities/{FORGE_LABEL}_token.txt"

    def __init__(self, forge_key: str, file_name: str = DEFAULT_FILE_NAME):
        self.file_name = os.path.expanduser(file_name.replace(Token.FORGE_LABEL, forge_key))
        with open(self.file_name, "r", encoding="utf-8") as token_file:
            token = token_file.read().strip()
            self.value = token

    def print_object(self):
        """Print string representation of this token to stdout"""
        print(f"#### Token: file_name = {self.file_name} - value = {self.value}")


################################################################################
class Project:
    """
    The project for which you want to get metadata. You shall have created a token before on the corresponding forge.
    A Project corresponds to a Repository in GitHub.

    Attributes:
      name:str: name of the forge project; GitHub: <user>/<repository>, GitLab: <project_id>.
      forge_key:str: key of the forge to use, this key is used in dictionnary to have parameters that depend on the
          forge. For GitHub: GITHUB_KEY, For GitLab: GITLAB_KEY.
      forge_name:str: for GitLab only, identify the gitlab instance, cf --forge-name argument help.
      url:str: full url of the project.
          Derived attribute: /url(name, forge_key, forge_name).
    """

    GITHUB_KEY = "github"
    GITLAB_KEY = "gitlab"
    GITLAB_NAME = "gitlab.com"
    FORGE_NAME_LABEL = "##FORGE_NAME##"
    FORGE_URLS = {
        GITHUB_KEY: "https://api.github.com/repos/",
        GITLAB_KEY: f"https://{FORGE_NAME_LABEL}/api/v4/projects/",
    }

    def __init__(self, name: str, forge_key: str, forge_name: str = GITLAB_NAME):
        self.name = name
        self.forge_key = forge_key
        self.forge_name = forge_name

    def __getattr__(self, name):
        if name == "url":
            value = Project.FORGE_URLS[self.forge_key].replace(Project.FORGE_NAME_LABEL, self.forge_name) + self.name
        else:
            raise AttributeError(name)
        return value

    def print_object(self):
        print(
            f"#### Project: name = {self.name} - forge_key = {self.forge_key} - forge_name = {self.forge_name} - "
            f"url = {self.url}"
        )


################################################################################
class GetRequest:
    """
    Implements a GET to the REST API of the given project endpoint.

    Attributes:
      endpoint:str: endpoint name of the data you want.
      /endpoint_url:str: endpoint url to pass to request the REST API.
          Derived attribute: /url(name, forge_key, forge_name).
      results:list: result of the request, i.e. the data you asked for.

    Associations:
      project:Project: the project you want to access.
      token:Token: the forge token to access the REST API.
    """

    KEY_LABEL = "key"
    VALUE_LABEL = "value"
    HEADER_INFO = {
        Project.GITHUB_KEY: {KEY_LABEL: "Accept", VALUE_LABEL: "application/vnd.github.v3+json"},
        Project.GITLAB_KEY: {KEY_LABEL: "Content-Type", VALUE_LABEL: "application/json"},
    }

    def __init__(self, the_project: Project, the_token: Token, the_endpoint: str = ""):
        self.endpoint = the_endpoint
        self.results = []
        self.project = the_project
        self.token = the_token

    def __getattr__(self, name):
        if name == "endpoint_url":
            value = (self.project.url + "/" + self.endpoint) if (self.endpoint) else (self.project.url)
        else:
            raise AttributeError(name)
        return value

    def __setattr__(self, name, value):
        if name == "endpoint" and isinstance(value, str):
            value = value.strip()
        super().__setattr__(name, value)

    def run(self):
        request_header = {
            "Authorization": f"Bearer {self.token.value}",
            GetRequest.HEADER_INFO[self.project.forge_key][GetRequest.KEY_LABEL]: GetRequest.HEADER_INFO[
                self.project.forge_key
            ][GetRequest.VALUE_LABEL],
        }

        response = requests.get(self.endpoint_url, headers=request_header)
        if response.status_code != 200:
            print("*" * 80)
            print(f"Error: Unable to get '{self.endpoint_url}'. Status Code: {response.status_code}")
            print("*" * 80)
            print(f"{response.json()}")
            print("*" * 80)
            sys.exit(1)
        self.results = response.json()

    def print_results(self, output):
        json.dump(self.results, output, indent=4)
        output.write("\n")

    def print_object(self):
        print(
            f"#### GetRequest: endpoint = {self.endpoint} - project_url = {self.project.url} - endpoint = "
            f"{self.endpoint}"
        )


################################################################################
def get_args():
    """
    Command line parsing and help.
    """
    my_parser = argparse.ArgumentParser(description="Get data from GitHub or GitLab using the according REST API.")

    my_parser.add_argument(
        "-f",
        "--forge",
        choices=[Project.GITHUB_KEY, Project.GITLAB_KEY],
        required=True,
        help="Choose the target forge.",
    )

    my_parser.add_argument(
        "-fn",
        "--forge-name",
        type=str,
        default=Project.GITLAB_NAME,
        help=(
            f"The forge name, e.g. gitlab.com for 'https://gitlab.com'. Default value is '{Project.GITLAB_NAME}'. If "
            f"'--forge {Project.GITHUB_KEY}' is used, this parameter is ignored."
        ),
    )

    my_parser.add_argument(
        "-p",
        "--project",
        type=str,
        required=True,
        help="Name of the project, format is, for GitHub: 'username/repository', for GitLab: project ID",
    )

    my_parser.add_argument(
        "-e",
        "--endpoint",
        type=str,
        default="",
        help="Endpoint name of the data you want, can be: events, issues, issues/<#issue>/comments, pulls, "
        "pulls?state=all, etc. Endpoint name depends on the <forge>.",
    )

    default_token_file_name = Token.DEFAULT_FILE_NAME.replace(Token.FORGE_LABEL, "<forge>")
    my_parser.add_argument(
        "-tf",
        "--token-file",
        type=str,
        default=Token.DEFAULT_FILE_NAME,
        help=(
            f"Full path name of the file containing your GitHub/GitLab authentication token, default is "
            f"{default_token_file_name}."
        ),
    )

    my_parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Full path name of the file to write the request result(s).",
    )

    return my_parser.parse_args()


################################################################################
def __main():
    my_args = get_args()

    forge_token = Token(my_args.forge, my_args.token_file)

    the_project = Project(my_args.project, my_args.forge, my_args.forge_name)

    the_request = GetRequest(the_project, forge_token, my_args.endpoint)
    the_request.run()
    the_request.print_results(my_args.output)


if __name__ == "__main__":
    __main()
