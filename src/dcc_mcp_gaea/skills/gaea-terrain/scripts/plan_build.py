from dcc_mcp_core.skill import run_main

from dcc_mcp_gaea.terrain import plan_build as main

if "__mcp_params__" in globals():
    __mcp_result__ = main(**globals()["__mcp_params__"])
if __name__ == "__main__":
    run_main(main)
