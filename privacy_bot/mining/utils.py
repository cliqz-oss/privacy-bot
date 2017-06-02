
import logging
import sys
import tqdm


class TqdmLoggingHandler(logging.Handler):
    def emit (self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg, file=sys.stdout)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def setup_logging():
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    log.addHandler(TqdmLoggingHandler())
