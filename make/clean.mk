.PHONY: clean
clean: clean-chaos clean-dr clean-mutation ## Remove generated artifact folders
	rm -rf "$(ARTIFACTS_DIR)"
