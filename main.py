import sys
import shutil
import os
from pathlib import Path

def check_first_run():
    config_path = Path("config.yaml")
    config_example_path = Path("config.example.yaml")
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    did_create = False
    
    if not config_path.exists():
        if config_example_path.exists():
            shutil.copy(config_example_path, config_path)
            print("config.yaml not found. Created one from config.example.yaml \u2014 please edit it before running again.")
            did_create = True
            
    if not env_path.exists():
        if env_example_path.exists():
            shutil.copy(env_example_path, env_path)
            print(".env not found. Created one from .env.example \u2014 please fill in your secrets before running again.")
            did_create = True
            
    if did_create:
        sys.exit(0)

if __name__ == '__main__':
    check_first_run()
    from ytpl_sync.main import cli
    cli()
