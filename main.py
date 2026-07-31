#!/usr/bin/env python3
from app import ForagerApp
import sys


def main():
    app = ForagerApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
