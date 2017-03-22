package model.output;

import model.Agent;
import model.Map;

public class Defend extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		return true;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.DEFEND;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

}
