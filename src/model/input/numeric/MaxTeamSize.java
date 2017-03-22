package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class MaxTeamSize extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return agent.getPlayer().getMaxAgents();
	}
	
	public String toString() {
		String output = Option.MAX_TEAM_SIZE.toString();
		return output;
	}

}
