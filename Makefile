.PHONY: install-schedule uninstall-schedule verify

verify:
	uv run pytest --maxfail=1 --disable-warnings -q

install-schedule:
	./00_run/install_refresh_schedule.sh

uninstall-schedule:
	./00_run/uninstall_refresh_schedule.sh
