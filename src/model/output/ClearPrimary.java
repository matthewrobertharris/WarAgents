package model.output;

import model.Agent;
import model.Map;

public class ClearPrimary extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		agent.setPrimary(null);
		return true;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.CLEAR_PRIMARY;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

}
