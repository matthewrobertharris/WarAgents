package model.output;

import model.Agent;
import model.Map;

public class ClearSecondary extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		agent.setSecondary(null);
		return true;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.CLEAR_SECONDARY;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

}
