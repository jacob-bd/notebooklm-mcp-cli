.PHONY: install-schedule uninstall-schedule health verify

verify:
	uv run pytest --maxfail=1 --disable-warnings -q

health:
	$(MAKE) verify

install-schedule:
	./00_run/install_refresh_schedule.sh

uninstall-schedule:
	./00_run/uninstall_refresh_schedule.sh
