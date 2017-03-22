package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class TeamSize extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return agent.getPlayer().currentAgents();
	}
	
	public String toString() {
		String output = Option.TEAM_SIZE.toString();
		return output;
	}

}
