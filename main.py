import os
from src.authenticator import DatadisAuthenticator
from src.streams import Supplies, Comsumption

def main():
    username = os.environ.get("DATADIS_USERNAME")
    password = os.environ.get("DATADIS_PASSWORD")
    
    authenticator = DatadisAuthenticator(
        username=username,
        password=password
    )
    args = {
        "authenticator": authenticator,
        "authorized_nif": "47841486Z"
    }

    supplies = Supplies(**args)
    comsumption = Comsumption(parent=supplies, start_date="2023/10", **args)

    data = [e for e in comsumption.read_records()]
    reutrn data


if __name__ == "__main__":
    main()