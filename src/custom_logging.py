import logging
import os
from datetime import datetime
LOG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_LEVEL = "DEBUG"
# Create a custom logger
logger = logging.getLogger("datadis")
logger.setLevel(LOG_LEVEL)

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(
    "{}/datadis.log".format(
        LOG_FOLDER)
)
c_handler.setLevel(LOG_LEVEL)
f_handler.setLevel(LOG_LEVEL)


# Create formatters and add it to handlers
c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)

if __name__ == "__main__":
    print(LOG_FOLDER)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")