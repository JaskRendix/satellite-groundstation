TOOLS_DIR := tools

analyze_hw:
	python3 $(TOOLS_DIR)/analyze_hw.py

torque_audit:
	python3 $(TOOLS_DIR)/sync_hw_config.py

update_config:
	python3 $(TOOLS_DIR)/update_config_from_stl.py

all: analyze_hw torque_audit
