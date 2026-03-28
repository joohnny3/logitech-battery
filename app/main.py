"""Entry point for Mouse Battery Monitor."""
import sys

from app.bootstrap import Application
from app.single_instance import acquire


def main() -> None:
    if not acquire():
        print("Mouse Battery Monitor 已在執行中，不可重複啟動。")
        sys.exit(0)

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
