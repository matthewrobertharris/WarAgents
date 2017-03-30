package model.output;

import model.Agent;
import model.Map;

public class Death extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		return Action.death(agent, map);
	}

	@Override
	public Activity getActivity() {
		return Activity.DEATH;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}
}
