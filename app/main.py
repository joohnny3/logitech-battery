"""Entry point for Mouse Battery Monitor."""
import sys

from app.bootstrap import Application


def main() -> None:
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        import logging
        logging.exception("未預期的錯誤")
        sys.exit(1)


if __name__ == "__main__":
    main()
