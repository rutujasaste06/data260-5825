from mcp.server.fastmcp import FastMCP
import domain_core as core

mcp = FastMCP("trials")


@mcp.tool()
def search_trials(query: str, limit: int = 10) -> dict:
    """Search clinical trials by title. limit is 1-50."""
    return core.search_trials(query, limit)


@mcp.tool()
def get_trial(trial_id: int) -> dict:
    """Get one trial (with its sponsor) by id."""
    return core.get_trial(trial_id)


@mcp.tool()
def count_trials_by_sponsor(sponsor_id: int) -> dict:
    """Aggregate: number of trials and total available slots for a sponsor."""
    return core.count_trials_by_sponsor(sponsor_id)


if __name__ == "__main__":
    mcp.run()