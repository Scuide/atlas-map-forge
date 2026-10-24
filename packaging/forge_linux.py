"""Entry point for the Linux browser edition, including frozen worker processes."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Force the browser edition even if a webview backend becomes available later.
    if "--browser" not in sys.argv:
        sys.argv.append("--browser")
    from atlasforge.app import main
    main()
