import os
from .config_loader import load_yaml_with_env

from auth_api.api_config import ApiConfig
from auth_api.access_token import AccessToken
from auth_api.oauth_scope import Scope

BASE = os.path.dirname(__file__)
CONFIG = load_yaml_with_env(os.path.join(BASE, "config.yml"))

REQUIRED_SCOPES = [
    Scope.READ_USERS,
    Scope.READ_PINS,
    Scope.READ_BOARDS,
    Scope.WRITE_PINS,
    Scope.WRITE_BOARDS,
    Scope.READ_SECRET_BOARDS,
    Scope.WRITE_SECRET_BOARDS,
    Scope.READ_ADS,
    Scope.WRITE_ADS,
    Scope.WRITE_CATALOGS,
    Scope.READ_CATALOGS,
]

API_CONFIG = ApiConfig(verbosity=1)
PINTEREST_ACCESS_TOKEN = AccessToken(API_CONFIG)
