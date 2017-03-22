package model.output;

import model.Agent;
import model.Map;

public class Confused extends Action {

	public static final int CONFUSED_HARM = 10;
	@Override
	public boolean action(Agent agent, Map map) {
		int agentHealth = agent.getHealth();
		if(agentHealth <= CONFUSED_HARM) {
			return death(agent, map);
		}
		else {
			agent.setHealth(agentHealth - CONFUSED_HARM);
			return true;
		}
	}
	
	@Override
	public Activity getActivity() {
		return Activity.CONFUSED;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

}
